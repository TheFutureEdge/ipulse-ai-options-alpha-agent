"""Command-line entrypoints for status and non-executing demonstrations."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .agent import AgentDecision, OptionsAlphaAgent
from .competition import build_competition_snapshot
from .domain import (
    AssetClass,
    PortfolioSnapshot,
    TradeProposal,
    TradeSide,
)
from .evidence import EvidenceJournal
from .evidence_sources import EvidenceLoadError, load_json_research_evidence
from .execution import (
    ExecutionBlockedError,
    ExecutionMode,
    ExecutionPolicy,
    PaperOrderExecutor,
)
from .market import AlpacaMarketAdapter, MarketSignalUnavailable
from .ipulse_evidence import (
    IPulseEvidenceUnavailable,
    load_ipulse_fund_research_evidence,
)
from .news import merge_news_evidence, normalize_alpaca_news
from .pipeline import MultiAdvisorPipeline
from .research import (
    FinancialEvidence,
    FundEvidence,
    FundValuationEvidence,
    NewsEvidence,
    OperationalState,
    ResearchContext,
    ValuationEvidence,
)
from .report import build_decision_report
from .readiness import check_submission_readiness
from .risk import RiskGate
from .session import SessionPolicy, run_bounded_session
from .strategy import StrategySignal


def find_value(payload: object, key: str) -> object | None:
    """Find the first matching key in a nested MCP response."""

    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = find_value(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_value(value, key)
            if found is not None:
                return found
    return None


def count_positions(payload: object) -> int:
    """Count distinct position records in a nested MCP response."""

    if isinstance(payload, dict):
        if "symbol" in payload and "qty" in payload:
            return 1
        return sum(count_positions(value) for value in payload.values())
    if isinstance(payload, list):
        return sum(count_positions(value) for value in payload)
    return 0


def require_float(payload: object, key: str) -> float:
    """Extract one required broker number or fail closed."""

    value = find_value(payload, key)
    if value is None:
        raise RuntimeError(f"Alpaca account response is missing {key}.")
    return float(str(value))


def count_order_records(payload: object) -> int:
    """Count broker order objects without depending on response wrappers."""

    if isinstance(payload, dict):
        if "id" in payload and "status" in payload and "symbol" in payload:
            return 1
        return sum(count_order_records(value) for value in payload.values())
    if isinstance(payload, list):
        return sum(count_order_records(value) for value in payload)
    return 0


def extract_order_records(payload: object) -> tuple[dict[str, object], ...]:
    """Extract broker order records from arbitrary MCP response wrappers."""

    records: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if "id" in payload and "status" in payload and "symbol" in payload:
            records.append(payload)
        else:
            for value in payload.values():
                records.extend(extract_order_records(value))
    elif isinstance(payload, list):
        for value in payload:
            records.extend(extract_order_records(value))
    return tuple(records)


def count_filled_orders(records: tuple[dict[str, object], ...]) -> int:
    """Count filled paper orders in a bounded recent-order response."""

    return sum(
        str(record.get("status", "")).lower() == "filled" for record in records
    )


def duplicate_option_signal(
    records: tuple[dict[str, object], ...], option_symbol: str
) -> bool:
    """Treat any recent order for the same contract as already processed."""

    return any(
        str(record.get("symbol", "")).upper() == option_symbol.upper()
        for record in records
    )


def minutes_since_last_fill(
    records: tuple[dict[str, object], ...], *, now: datetime | None = None
) -> float | None:
    """Return time since the most recent fill, or None when no fill exists."""

    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    timestamps: list[datetime] = []
    for record in records:
        if str(record.get("status", "")).lower() != "filled":
            continue
        raw = record.get("filled_at")
        if raw is None:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            timestamps.append(parsed.astimezone(UTC))
    if not timestamps:
        return None
    return max(0, (effective_now - max(timestamps)).total_seconds() / 60)


def parse_bool(value: object | None) -> bool:
    """Normalize a broker boolean without treating arbitrary text as true."""

    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


def quote_age_seconds(timestamp: str | None) -> float:
    """Return quote age or a deliberately stale sentinel when timing is absent."""

    if not timestamp:
        return 999_999
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 999_999
    return max(0, (datetime.now(UTC) - parsed.astimezone(UTC)).total_seconds())


def demo_research_context(*, market_open: bool = True) -> ResearchContext:
    """Return a complete six-advisor fixture with explicit source lineage."""

    now = datetime.now(UTC)
    return ResearchContext(
        underlying="SPY",
        signal=StrategySignal(
            underlying="SPY",
            option_symbol="SPY260904C00772000",
            option_limit_price=2.50,
            fast_return_pct=0.62,
            slow_return_pct=1.15,
            realized_volatility_pct=18.5,
            option_spread_pct=3.0,
            confidence=0.82,
        ),
        as_of_utc=now.isoformat(),
        operational=OperationalState(
            market_open=market_open,
            quote_age_seconds=8,
            daily_trade_count=0,
            duplicate_signal=False,
            open_order_count=0,
            minutes_since_last_trade=None,
        ),
        news=(
            NewsEvidence(
                evidence_id="news:demo-primary-1",
                headline="Broad-market earnings revisions remain positive",
                summary="Demonstration evidence for the advisor contract only.",
                source="demo_primary_source",
                published_at_utc=(now - timedelta(hours=2)).isoformat(),
                sentiment_score=0.35,
            ),
        ),
        financials=FinancialEvidence(
            as_of_date="2026-06-30",
            source_ids=("demo:aggregate-financials",),
            revenue_growth_pct=10,
            gross_margin_pct=52,
            operating_margin_pct=20,
            free_cash_flow_margin_pct=16,
            cash_conversion_pct=92,
            accrual_ratio_pct=3,
            net_debt_to_ebitda=1.1,
            share_count_growth_pct=0.4,
            roic_pct=13,
        ),
        valuation=ValuationEvidence(
            as_of_date="2026-08-27",
            source_ids=("demo:value-model-v1",),
            market_price=80,
            estimated_fair_value=100,
            forward_pe=16,
            sector_median_forward_pe=20,
            ev_to_ebitda=10,
            sector_median_ev_to_ebitda=12,
            free_cash_flow_yield_pct=5,
            earnings_growth_pct=9,
        ),
    )


async def show_status() -> None:
    """Verify MCP connectivity and print only non-sensitive account state."""

    from .mcp_client import AlpacaMcpClient

    async with AlpacaMcpClient() as client:
        tools = await client.list_tool_names()
        account = await client.call_json("get_account_info", {})
        summary = {
            "connected": True,
            "tool_count": len(tools),
            "options_data_available": "get_option_contracts" in tools,
            "order_placement_enabled": any(name.startswith("place_") for name in tools),
            "status": find_value(account, "status"),
            "currency": find_value(account, "currency"),
            "cash": find_value(account, "cash"),
            "buying_power": find_value(account, "buying_power"),
            "trading_blocked": find_value(account, "trading_blocked"),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))


async def capture_competition_status() -> None:
    """Record a sanitized eligibility and P&L snapshot from Alpaca MCP."""

    from .mcp_client import AlpacaMcpClient

    journal = EvidenceJournal(Path("artifacts/competition/performance.jsonl"))
    async with AlpacaMcpClient() as client:
        account = await client.call_json("get_account_info", {})
        positions = await client.call_json_value("get_all_positions", {})
        orders = await client.call_json(
            "get_orders", {"status": "all", "limit": 500, "nested": True}
        )
        activities = await client.call_json(
            "get_account_activities",
            {
                "after": "2026-08-28",
                "page_size": 100,
                "direction": "asc",
            },
        )
        snapshot = build_competition_snapshot(
            account=account,
            positions=positions,
            orders=orders,
            activities=activities,
            captured_at_utc=datetime.now(UTC).isoformat(),
        )
        journal.append_record("competition_performance", asdict(snapshot))
        print(
            json.dumps(
                {
                    "competition": asdict(snapshot),
                    "evidence_path": str(journal.path),
                },
                indent=2,
                sort_keys=True,
            )
        )


async def submit_paper_smoke() -> None:
    """Submit one non-marketable share as a paper connectivity proof."""

    from .mcp_client import AlpacaMcpClient

    execution_enabled = os.environ.get("IPULSE_ENABLE_PAPER_EXECUTION") == "true"
    paper_environment = os.environ.get("IPULSE_ALPACA_ENVIRONMENT") == "paper"
    journal = EvidenceJournal(
        Path("artifacts/decisions/paper_execution_evidence.jsonl")
    )

    async with AlpacaMcpClient() as client:
        tools = await client.list_tool_names()
        if "place_stock_order" not in tools:
            raise RuntimeError("Configured Alpaca MCP server has no stock order tool.")
        account = await client.call_json("get_account_info", {})
        positions = await client.call_json_value("get_all_positions", {})
        equity = require_float(account, "equity")
        last_equity = require_float(account, "last_equity")
        portfolio = PortfolioSnapshot(
            equity=equity,
            cash=require_float(account, "cash"),
            buying_power=require_float(account, "buying_power"),
            daily_pnl=equity - last_equity,
            open_positions=count_positions(positions),
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        proposal = TradeProposal(
            client_order_id=f"ipulse-paper-smoke-spy-{timestamp}",
            strategy_name="paper_connectivity_smoke_v0",
            underlying="SPY",
            symbol="SPY",
            asset_class=AssetClass.EQUITY,
            side=TradeSide.BUY,
            quantity=1,
            order_type="limit",
            time_in_force="day",
            estimated_entry_price=1.0,
            max_loss_amount=1.0,
            confidence=1.0,
            rationale=(
                "Non-marketable one-share paper order used only to prove the "
                "risk-gated Alpaca MCP execution path."
            ),
        )
        risk = RiskGate().evaluate(
            proposal,
            portfolio,
            paper_environment=paper_environment,
        )
        decision = AgentDecision(
            action="APPROVE" if risk.approved else "REJECT",
            proposal=proposal,
            risk=risk,
            explanation=(
                "Paper connectivity smoke passed every risk gate."
                if risk.approved
                else "Paper connectivity smoke was rejected by the risk gate."
            ),
        )
        journal.append(decision)
        receipt = await PaperOrderExecutor(client).submit(
            decision,
            ExecutionPolicy(
                enabled=execution_enabled,
                paper_environment=paper_environment,
                mode=ExecutionMode.CONNECTIVITY_SMOKE,
            ),
        )
        journal.append_record("broker_order_receipt", asdict(receipt))
        verification: dict[str, object] = {}
        if receipt.broker_order_id:
            order = await client.call_json(
                "get_order_by_id",
                {"order_id": receipt.broker_order_id, "nested": False},
            )
            verification = {
                "broker_order_id": receipt.broker_order_id,
                "status": find_value(order, "status"),
                "symbol": find_value(order, "symbol"),
                "side": find_value(order, "side"),
                "order_type": find_value(order, "type"),
                "limit_price": find_value(order, "limit_price"),
                "quantity": find_value(order, "qty"),
            }
            journal.append_record("broker_order_verification", verification)

        print(
            json.dumps(
                {
                    "submitted": True,
                    "paper_environment": paper_environment,
                    "risk_approved": risk.approved,
                    "estimated_max_loss": proposal.max_loss_amount,
                    "receipt": asdict(receipt),
                    "verification": verification,
                    "evidence_path": str(journal.path),
                },
                indent=2,
                sort_keys=True,
            )
        )


async def evaluate_market() -> None:
    """Build and record one read-only decision from live Alpaca market data."""

    from .mcp_client import AlpacaMcpClient

    journal = EvidenceJournal(Path("artifacts/decisions/market_evidence.jsonl"))
    async with AlpacaMcpClient() as client:
        account = await client.call_json("get_account_info", {})
        positions = await client.call_json_value("get_all_positions", {})
        equity = require_float(account, "equity")
        portfolio = PortfolioSnapshot(
            equity=equity,
            cash=require_float(account, "cash"),
            buying_power=require_float(account, "buying_power"),
            daily_pnl=equity - require_float(account, "last_equity"),
            open_positions=count_positions(positions),
        )
        try:
            signal = await AlpacaMarketAdapter(client).build_signal("SPY")
        except MarketSignalUnavailable as exc:
            journal.append_record(
                "market_signal_unavailable", {"underlying": "SPY", "reason": str(exc)}
            )
            print(
                json.dumps(
                    {"action": "WAIT", "reason": str(exc), "executed": False},
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        decision = OptionsAlphaAgent().decide(
            signal,
            portfolio,
            paper_environment=True,
        )
        journal.append_record("normalized_market_signal", asdict(signal))
        journal.append(decision)
        print(
            json.dumps(
                {
                    "decision": asdict(decision),
                    "executed": False,
                    "evidence_path": str(journal.path),
                },
                indent=2,
                sort_keys=True,
            )
        )


async def evaluate_advisors_market(
    *, execute: bool = False, print_result: bool = True
) -> dict[str, object]:
    """Run all six advisors and optionally submit one fully gated paper order."""

    from .mcp_client import AlpacaMcpClient

    journal = EvidenceJournal(Path("artifacts/decisions/advisor_market_evidence.jsonl"))
    async with AlpacaMcpClient() as client:
        account = await client.call_json("get_account_info", {})
        positions = await client.call_json_value("get_all_positions", {})
        clock = await client.call_json("get_clock", {})
        open_orders = await client.call_json("get_orders", {"status": "open", "limit": 50})
        recent_orders_available = True
        try:
            recent_orders_payload = await client.call_json(
                "get_orders",
                {
                    "status": "all",
                    "limit": 100,
                    "after": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                    "direction": "desc",
                },
            )
        except RuntimeError as exc:
            recent_orders_available = False
            recent_orders_payload = {}
            journal.append_record(
                "recent_order_state_unavailable",
                {"reason": str(exc), "executed": False},
            )
        portfolio = PortfolioSnapshot(
            equity=require_float(account, "equity"),
            cash=require_float(account, "cash"),
            buying_power=require_float(account, "buying_power"),
            daily_pnl=(
                require_float(account, "equity")
                - require_float(account, "last_equity")
            ),
            open_positions=count_positions(positions),
        )
        try:
            evaluation = await AlpacaMarketAdapter(client).build_evaluation("SPY")
        except MarketSignalUnavailable as exc:
            journal.append_record(
                "advisor_market_signal_unavailable",
                {"underlying": "SPY", "reason": str(exc)},
            )
            result: dict[str, object] = {
                "action": "WAIT",
                "reason": str(exc),
                "execution": {"requested": execute, "submitted": False},
            }
            if print_result:
                print(json.dumps(result, indent=2, sort_keys=True))
            return result
        recent_orders = extract_order_records(recent_orders_payload)
        news_status: dict[str, object] = {"loaded": False, "count": 0}
        try:
            alpaca_news_payload = await client.call_json(
                "get_news",
                {
                    "symbols": "SPY",
                    "start": (datetime.now(UTC) - timedelta(days=3)).isoformat(),
                    "sort": "desc",
                    "limit": 10,
                    "include_content": False,
                    "exclude_contentless": False,
                },
            )
        except RuntimeError as exc:
            alpaca_news = ()
            news_status["error"] = str(exc)
            journal.append_record(
                "alpaca_news_unavailable",
                {"reason": str(exc), "executed": False},
            )
        else:
            alpaca_news = normalize_alpaca_news(
                alpaca_news_payload, underlying="SPY"
            )
            news_status.update({"loaded": True, "count": len(alpaca_news)})
            journal.append_record(
                "normalized_alpaca_news",
                {"items": [asdict(item) for item in alpaca_news]},
            )
        evidence_status: dict[str, object] = {
            "configured": False,
            "loaded": False,
        }
        news: tuple[NewsEvidence, ...] = alpaca_news
        financials: FinancialEvidence | None = None
        fund: FundEvidence | None = None
        valuation: ValuationEvidence | None = None
        fund_valuation: FundValuationEvidence | None = None
        ipulse_fund_status: dict[str, object] = {
            "configured": False,
            "loaded": False,
        }
        if os.environ.get("IPULSE_ENABLE_BIGQUERY_EVIDENCE") == "true":
            ipulse_fund_status["configured"] = True
            try:
                fund_research = await asyncio.to_thread(
                    load_ipulse_fund_research_evidence, "SPY"
                )
            except IPulseEvidenceUnavailable as exc:
                ipulse_fund_status["error"] = str(exc)
                journal.append_record(
                    "ipulse_fund_evidence_unavailable",
                    {"reason": str(exc), "executed": False},
                )
            else:
                fund = fund_research.fund
                fund_valuation = fund_research.valuation
                ipulse_fund_status.update(
                    {
                        "loaded": True,
                        "as_of_date": fund.as_of_date,
                        "source_ids": list(fund.source_ids),
                        "has_valuation": fund_valuation is not None,
                    }
                )
                journal.append_record(
                    "ipulse_fund_evidence_loaded", asdict(fund)
                )
        configured_evidence_path = os.environ.get("IPULSE_RESEARCH_EVIDENCE_FILE")
        if configured_evidence_path:
            evidence_status["configured"] = True
            try:
                bundle = load_json_research_evidence(
                    Path(configured_evidence_path), underlying="SPY"
                )
            except EvidenceLoadError as exc:
                evidence_status["error"] = str(exc)
                journal.append_record(
                    "research_evidence_rejected",
                    {"reason": str(exc), "executed": False},
                )
            else:
                news = merge_news_evidence(alpaca_news, bundle.news)
                financials = bundle.financials
                if bundle.fund is not None:
                    fund = bundle.fund
                valuation = bundle.valuation
                if bundle.fund_valuation is not None:
                    fund_valuation = bundle.fund_valuation
                evidence_status.update(
                    {
                        "loaded": True,
                        "document_sha256": bundle.document_sha256,
                        "generated_at_utc": bundle.generated_at_utc,
                    }
                )
                journal.append_record(
                    "research_evidence_loaded",
                    {
                        "document_sha256": bundle.document_sha256,
                        "generated_at_utc": bundle.generated_at_utc,
                        "news_count": len(bundle.news),
                        "has_financials": bundle.financials is not None,
                        "has_fund": bundle.fund is not None,
                        "has_fund_valuation": bundle.fund_valuation is not None,
                        "has_valuation": bundle.valuation is not None,
                    },
                )
        context = ResearchContext(
            underlying="SPY",
            signal=evaluation.signal,
            as_of_utc=datetime.now(UTC).isoformat(),
            operational=OperationalState(
                market_open=parse_bool(find_value(clock, "is_open")),
                quote_age_seconds=quote_age_seconds(
                    evaluation.selected_option.quote_timestamp_utc
                ),
                daily_trade_count=(
                    count_filled_orders(recent_orders)
                    if recent_orders_available
                    else None
                ),
                duplicate_signal=(
                    duplicate_option_signal(
                        recent_orders, evaluation.selected_option.symbol
                    )
                    if recent_orders_available
                    else None
                ),
                open_order_count=count_order_records(open_orders),
                minutes_since_last_trade=(
                    minutes_since_last_fill(recent_orders)
                    if recent_orders_available
                    else None
                ),
            ),
            news=news,
            financials=financials,
            fund=fund,
            valuation=valuation,
            fund_valuation=fund_valuation,
        )
        run = await MultiAdvisorPipeline().run(
            context,
            portfolio,
            paper_environment=True,
        )
        journal.append_record("research_context", context.prompt_payload())
        journal.append_record(
            "advisor_opinions", {"opinions": [asdict(item) for item in run.opinions]}
        )
        journal.append_record("advisor_consensus", asdict(run.consensus))
        journal.append_record(
            "operational_safety", asdict(run.operational_safety)
        )
        journal.append(run.decision)
        execution_result: dict[str, object] = {
            "requested": execute,
            "submitted": False,
        }
        if execute and run.decision.action == "APPROVE":
            try:
                receipt = await PaperOrderExecutor(client).submit(
                    run.decision,
                    ExecutionPolicy(
                        enabled=(
                            os.environ.get("IPULSE_ENABLE_PAPER_EXECUTION") == "true"
                        ),
                        paper_environment=(
                            os.environ.get("IPULSE_ALPACA_ENVIRONMENT") == "paper"
                        ),
                        mode=ExecutionMode.STRATEGY,
                        operational_safety=run.operational_safety,
                    ),
                )
            except ExecutionBlockedError as exc:
                execution_result["blocked_reason"] = str(exc)
                journal.append_record(
                    "strategy_execution_blocked",
                    {"reason": str(exc), "executed": False},
                )
            else:
                execution_result.update(
                    {
                        "submitted": True,
                        "receipt": asdict(receipt),
                    }
                )
                journal.append_record("broker_order_receipt", asdict(receipt))
                if receipt.broker_order_id:
                    verification = await client.call_json(
                        "get_order_by_id",
                        {"order_id": receipt.broker_order_id, "nested": False},
                    )
                    sanitized_verification = {
                        "broker_order_id": receipt.broker_order_id,
                        "status": find_value(verification, "status"),
                        "symbol": find_value(verification, "symbol"),
                        "side": find_value(verification, "side"),
                        "order_type": find_value(verification, "type"),
                        "limit_price": find_value(verification, "limit_price"),
                        "quantity": find_value(verification, "qty"),
                    }
                    execution_result["verification"] = sanitized_verification
                    journal.append_record(
                        "broker_order_verification", sanitized_verification
                    )
        result = {
            "opinions": [asdict(item) for item in run.opinions],
            "consensus": asdict(run.consensus),
            "operational_safety": asdict(run.operational_safety),
            "decision": asdict(run.decision),
            "external_research_evidence": evidence_status,
            "ipulse_fund_evidence": ipulse_fund_status,
            "alpaca_news": news_status,
            "execution": execution_result,
            "evidence_path": str(journal.path),
        }
        if print_result:
            print(json.dumps(result, indent=2, sort_keys=True))
        return result


async def run_paper_session(*, max_cycles: int, interval_seconds: int) -> None:
    """Run a finite autonomous session with execution and evidence gates on."""

    if os.environ.get("IPULSE_ENABLE_PAPER_EXECUTION") != "true":
        raise RuntimeError("IPULSE_ENABLE_PAPER_EXECUTION must explicitly be true.")
    if os.environ.get("IPULSE_ALPACA_ENVIRONMENT") != "paper":
        raise RuntimeError("IPULSE_ALPACA_ENVIRONMENT must explicitly be paper.")

    policy = SessionPolicy(
        max_cycles=max_cycles,
        interval_seconds=interval_seconds,
    )
    policy.validate()
    session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    journal = EvidenceJournal(Path("artifacts/competition/session.jsonl"))
    journal.append_record(
        "autonomous_session_started",
        {"session_id": session_id, "policy": asdict(policy)},
    )

    async def cycle(index: int) -> dict[str, object]:
        try:
            result = await evaluate_advisors_market(
                execute=True, print_result=False
            )
        except Exception as exc:
            journal.append_record(
                "autonomous_session_failed",
                {
                    "session_id": session_id,
                    "cycle": index,
                    "error_type": type(exc).__name__,
                    "reason": str(exc),
                },
            )
            raise
        decision = result.get("decision")
        execution = result.get("execution")
        summary = {
            "session_id": session_id,
            "cycle": index,
            "action": (
                decision.get("action") if isinstance(decision, dict) else result.get("action")
            ),
            "submitted": (
                bool(execution.get("submitted"))
                if isinstance(execution, dict)
                else False
            ),
            "evidence_path": result.get("evidence_path"),
        }
        journal.append_record("autonomous_session_cycle", summary)
        print(json.dumps(summary, sort_keys=True), flush=True)
        return summary

    results = await run_bounded_session(cycle, policy)
    submitted = sum(bool(item.get("submitted")) for item in results)
    final = {
        "session_id": session_id,
        "cycles_completed": len(results),
        "orders_submitted": submitted,
        "evidence_path": str(journal.path),
    }
    journal.append_record("autonomous_session_completed", final)
    print(json.dumps(final, indent=2, sort_keys=True))


async def evaluate_advisors_demo(*, use_llm: bool) -> None:
    """Run the complete six-advisor pipeline over explicit demonstration data."""

    advisors = None
    reasoning_mode = "deterministic"
    if use_llm:
        from .llm_advisors import create_prompted_advisors
        from .reasoning import OpenAIResponsesReasoningClient

        model = os.environ.get("IPULSE_OPENAI_MODEL", "gpt-5.4-mini")
        advisors = create_prompted_advisors(
            OpenAIResponsesReasoningClient(model=model)
        )
        reasoning_mode = model
    context = demo_research_context()
    portfolio = PortfolioSnapshot(
        equity=100_000,
        cash=100_000,
        buying_power=400_000,
        daily_pnl=0,
        open_positions=0,
    )
    run = await MultiAdvisorPipeline(advisors=advisors).run(
        context,
        portfolio,
        paper_environment=True,
    )
    print(
        json.dumps(
            {
                "reasoning_mode": reasoning_mode,
                "opinions": [asdict(item) for item in run.opinions],
                "consensus": asdict(run.consensus),
                "operational_safety": asdict(run.operational_safety),
                "decision": asdict(run.decision),
                "executed": False,
                "demo_data": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


def evaluate_demo() -> None:
    """Run a deterministic decision without calling a broker or placing an order."""

    signal = StrategySignal(
        underlying="SPY",
        option_symbol="SPY_DEMO_CALL",
        option_limit_price=2.25,
        fast_return_pct=0.52,
        slow_return_pct=0.91,
        realized_volatility_pct=21.0,
        option_spread_pct=3.5,
        confidence=0.76,
    )
    portfolio = PortfolioSnapshot(
        equity=100_000,
        cash=100_000,
        buying_power=400_000,
        daily_pnl=0,
        open_positions=0,
    )
    decision = OptionsAlphaAgent().decide(
        signal,
        portfolio,
        paper_environment=True,
    )
    print(json.dumps(asdict(decision), indent=2, sort_keys=True))


def build_report() -> None:
    """Render the most recent multi-advisor cycle as a static HTML report."""

    path = build_decision_report(
        Path("artifacts/decisions/advisor_market_evidence.jsonl"),
        Path("artifacts/report/latest_decision.html"),
        Path("artifacts/competition/performance.jsonl"),
        backtest_path=Path(
            "artifacts/backtests/exhaustion_reversal_v1_scorecard.json"
        ),
        live_fill_path=Path(
            "artifacts/competition/live_strategy_evidence.jsonl"
        ),
    )
    print(json.dumps({"report_path": str(path)}, indent=2))


def build_public_site() -> None:
    """Publish the latest sanitized evidence into the static site directory."""

    path = build_decision_report(
        Path("artifacts/decisions/advisor_market_evidence.jsonl"),
        Path("public/index.html"),
        Path("artifacts/competition/performance.jsonl"),
        "assets/ipulse-options-alpha-agent-cover.png",
        Path("artifacts/backtests/exhaustion_reversal_v1_scorecard.json"),
        Path("artifacts/competition/live_strategy_evidence.jsonl"),
    )
    print(json.dumps({"public_site_path": str(path)}, indent=2))


def show_submission_readiness() -> None:
    """Report final-submission gates without mutating external state."""

    result = check_submission_readiness(Path.cwd())
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


def main() -> None:
    """Parse and execute one explicit command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "status",
            "competition-status",
            "evaluate-demo",
            "evaluate-advisors-demo",
            "evaluate-ai-demo",
            "evaluate-advisors-market",
            "evaluate-market",
            "build-report",
            "build-public-site",
            "submission-readiness",
            "run-paper-once",
            "run-paper-session",
            "submit-paper-smoke",
        ),
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=12,
        help="Finite cycle count for run-paper-session (1-78).",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="Cooldown for run-paper-session (60-1800 seconds).",
    )
    args = parser.parse_args()
    if args.command == "status":
        asyncio.run(show_status())
    elif args.command == "competition-status":
        asyncio.run(capture_competition_status())
    elif args.command == "build-report":
        build_report()
    elif args.command == "build-public-site":
        build_public_site()
    elif args.command == "submission-readiness":
        show_submission_readiness()
    elif args.command == "evaluate-demo":
        evaluate_demo()
    elif args.command == "evaluate-advisors-demo":
        asyncio.run(evaluate_advisors_demo(use_llm=False))
    elif args.command == "evaluate-ai-demo":
        asyncio.run(evaluate_advisors_demo(use_llm=True))
    elif args.command == "evaluate-advisors-market":
        asyncio.run(evaluate_advisors_market(execute=False))
    elif args.command == "evaluate-market":
        asyncio.run(evaluate_market())
    elif args.command == "run-paper-once":
        asyncio.run(evaluate_advisors_market(execute=True))
    elif args.command == "run-paper-session":
        asyncio.run(
            run_paper_session(
                max_cycles=args.max_cycles,
                interval_seconds=args.interval_seconds,
            )
        )
    else:
        asyncio.run(submit_paper_smoke())


if __name__ == "__main__":
    main()
