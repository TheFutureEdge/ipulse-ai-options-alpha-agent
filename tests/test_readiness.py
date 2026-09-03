"""Tests for deterministic final-submission readiness checks."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ipulse_options_alpha_agent.readiness import check_submission_readiness


class SubmissionReadinessTests(unittest.TestCase):
    def _project(self, root: Path) -> None:
        for relative in (
            "public/index.html",
            "public/assets/ipulse-options-alpha-agent-cover.png",
            "public/assets/ipulse-options-alpha-agent-49s-pitch.mp4",
            "public/assets/"
            "2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v01.pptx",
            "docs/judge_one_pager.md",
            "docs/presentation_outline.md",
            "docs/submission_assets/"
            "2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v01.pptx",
            "docs/demo_script.md",
            "docs/submission_draft.md",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("safe artifact", encoding="utf-8")
        performance = root / "artifacts/competition/performance.jsonl"
        performance.parent.mkdir(parents=True, exist_ok=True)
        performance.write_text(
            json.dumps(
                {
                    "event_type": "competition_performance",
                    "payload": {"baseline_ready": True, "issues": []},
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_passes_with_artifacts_baseline_and_public_urls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            env = {
                "IPULSE_PUBLIC_REPOSITORY_URL": "https://example.com/repo",
                "IPULSE_PUBLIC_DEMO_URL": "https://example.com/demo",
                "IPULSE_DEMO_VIDEO_URL": "https://example.com/video",
                "IPULSE_SLIDES_URL": "https://example.com/slides",
            }
            with patch.dict(os.environ, env, clear=False):
                result = check_submission_readiness(root)

        self.assertTrue(result.ready)
        self.assertTrue(all(check.passed for check in result.checks))

    def test_fails_for_missing_urls_and_public_secret_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            (root / "public/index.html").write_text(
                "ALPACA_SECRET_KEY", encoding="utf-8"
            )
            with patch.dict(
                os.environ,
                {variable: "" for variable in (
                    "IPULSE_PUBLIC_REPOSITORY_URL",
                    "IPULSE_PUBLIC_DEMO_URL",
                    "IPULSE_DEMO_VIDEO_URL",
                    "IPULSE_SLIDES_URL",
                )},
                clear=False,
            ):
                result = check_submission_readiness(root)

        self.assertFalse(result.ready)
        failed = {check.name for check in result.checks if not check.passed}
        self.assertIn("public_artifact_safety", failed)
        self.assertIn("url:public_repository", failed)


if __name__ == "__main__":
    unittest.main()
