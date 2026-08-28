"""Tests for bounded normalization of untrusted Alpaca news."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from ipulse_options_alpha_agent.news import (
    lexicon_sentiment,
    normalize_alpaca_news,
)


class NewsTests(unittest.TestCase):
    def test_lexicon_sentiment_is_bounded_and_directional(self) -> None:
        self.assertGreater(lexicon_sentiment("strong profit growth beats"), 0)
        self.assertLess(lexicon_sentiment("weak loss downgrade probe"), 0)
        self.assertEqual(lexicon_sentiment("ordinary neutral update"), 0)

    def test_normalizes_only_fresh_symbol_matched_articles(self) -> None:
        now = datetime(2026, 8, 28, 14, 0, tzinfo=UTC)
        payload = {
            "news": [
                {
                    "id": 1,
                    "headline": "Strong earnings growth beats expectations",
                    "summary": "Portfolio companies report profit growth.",
                    "source": "Benzinga",
                    "symbols": ["SPY"],
                    "created_at": "2026-08-28T12:00:00Z",
                },
                {
                    "id": 2,
                    "headline": "Unrelated article",
                    "summary": "This belongs to another symbol.",
                    "source": "Benzinga",
                    "symbols": ["QQQ"],
                    "created_at": "2026-08-28T12:00:00Z",
                },
                {
                    "id": 3,
                    "headline": "Stale article",
                    "summary": "Too old for the evidence window.",
                    "source": "Benzinga",
                    "symbols": ["SPY"],
                    "created_at": "2026-08-01T12:00:00Z",
                },
            ]
        }
        result = normalize_alpaca_news(payload, underlying="SPY", now=now)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].evidence_id, "news:alpaca:1")
        self.assertGreater(result[0].sentiment_score, 0)


if __name__ == "__main__":
    unittest.main()
