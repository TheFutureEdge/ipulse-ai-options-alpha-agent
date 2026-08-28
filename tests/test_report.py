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
                            "value": {"headline": "<script>alert(1)</script>"},
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
            output = build_decision_report(journal, root / "report.html")
            rendered = output.read_text(encoding="utf-8")
        self.assertIn("SPY decision trace", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("Execution forbidden", rendered)


if __name__ == "__main__":
    unittest.main()
