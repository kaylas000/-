"""Нейро-сметчик — локальный AI-ассистент сметчика.

Реализация MVP по ТЗ v1.1: детерминированный пайплайн
Parser -> Clarification -> Search -> Matching -> Calculation -> Validation -> Document,
управляемый Orchestrator с human-in-the-loop на всех неоднозначных шагах.

LLM НЕ используется для вычислений (ТЗ 3.2.5) и не является источником цен:
каждая позиция обязана ссылаться на запись price_catalog (ТЗ 5.2).
"""

__version__ = "1.1.0-mvp"
