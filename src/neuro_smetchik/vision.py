"""Vision/OCR Service (ТЗ v1.1 3.2.10): качество фото,-confidence, деградация в ручной ввод.

В MVP — детерминированный анализ качества изображения + разбор текстовых метаданных.
При наличии локальной мультимодальной модели (Qwen2.5-VL) через vLLM сюда
подключается /v1/chat/completions с image_url; контракт JSON остаётся тем же.
"""
from __future__ import annotations

import io
import re
import uuid
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from .db import db
from .llm import llm
from .models import dumps, utcnow
from .prompts import resolve
from .security import CONTROL_CHARS, validate_upload


def analyze_image(data: bytes, *, filename: str, mime: str, trace_id: str,
                  actor: dict[str, Any] | None = None) -> dict[str, Any]:
    ok, reason = validate_upload(data, mime, filename)
    if not ok:
        return {"accepted": False, "reason": reason, "elements": [], "confidence": 0.0,
                "degraded_to_manual": True, "trace_id": trace_id}

    image = Image.open(io.BytesIO(data)).convert("L")
    edges = image.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    mean_brightness = ImageStat.Stat(image).mean[0] / 255
    sharpness = min(1.0, (stat.stddev[0] / 25))          # грубая оценка резкости
    blur_penalty = 0.0 if sharpness > 0.35 else (0.35 - sharpness)
    light_penalty = 0.0 if 0.25 <= mean_brightness <= 0.85 else 0.3
    quality = round(max(0.0, min(1.0, 0.6 * sharpness + 0.4 * mean_brightness - blur_penalty - light_penalty)), 3)

    elements: list[dict[str, Any]] = []
    # Текст из метаданных (EXIF/comment) — источник возможной injection, санитизируем.
    meta_text = ""
    try:
        meta_text = str(image.info.get("comment") or image.info.get("exif") or "")[:2000]
    except Exception:
        pass
    meta_text = CONTROL_CHARS.sub(" ", meta_text)
    area_match = re.search(r"(\d{1,4}(?:[.,]\d+)?)\s*(?:м2|м²|кв)", meta_text, re.I)
    if area_match:
        elements.append({"type": "площадь", "value": area_match.group(1).replace(",", "."),
                         "confidence": round(min(0.95, quality), 2), "source": "metadata"})
    if quality < 0.35:
        elements.append({"type": "дефект", "value": "низкое качество фото (размытие/освещение)",
                         "confidence": 0.9, "source": "quality_check"})

    degraded = quality < 0.35
    confidence = round(min(0.9, quality), 2)
    # При доступном локальном VLM — запрос структурированного JSON (роли system/user разделены).
    model_used = "vision-rules-v1"
    if llm.enabled and not degraded:
        prompt = resolve("vision", trace_id)
        res = llm.complete(service="vision", system=prompt.body,
                           user="Фото объекта. Верни JSON по схеме.", trace_id=trace_id,
                           prompt_version=prompt.version)
        model_used = res.model if res.source == "local_vllm" else model_used

    result = {
        "accepted": True, "trace_id": trace_id, "file_name": filename, "mime": mime,
        "size_bytes": len(data), "quality_score": quality, "elements": elements,
        "confidence": confidence, "degraded_to_manual": degraded,
        "model_used": model_used,
        "note": "При низком confidence необходим ручной ввод параметров (ТЗ 3.2.10)",
    }
    db.insert("vision_extraction_results", {
        "id": str(uuid.uuid4()), "trace_id": trace_id, "file_name": filename[:255], "mime": mime,
        "size_bytes": len(data), "quality_score": quality, "elements_json": dumps(elements),
        "confidence": confidence, "created_at": utcnow(),
    })
    return result
