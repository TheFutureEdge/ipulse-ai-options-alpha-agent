"""Tests for safe static rendering of the latest decision cycle."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ipulse_options_alpha_agent.report import build_decision_report


class ReportTests(unittest.TestCase):
    def test_builds_latest_cycle_and_escapes_external_text(self) -> None:
        records = [
            {
                "recorded_at_utc": "2026-08-28T14:00:00Z",
                "event_type": "research_context",
                "payload": {
                    "underlying": "SPY",
                    "evidence": [
                        {
                            "evidence_id": "news:1",
                            "category": "news",
                            "value": {
                                "headline": "<script>alert(1)</script>",
                                "summary": "Do not publish this article excerpt.",
                            },
                            "source": "test",
                            "unit": None,
                            "as_of_utc": "2026-08-28T13:00:00Z",
                        }
                    ],
                },
            },
            {
                "recorded_at_utc": "2026-08-28T14:00:01Z",
                "event_type": "advisor_opinions",
                "payload": {
                    "opinions": [
                        {
                            "advisor": "news_catalyst",
                            "action": "WAIT",
                            "confidence": 0.5,
                            "thesis": "Untrusted <b>headline</b>.",
                            "evidence_refs": ["news:1"],
                            "contrary_evidence": [],
                            "invalidation_conditions": [],
                        }
                    ]
                },
            },
            {
                "recorded_at_utc": "2026-08-28T14:00:02Z",
                "event_type": "advisor_consensus",
                "payload": {
                    "action": "WAIT",
                    "confidence": 1,
                    "rationale": "Insufficient evidence.",
                    "hard_vetoes": [],
                },
            },
            {
                "recorded_at_utc": "2026-08-28T14:00:03Z",
                "event_type": "operational_safety",
                "payload": {"approved": False, "reasons": ["Market closed."]},
            },
            {
                "recorded_at_utc": "2026-08-28T14:00:04Z",
                "event_type": "agent_decision",
                "payload": {"action": "WAIT", "explanation": "Safety veto."},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal = root / "evidence.jsonl"
            journal.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
            performance = root / "performance.jsonl"
            performance.write_text(
                json.dumps(
                    {
                        "event_type": "competition_performance",
                        "payload": {
                            "cumulative_pnl_usd": 125.5,
                            "cumulative_return_pct": 0.1255,
                            "baseline_ready": True,
                            "options_trading_level": 3,
                            "open_positions": 1,
                            "filled_orders": 2,
                            "issues": [],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            validation = root / "validation.json"
            validation.write_text(
                json.dumps(
                    {
                        "captured_at_utc": "2026-09-04T03:20:41Z",
                        "regimes": {
                            "SPY": {"qualifies": False},
                            "QQQ": {"qualifies": False},
                            "IWM": {"qualifies": False},
                        },
                        "decision": {"action": "WAIT"},
                    }
                ),
                encoding="utf-8",
            )
            output = build_decision_report(
                journal,
                root / "report.html",
                performance,
                preopen_validation_path=validation,
            )
            rendered = output.read_text(encoding="utf-8")
        self.assertIn("Options alpha, with receipts.", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertNotIn("Do not publish this article excerpt.", rendered)
        self.assertIn("Execution forbidden", rendered)
        self.assertIn("Competition paper account", rendered)
        self.assertIn("$125.50", rendered)
        self.assertIn("Latest frozen-rule check", rendered)
        self.assertIn("3 underlyings checked · 0 qualified", rendered)
        self.assertIn("Historical v0 safety-control replay", rendered)
        self.assertIn("No baseline issues recorded.", rendered)
        self.assertNotIn(
            "2 filled orders</p><ul><li class=\"muted\">None recorded", rendered
        )
        self.assertIn('content="index,follow,max-image-preview:large"', rendered)


if __name__ == "__main__":
    unittest.main()
