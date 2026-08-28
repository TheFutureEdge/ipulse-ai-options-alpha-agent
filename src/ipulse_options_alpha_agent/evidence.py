"""Append-only local evidence journal for inspectable decisions."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent import AgentDecision


class EvidenceJournal:
    """Persist one JSON object per decision without storing credentials."""

    def __init__(self, path: Path) -> None:
        """Initialize the journal at an explicit local artifact path."""

        self.path = path

    def append(self, decision: AgentDecision) -> None:
        """Append a timestamped decision record to the JSONL journal."""

        self.append_record("agent_decision", asdict(decision))

    def append_record(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a sanitized generic event to the same evidence stream."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
