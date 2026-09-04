"""Deterministic final-submission readiness checks."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


PUBLIC_URL_VARIABLES = {
    "public_repository": "IPULSE_PUBLIC_REPOSITORY_URL",
    "hosted_demo": "IPULSE_PUBLIC_DEMO_URL",
    "demo_video": "IPULSE_DEMO_VIDEO_URL",
    "slides": "IPULSE_SLIDES_URL",
}


@dataclass(frozen=True)
class ReadinessCheck:
    """One auditable submission prerequisite."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class SubmissionReadiness:
    """Complete local and external readiness result."""

    ready: bool
    checks: tuple[ReadinessCheck, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable report."""

        return {
            "ready": self.ready,
            "checks": [asdict(check) for check in self.checks],
        }


def _file_check(root: Path, relative_path: str) -> ReadinessCheck:
    path = root / relative_path
    exists = path.is_file() and path.stat().st_size > 0
    return ReadinessCheck(
        name=f"file:{relative_path}",
        passed=exists,
        detail="present and non-empty" if exists else "missing or empty",
    )


def _latest_competition_payload(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    latest: dict[str, object] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("event_type") != "competition_performance":
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            latest = payload
    return latest


def _account_check(root: Path) -> ReadinessCheck:
    payload = _latest_competition_payload(
        root / "artifacts/competition/performance.jsonl"
    )
    passed = bool(payload and payload.get("baseline_ready"))
    if payload is None:
        detail = "no competition performance snapshot"
    elif passed:
        detail = "sanitized $100,000 paper/options baseline is ready"
    else:
        issues = payload.get("issues")
        detail = f"competition baseline failed: {issues}"
    return ReadinessCheck("competition_account", passed, detail)


def _public_safety_check(root: Path) -> ReadinessCheck:
    public_root = root / "public"
    forbidden = (
        "ALPACA_SECRET_KEY",
        "ALPACA_API_KEY",
        "account_number",
        "account_id",
    )
    hits: list[str] = []
    for path in public_root.rglob("*") if public_root.is_dir() else ():
        if not path.is_file() or path.suffix.lower() not in {".html", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            if token in text:
                hits.append(f"{path.relative_to(root)}:{token}")
    return ReadinessCheck(
        "public_artifact_safety",
        not hits,
        "no credential/account tokens found" if not hits else ", ".join(hits),
    )


def _url_check(name: str, variable: str) -> ReadinessCheck:
    value = os.environ.get(variable, "").strip()
    passed = value.startswith("https://") and "[" not in value and "]" not in value
    return ReadinessCheck(
        name=f"url:{name}",
        passed=passed,
        detail=value if passed else f"set {variable} to a public HTTPS URL",
    )


def check_submission_readiness(root: Path) -> SubmissionReadiness:
    """Check every locally provable and URL-based submission prerequisite."""

    checks = [
        _file_check(root, "public/index.html"),
        _file_check(root, "public/assets/ipulse-options-alpha-agent-cover.png"),
        _file_check(
            root, "public/assets/ipulse-options-alpha-agent-judge-demo-v03.mp4"
        ),
        _file_check(
            root,
            "public/assets/"
            "2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pptx",
        ),
        _file_check(
            root,
            "public/assets/"
            "2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pdf",
        ),
        _file_check(root, "docs/judge_one_pager.md"),
        _file_check(root, "docs/presentation_outline.md"),
        _file_check(
            root,
            "docs/submission_assets/"
            "2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pptx",
        ),
        _file_check(
            root,
            "output/pdf/"
            "2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pdf",
        ),
        _file_check(root, "docs/demo_script.md"),
        _file_check(root, "docs/submission_draft.md"),
        _account_check(root),
        _public_safety_check(root),
    ]
    checks.extend(_url_check(name, variable) for name, variable in PUBLIC_URL_VARIABLES.items())
    result = tuple(checks)
    return SubmissionReadiness(
        ready=all(check.passed for check in result),
        checks=result,
    )
