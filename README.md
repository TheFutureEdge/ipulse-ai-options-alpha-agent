# iPulse AI Options Alpha Agent

An inspectable autonomous options research and paper-trading agent built for
the Alpaca AI Trading Agents Hackathon.

iPulse AI is an Open Agentic Investment Research Platform. This project makes
each signal, risk decision, rejected trade, paper order, and result inspectable.

## Safety baseline

- Paper trading is mandatory.
- Live trading fails closed.
- Order placement is disabled by default.
- The first execution policy permits only one-contract long options or one-share
  equity smoke tests.
- Every proposal passes deterministic portfolio risk gates before execution.
- Credentials stay outside the repository.

## Architecture

1. Alpaca adapter normalizes account, order, clock, bar, quote, and option data.
2. Live Alpaca news and strict adapters supply versioned financial, fund, and
   valuation inputs while rejecting stale or mismatched evidence.
3. Six independent advisors return structured CALL, PUT, WAIT, or ABSTAIN views:
   technical regime, news catalysts, options liquidity, financials forensic
   audit, value framework, and operational risk critic.
4. Evidence-aware consensus requires technical/options agreement, retains
   dissent, and respects hard vetoes.
5. Deterministic operational and portfolio gates retain final authority.
6. The Alpaca paper adapter can submit one bounded limit order only behind
   explicit paper switches; the evidence journal records the complete path.

OpenAI reasoning is optional. When configured, each advisor receives only the
bounded evidence catalog and must return strict JSON Schema output. Missing,
invalid, stale, or uncited evidence causes abstention or WAIT.

## Local validation

Use the existing workspace Python environment; do not create a new virtual
environment.

```bash
activate ipulse_scripts
cd /Users/russlan/Documents/futureedge/code/ipulse_ai_options_alpha_agent
PYTHONPATH=src python -m unittest discover -s tests -v
```

Run a non-executing decision demo:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent evaluate-demo
PYTHONPATH=src python -m ipulse_options_alpha_agent evaluate-advisors-demo
```

`evaluate-ai-demo` exercises the same six contracts through the OpenAI Responses
API when `OPENAI_API_KEY` is supplied by the runtime. No key is accepted as a
command-line argument or written to evidence.

Build and record a read-only decision from real Alpaca bars, stock quotes, and a
narrow options chain:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent evaluate-advisors-market
```

Capture a sanitized competition baseline and current paper P&L. Raw Alpaca
account identifiers are fingerprinted and never written to the public artifact:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent competition-status
PYTHONPATH=src python -m ipulse_options_alpha_agent build-report
```

Set `IPULSE_RESEARCH_EVIDENCE_FILE` to a fresh JSON document conforming to
[`docs/research_evidence.schema.json`](docs/research_evidence.schema.json) to
activate news, forensic-financial, and value analysis in that real-market run.
The boundary is designed for iPulse AI's existing annual/quarterly fundamentals
and derived-metrics pipeline; database credentials remain outside this agent.

For SPY/QQQ/IWM fund-structure audits, the optional read-only iPulse adapter
accepts only explicit non-secret table configuration:

```bash
IPULSE_ENABLE_BIGQUERY_EVIDENCE=true \
IPULSE_BQ_PROJECT_ID=your-project \
IPULSE_BQ_FUNDAMENTAL_DATASET=your-dataset \
PYTHONPATH=src python -m ipulse_options_alpha_agent evaluate-advisors-market
```

It maps expense ratio, turnover, assets, holdings count, top-ten and largest
holding concentration, largest sector weight, and cash allocation. It does not
pretend those are company income-statement metrics.

When a snapshot includes the supported `FundValuationGrowth` block, the same
read-only adapter also activates ETF relative-value analysis using prospective
P/E, price-to-cash-flow, cash-flow yield, and growth versus category.

Generate a self-contained HTML report from the latest evidence cycle:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent build-report
```

The report is written to `artifacts/report/latest_decision.html` and includes
all advisor views, dissent, vetoes, operational safety, and evidence lineage.

The MCP status command requires the `mcp` Python package and paper credentials
provided to the Alpaca MCP server by the local runtime:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent status
```

The paper connectivity proof is doubly gated. It requires the paper-only MCP
launcher plus both explicit environment switches. It submits one SPY share at a
non-marketable $1.00 DAY limit, records the broker response, and can never route
to a live environment:

```bash
IPULSE_ENABLE_PAPER_EXECUTION=true \
IPULSE_ALPACA_ENVIRONMENT=paper \
PYTHONPATH=src python -m ipulse_options_alpha_agent run-paper-once
```

`run-paper-once` is a single-cycle strategy path, not a daemon. It additionally
requires an open regular session, a quote no older than 120 seconds, no pending
order, fewer than three recent fills, no recent order for the same contract, a
15-minute cooldown, aligned advisor consensus, and every portfolio risk gate.
Use `submit-paper-smoke` only for the separate USD 1 connectivity proof.

Run a finite autonomous paper session only after the same two execution switches
are set. The runner is bounded to 1–78 cycles, enforces a 60–1,800 second
cooldown, records every cycle, stops on unexpected failure, and cannot bypass
the strategy's deterministic gates:

```bash
IPULSE_ENABLE_PAPER_EXECUTION=true \
IPULSE_ALPACA_ENVIRONMENT=paper \
PYTHONPATH=src python -m ipulse_options_alpha_agent run-paper-session \
  --max-cycles 12 --interval-seconds 300
```

## Hackathon submission targets

- Public MIT-licensed GitHub repository
- Hosted inspectable decision dashboard
- Alpaca paper account evidence
- Autonomous options strategy using Alpaca MCP
- One-page AI logic, risk-gate, and Alpaca infrastructure write-up
- Demo video and judge presentation

Public proof package:

- [Source repository](https://github.com/TheFutureEdge/ipulse-ai-options-alpha-agent)
- [Inspectable decision dashboard](https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/)
- [49-second visual walkthrough](https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/ipulse-options-alpha-agent-49s-pitch.mp4)
- [Judge presentation](https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v01.pdf)

The local judge deck is
[`docs/submission_assets/2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v01.pptx`](docs/submission_assets/2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v01.pptx).

The dated execution and submission sequence is maintained in
[`docs/submission_runbook.md`](docs/submission_runbook.md).

Audit the complete local package and the four required public URLs before the
final Lablab form is submitted:

```bash
IPULSE_PUBLIC_REPOSITORY_URL=https://github.com/TheFutureEdge/ipulse-ai-options-alpha-agent \
IPULSE_PUBLIC_DEMO_URL=https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/ \
IPULSE_DEMO_VIDEO_URL=https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/ipulse-options-alpha-agent-49s-pitch.mp4 \
IPULSE_SLIDES_URL=https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v01.pdf \
PYTHONPATH=src python -m ipulse_options_alpha_agent submission-readiness
```

The check fails until every required local artifact, the sanitized competition
baseline, the public-artifact safety scan, and all four public HTTPS URLs pass.

This software is for research and simulated paper trading only. It is not
investment advice.
