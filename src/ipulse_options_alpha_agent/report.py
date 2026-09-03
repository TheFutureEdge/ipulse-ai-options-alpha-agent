"""Static, dependency-free decision report for hackathon demonstrations."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ReportBuildError(RuntimeError):
    """Raised when a complete decision cycle cannot be recovered."""


@dataclass(frozen=True)
class DecisionReportData:
    """Latest complete cycle recovered from an append-only journal."""

    recorded_at_utc: str
    underlying: str
    evidence: tuple[Mapping[str, Any], ...]
    opinions: tuple[Mapping[str, Any], ...]
    consensus: Mapping[str, Any]
    operational_safety: Mapping[str, Any]
    decision: Mapping[str, Any]


def load_latest_decision_cycle(path: Path) -> DecisionReportData:
    """Read the latest complete advisory cycle from a bounded JSONL file."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReportBuildError(f"Cannot read evidence journal: {path}") from exc
    if not raw or len(raw) > 10_000_000:
        raise ReportBuildError("Evidence journal is empty or exceeds 10 MB.")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReportBuildError(
                f"Evidence journal line {line_number} is invalid JSON."
            ) from exc
        if isinstance(record, dict):
            records.append(record)
    context_indexes = [
        index
        for index, record in enumerate(records)
        if record.get("event_type") == "research_context"
    ]
    if not context_indexes:
        raise ReportBuildError("No research context exists in the journal.")
    start = context_indexes[-1]
    cycle = records[start:]
    by_type: dict[str, dict[str, Any]] = {}
    for record in cycle:
        event_type = record.get("event_type")
        if isinstance(event_type, str):
            by_type[event_type] = record
    required = {
        "research_context",
        "advisor_opinions",
        "advisor_consensus",
        "operational_safety",
        "agent_decision",
    }
    missing = required.difference(by_type)
    if missing:
        raise ReportBuildError(f"Latest cycle is incomplete: {sorted(missing)}")

    def payload(event_type: str) -> Mapping[str, Any]:
        value = by_type[event_type].get("payload")
        if not isinstance(value, dict):
            raise ReportBuildError(f"{event_type} payload is malformed.")
        return value

    context = payload("research_context")
    opinions_payload = payload("advisor_opinions").get("opinions")
    evidence_payload = context.get("evidence")
    if not isinstance(opinions_payload, list) or not isinstance(evidence_payload, list):
        raise ReportBuildError("Latest cycle opinions or evidence are malformed.")
    opinions = tuple(item for item in opinions_payload if isinstance(item, dict))
    evidence = tuple(item for item in evidence_payload if isinstance(item, dict))
    if not opinions or not evidence:
        raise ReportBuildError("Latest cycle has no opinions or evidence.")
    return DecisionReportData(
        recorded_at_utc=str(by_type["agent_decision"].get("recorded_at_utc", "")),
        underlying=str(context.get("underlying", "UNKNOWN")),
        evidence=evidence,
        opinions=opinions,
        consensus=payload("advisor_consensus"),
        operational_safety=payload("operational_safety"),
        decision=payload("agent_decision"),
    )


