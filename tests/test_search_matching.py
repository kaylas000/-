"""Unit/integration: гибридный поиск и пороги confidence (ТЗ 3.2.3, 3.2.4)."""
from __future__ import annotations

import time

from neuro_smetchik.catalog import get_catalog
from neuro_smetchik.config import settings
from neuro_smetchik.matching import match_query
from neuro_smetchik.search import get_search, ngrams, stem, tokens


def test_hybrid_search_finds_catalog_items():
    hits = get_search().search("штукатурка стен по маякам", top_n=5)
    assert hits and hits[0].catalog_id == "CAT-018"
    assert hits[0].semantic_score > 0 and hits[0].keyword_score > 0
    assert all(h.latency_ms <= settings.search_sla_ms for h in hits)


def test_search_latency_sla_500ms():
    start = time.perf_counter()
    for phrase in ["укладка ламината", "натяжной потолок", "прокладка канализации", "грунтовка"]:
        get_search().search(phrase)
    assert (time.perf_counter() - start) * 1000 < 500


def test_keyword_and_semantic_components():
    assert "штукатурк" in tokens("штукатурка стен")
    assert stem("шпаклевка") == stem("шпаклевки")
    assert "^шт" in ngrams("штукатурка")


def test_confidence_thresholds():
    auto = match_query("штукатурка стен по маякам", trace_id="t1", persist_log=False)
    review = match_query("укладка кафеля", trace_id="t2", persist_log=False)
    escalated = match_query("уточнить объём работ: что-нибудь", trace_id="t3", persist_log=False)
    assert auto.status == "auto_accepted" and auto.confidence >= float(settings.match_auto_accept)
    assert review.status == "needs_review"
    assert escalated.status == "escalated" and escalated.confidence < float(settings.match_extended_search)


def test_every_match_references_real_catalog_item():
    cat = get_catalog()
    for phrase in ["шпаклевка стен", "стяжка пола", "установка унитаза", "монтаж вентиляции", "отделка"]:
        m = match_query(phrase, trace_id="t4", persist_log=False)
        assert m.catalog_id is None or cat.get(m.catalog_id) is not None


def test_vague_query_never_auto_accepted():
    m = match_query("отделка", trace_id="t5", persist_log=False)
    assert m.status != "auto_accepted"
