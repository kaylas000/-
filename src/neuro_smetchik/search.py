"""Search Service: гибридный поиск semantic (char-ngram TF-IDF) + keyword (exact).

Полностью локальный, без внешних эмбеддингов: в проде semantic-часть заменяется на
Qdrant + embedding-модель, контракт и метрики остаются теми же (ТЗ 3.2.3, 4.3).
SLA: p95 <= 500 мс на запрос.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter

from .catalog import Catalog, get_catalog
from .config import settings
from .models import CatalogItem, SearchHit

WORD_RE = re.compile(r"[a-zа-яё0-9]+", re.I)
STOP = set("""
и в на с по для из под до к у о от при за не или это смета смету стоимость работ работа работы ремонт
сделать нужно посчитайте посчитать составь составить сколько будет стоить черновик оцени объём объем
требуется необходимо прошу пожалуйста квартиры помещения м2 кв м квадратных метра метров площадью
""".split())

SUFFIXES = ("иями", "ями", "ами", "ого", "его", "ыми", "ими", "ах", "ях", "ов", "ев", "ам", "ям",
            "ой", "ый", "ий", "ая", "яя", "ое", "ее", "ые", "ие", "ью", "ию", "ия", "ье", "ем", "им",
            "ть", "ла", "ли", "ло", "ет", "ут", "ют", "а", "я", "ы", "и", "е", "о", "у", "ю", "ь")


def stem(word: str) -> str:
    w = word.lower().replace("ё", "е")
    if len(w) <= 4:
        return w
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def tokens(text: str) -> set[str]:
    return {stem(t) for t in WORD_RE.findall(text.lower()) if t not in STOP and len(t) > 2}


def ngrams(text: str, n: int = 3) -> set[str]:
    out: set[str] = set()
    for word in WORD_RE.findall(text.lower().replace("ё", "е")):
        padded = f"^{word}$"
        for i in range(len(padded) - n + 1):
            out.add(padded[i:i + n])
    return out


# Расширение синонимов: разговорная формулировка -> каталожный термин
DOMAIN_SYNONYMS: dict[str, list[str]] = {
    "отштукатурить": ["штукатурка"], "зашпаклевать": ["шпаклевка"], "положить плитку": ["укладка плитки"],
    "постелить": ["укладка"], "провести свет": ["электропроводка"], "сделать разводку": ["электропроводка"],
    "поменять трубы": ["прокладка труб"], "поставить розетки": ["установка розеток"],
    "побелить": ["окраска"], "поставить дверь": ["монтаж двери"], "сделать потолок": ["потолок"],
}


class HybridSearch:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()
        self.items = self.catalog.items
        self.n = len(self.items)
        self._item_tokens: list[set[str]] = [tokens(i.searchable) for i in self.items]
        self._item_grams: list[set[str]] = [ngrams(i.searchable) for i in self.items]
        df: Counter[str] = Counter()
        for grams in self._item_grams:
            df.update(grams)
        self.idf: dict[str, float] = {g: math.log((self.n + 1) / (c + 0.5)) + 1 for g, c in df.items()}
        self._item_norms = [math.sqrt(sum(self.idf.get(g, 1.0) ** 2 for g in grams)) or 1.0 for grams in self._item_grams]

    def _semantic(self, query_grams: set[str], query_norm: float, idx: int) -> float:
        if not query_grams or query_norm == 0:
            return 0.0
        shared = query_grams & self._item_grams[idx]
        num = sum(self.idf.get(g, 1.0) ** 2 for g in shared)
        return min(1.0, num / (query_norm * self._item_norms[idx]))

    @staticmethod
    def _exact_phrase(query: str, item: CatalogItem) -> float:
        """Точное совпадение фразы. Короткий запрос не должен получать бонус за то,
        что он является подстрокой длинного синонима («отделка» ≠ «отделка откосов»)."""
        q = query.lower().replace("ё", "е").strip()
        for syn in item.synonyms:
            s = syn.lower().replace("ё", "е")
            if len(s) >= 5 and s in q:
                return 1.0
            if len(s) >= 8 and len(q) >= 8 and len(q) >= 0.75 * len(s) and q in s:
                return 1.0
        name = item.name.lower().replace("ё", "е")
        head = name.split("(")[0].strip()
        if len(head) >= 8 and head in q:
            return 1.0
        return 0.0

    def search(self, query: str, top_n: int | None = None, *, category: str | None = None,
               expand: bool = False) -> list[SearchHit]:
        """Гибридный поиск. expand=True — повторный расширенный поиск (ТЗ 3.2.4)."""
        started = time.perf_counter()
        q = (query or "").lower().replace("ё", "е").strip()
        if expand:
            for src, repl in DOMAIN_SYNONYMS.items():
                if src in q:
                    q += " " + " ".join(repl)
        q_tokens = tokens(q)
        q_grams = ngrams(q)
        q_norm = math.sqrt(sum(self.idf.get(g, 1.0) ** 2 for g in q_grams)) or 1.0
        hits: list[SearchHit] = []
        for idx, item in enumerate(self.items):
            if category and item.category != category:
                continue
            sem = self._semantic(q_grams, q_norm, idx)
            it = self._item_tokens[idx]
            kw = len(q_tokens & it) / len(q_tokens) if q_tokens else 0.0
            phrase = self._exact_phrase(q, item)
            code_bonus = 0.10 if item.code.lower() in q else 0.0
            score = min(1.0, 0.45 * sem + 0.35 * min(1.0, kw) + 0.20 * phrase + code_bonus)
            if score <= 0.02:
                continue
            hits.append(SearchHit(item.id, round(score, 4), round(sem, 4), round(kw, 4), 0.0, item))
        hits.sort(key=lambda h: (-h.score, h.catalog_id))
        hits = hits[: top_n or settings.search_top_n]
        latency = (time.perf_counter() - started) * 1000
        return [SearchHit(h.catalog_id, h.score, h.semantic_score, h.keyword_score, round(latency, 2), h.item)
                for h in hits]


_search: HybridSearch | None = None


def get_search() -> HybridSearch:
    global _search
    if _search is None:
        _search = HybridSearch()
    return _search