def load_latest_competition_snapshot(path: Path) -> Mapping[str, Any]:
    """Load the newest sanitized performance record from a JSONL journal."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ReportBuildError(f"Cannot read competition journal: {path}") from exc
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReportBuildError("Competition journal contains invalid JSON.") from exc
        if not isinstance(record, dict):
            continue
        if record.get("event_type") != "competition_performance":
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            return payload
    raise ReportBuildError("Competition journal has no performance snapshot.")


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _format_value(value: object, unit: object) -> str:
    if isinstance(value, float):
        rendered = f"{value:,.4f}".rstrip("0").rstrip(".")
    elif isinstance(value, dict):
        public_value = value
        if "headline" in value:
            public_value = {
                "headline": value.get("headline"),
                "sentiment_score": value.get("sentiment_score"),
            }
        rendered = json.dumps(public_value, sort_keys=True)
    else:
        rendered = str(value)
    return _escape(f"{rendered} {unit}".strip() if unit else rendered)


def _list_items(values: object) -> str:
    if not isinstance(values, (list, tuple)) or not values:
        return '<li class="muted">None recorded</li>'
    return "".join(f"<li>{_escape(value)}</li>" for value in values)


def render_decision_report(
    data: DecisionReportData,
    competition: Mapping[str, Any] | None = None,
    cover_image_url: str | None = None,
) -> str:
    """Render one self-contained HTML report with all external text escaped."""

    action = str(data.decision.get("action", "UNKNOWN"))
    consensus_action = str(data.consensus.get("action", "UNKNOWN"))
    confidence = data.consensus.get("confidence", 0)
    safety_approved = bool(data.operational_safety.get("approved", False))
    action_class = action.lower() if action in {"APPROVE", "WAIT", "REJECT"} else "unknown"
    advisor_cards = []
    for opinion in data.opinions:
        advisor_action = str(opinion.get("action", "UNKNOWN"))
        advisor = str(opinion.get("advisor", "unknown")).replace("_", " ").title()
        advisor_cards.append(
            f"""
            <article class="advisor">
              <div class="advisor-head">
                <h3>{_escape(advisor)}</h3>
                <span class="pill {advisor_action.lower()}">{_escape(advisor_action)}</span>
              </div>
              <p class="confidence">Confidence {_escape(opinion.get('confidence', 0))}</p>
              <p>{_escape(opinion.get('thesis', ''))}</p>
              <details><summary>Evidence</summary><ul>{_list_items(opinion.get('evidence_refs'))}</ul></details>
              <details><summary>Contrary evidence</summary><ul>{_list_items(opinion.get('contrary_evidence'))}</ul></details>
              <details><summary>Invalidation</summary><ul>{_list_items(opinion.get('invalidation_conditions'))}</ul></details>
            </article>
            """
        )
    evidence_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('evidence_id', ''))}</td>
          <td>{_escape(item.get('category', ''))}</td>
          <td>{_format_value(item.get('value'), item.get('unit'))}</td>
          <td>{_escape(item.get('source', ''))}</td>
          <td>{_escape(item.get('as_of_utc', ''))}</td>
        </tr>
        """
        for item in data.evidence
    )
    performance_section = ""
    if competition is not None:
        pnl = float(competition.get("cumulative_pnl_usd", 0))
        pnl_class = "approve" if pnl >= 0 else "reject"
        issues = competition.get("issues")
        performance_section = f"""
  <h2>Competition paper account</h2>
  <section class="grid">
    <article class="panel"><h3>Paper P&amp;L</h3><p class="hero-action {pnl_class}">${_escape(f'{pnl:,.2f}')}</p><p>{_escape(competition.get('cumulative_return_pct', 0))}% return from the required $100,000 starting balance.</p></article>
    <article class="panel"><h3>Account baseline</h3><p>{'READY' if competition.get('baseline_ready') else 'REVIEW REQUIRED'}</p><p>Options level {_escape(competition.get('options_trading_level', 'unknown'))} · {_escape(competition.get('open_positions', 0))} positions · {_escape(competition.get('filled_orders', 0))} filled orders</p><ul>{_list_items(issues)}</ul></article>
  </section>
"""
    cover = (
        f'<img class="cover" src="{_escape(cover_image_url)}" alt="iPulse AI Options Alpha Agent architecture cover">'
        if cover_image_url
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="description" content="Inspectable multi-advisor options research and Alpaca paper-trading decisions from iPulse AI.">
  <meta property="og:title" content="iPulse AI Options Alpha Agent">
  <meta property="og:description" content="Every signal, dissent, risk gate, paper order and result is inspectable.">
  <meta property="og:type" content="website">
  <title>iPulse AI Decision Report — {_escape(data.underlying)}</title>
  <script type="application/ld+json">{{"@context":"https://schema.org","@type":"SoftwareApplication","name":"iPulse AI Options Alpha Agent","applicationCategory":"FinanceApplication","operatingSystem":"Web","license":"https://opensource.org/license/mit","description":"Inspectable autonomous options research and Alpaca paper-trading agent."}}</script>
  <style>
    :root {{ color-scheme: dark; --bg:#080b12; --panel:#111722; --line:#263044; --text:#eef3ff; --muted:#9ca9bd; --cyan:#55d6ff; --green:#53e6a2; --amber:#ffc857; --red:#ff6b7d; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:radial-gradient(circle at 15% 0,#10273a 0,transparent 34%),var(--bg); color:var(--text); font:15px/1.55 Inter,ui-sans-serif,system-ui,sans-serif; }}
    main {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; padding:48px 0 80px; }}
    .eyebrow {{ color:var(--cyan); letter-spacing:.14em; text-transform:uppercase; font-size:12px; }} h1 {{ margin:.2em 0; font-size:clamp(38px,8vw,80px); line-height:.95; }} h2 {{ margin-top:48px; }}
    .cover {{ width:100%; height:auto; border:1px solid var(--line); border-radius:18px; margin:0 0 34px; box-shadow:0 18px 70px rgba(0,0,0,.32); }}
    .hero,.advisor,.panel {{ background:rgba(17,23,34,.9); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 70px rgba(0,0,0,.24); }}
    .hero {{ padding:28px; display:grid; grid-template-columns:1fr auto; gap:20px; align-items:center; }} .hero-action {{ font-size:34px; font-weight:800; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }} .advisor {{ padding:20px; }} .advisor-head {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    .advisor h3 {{ margin:0; }} .pill {{ border:1px solid var(--line); border-radius:999px; padding:5px 10px; font-size:12px; font-weight:800; }} .call,.approve {{ color:var(--green); }} .put,.reject {{ color:var(--red); }} .wait {{ color:var(--amber); }} .abstain {{ color:var(--muted); }}
    .confidence,.muted {{ color:var(--muted); }} details {{ border-top:1px solid var(--line); padding-top:10px; margin-top:10px; }} summary {{ cursor:pointer; color:var(--cyan); }}
    .panel {{ padding:18px; overflow:auto; }} table {{ width:100%; border-collapse:collapse; min-width:900px; }} th,td {{ text-align:left; padding:11px 12px; border-bottom:1px solid var(--line); vertical-align:top; }} th {{ color:var(--cyan); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    footer {{ color:var(--muted); margin-top:40px; border-top:1px solid var(--line); padding-top:20px; }}
    @media(max-width:640px) {{ .hero {{ grid-template-columns:1fr; }} main {{ width:min(100% - 20px,1180px); padding-top:28px; }} }}
  </style>
</head>
<body><main>
  {cover}
  <p class="eyebrow">Open Agentic Investment Research Platform</p>
  <h1>{_escape(data.underlying)} decision trace</h1>
  <section class="hero">
    <div><p class="muted">Recorded {_escape(data.recorded_at_utc)}</p><div class="hero-action {action_class}">{_escape(action)}</div><p>{_escape(data.decision.get('explanation', ''))}</p></div>
    <div><strong>Consensus {_escape(consensus_action)}</strong><br>Confidence {_escape(confidence)}<br>Operational safety {'PASS' if safety_approved else 'VETO'}</div>
  </section>
  <h2>Independent advisors</h2><section class="grid">{''.join(advisor_cards)}</section>
  <h2>Consensus and deterministic safety</h2>
  <section class="grid">
    <article class="panel"><h3>Consensus</h3><p>{_escape(data.consensus.get('rationale', ''))}</p><h4>Hard vetoes</h4><ul>{_list_items(data.consensus.get('hard_vetoes'))}</ul></article>
    <article class="panel"><h3>Operational safety</h3><p>{'Approved' if safety_approved else 'Execution forbidden'}</p><ul>{_list_items(data.operational_safety.get('reasons'))}</ul></article>
  </section>
{performance_section}
  <h2>Evidence catalog</h2><section class="panel"><table><thead><tr><th>ID</th><th>Category</th><th>Value</th><th>Source</th><th>As of</th></tr></thead><tbody>{evidence_rows}</tbody></table></section>
  <footer>Research and simulated paper trading only. Not investment advice. Missing or stale evidence results in ABSTAIN or WAIT.</footer>
</main></body></html>"""


def build_decision_report(
    journal_path: Path,
    output_path: Path,
    competition_journal_path: Path | None = None,
    cover_image_url: str | None = None,
) -> Path:
    """Build the latest report atomically enough for local demonstration use."""

    data = load_latest_decision_cycle(journal_path)
    competition = (
        load_latest_competition_snapshot(competition_journal_path)
        if competition_journal_path is not None and competition_journal_path.exists()
        else None
    )
    rendered = render_decision_report(data, competition, cover_image_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(rendered, encoding="utf-8")
    temporary_path.replace(output_path)
    return output_path
