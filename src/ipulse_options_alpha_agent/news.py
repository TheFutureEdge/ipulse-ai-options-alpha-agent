"""Normalization of untrusted Alpaca news into bounded advisor evidence."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from .research import NewsEvidence


POSITIVE_TERMS = frozenset(
    {
        "approval",
        "approved",
        "beat",
        "beats",
        "bullish",
        "exceeds",
        "gain",
        "gains",
        "growth",
        "partnership",
        "profit",
        "profits",
        "raise",
        "raised",
        "raises",
        "record",
        "strong",
        "surge",
        "upgrade",
        "upgraded",
    }
)

NEGATIVE_TERMS = frozenset(
    {
        "bankruptcy",
        "bearish",
        "concern",
        "cut",
        "cuts",
        "decline",
        "default",
        "downgrade",
        "downgraded",
        "fall",
        "falls",
        "fraud",
        "investigation",
        "loss",
        "losses",
        "lawsuit",
        "miss",
        "misses",
        "probe",
        "restatement",
        "weak",
    }
)


def lexicon_sentiment(text: str) -> float:
    """Return an auditable bounded baseline sentiment score in [-1, 1]."""

    tokens = re.findall(r"[a-z]+", text.lower())
    positive = sum(token in POSITIVE_TERMS for token in tokens)
    negative = sum(token in NEGATIVE_TERMS for token in tokens)
    if positive == negative == 0:
        return 0.0
    return max(-1.0, min(1.0, (positive - negative) / (positive + negative + 2)))


def _find_news_list(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        value = payload.get("news")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        for nested in payload.values():
            found = _find_news_list(nested)
            if found:
                return found
    return []


def _parse_timestamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def normalize_alpaca_news(
    payload: object,
    *,
    underlying: str,
    now: datetime | None = None,
    maximum_age: timedelta = timedelta(days=7),
    maximum_items: int = 10,
) -> tuple[NewsEvidence, ...]:
    """Accept only fresh, symbol-matched, minimally complete news records."""

    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    symbol = underlying.upper()
    results: list[NewsEvidence] = []
    seen: set[str] = set()
    for record in _find_news_list(payload):
        raw_id = record.get("id")
        evidence_id = f"news:alpaca:{raw_id}"
        if raw_id is None or evidence_id in seen:
            continue
        symbols = record.get("symbols")
        if not isinstance(symbols, list) or symbol not in {
            str(item).upper() for item in symbols
        }:
            continue
        published = _parse_timestamp(record.get("created_at"))
        if published is None:
            continue
        if published > effective_now + timedelta(minutes=5):
            continue
        if effective_now - published > maximum_age:
            continue
        headline = str(record.get("headline", "")).strip()[:500]
        summary = str(record.get("summary", "")).strip()[:4_000]
        source = str(record.get("source", "")).strip()[:200]
        if not headline or not summary or not source:
            continue
        results.append(
            NewsEvidence(
                evidence_id=evidence_id,
                headline=headline,
                summary=summary,
                source=f"alpaca_news:{source}",
                published_at_utc=published.isoformat(),
                sentiment_score=lexicon_sentiment(f"{headline} {summary}"),
            )
        )
        seen.add(evidence_id)
        if len(results) >= maximum_items:
            break
    return tuple(results)


def merge_news_evidence(
    *collections: tuple[NewsEvidence, ...],
) -> tuple[NewsEvidence, ...]:
    """Merge sources without permitting duplicate evidence identifiers."""

    merged: dict[str, NewsEvidence] = {}
    for collection in collections:
        for item in collection:
            merged.setdefault(item.evidence_id, item)
    return tuple(merged.values())
