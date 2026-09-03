# Delivery Board to Final Submission

Last updated: 28 August 2026, 13:25 GST
Hard deadline: 4 September 2026, 19:00 GST
Internal submission target: 4 September 2026, 16:00 GST

## Current scorecard

| Workstream | State | Exit condition |
| --- | --- | --- |
| Competition eligibility | DONE | Dedicated active Alpaca paper account, USD 100,000 baseline, options enabled |
| Core agent | DONE | Six advisors, consensus, deterministic risk authority, WAIT/REJECT path |
| Alpaca/MCP integration | READY, LOCAL KEY HANDOFF PENDING | Local runtime receives dedicated paper API credentials and completes status check |
| Autonomous runner | DONE | Finite 1-78 cycle runner; cooldown and failure stop enforced |
| Competition telemetry | DONE | Sanitized baseline/P&L journal; raw identifiers excluded |
| Public dashboard | LOCALLY READY | Public HTTPS URL works signed out on desktop/mobile |
| Repository | LOCALLY READY | Public GitHub URL, clean clone, tests pass, no secrets |
| Paper evidence | MARKET-HOURS NEXT | At least one bounded rehearsal; strategy order only if evidence approves |
| One-page write-up | DONE | Technical brief matches running code |
| Cover image | DONE | Correct 16:9 cover, no broker logo or performance claim |
| Slides | OUTLINE READY, EDITABLE FILE BLOCKED | Public slide URL works signed out |
| Demo video | SCRIPT READY | Public/unlisted video URL works signed out |
| Social links | COPY PACKAGE READY | Up to five verified public posts; no placeholder facts |
| Lablab form | PENDING FINAL URLS | Every field complete and audited before submit |

## Execution order

### Gate 1 - Local Alpaca credentials

Create a dedicated paper API key in Alpaca and provide it only through the local
runtime environment as `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`. Do not paste it
into source, chat copy, a document, a screenshot, or the repository. Verify with:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent status
```

Exit: local MCP connects to the verified competition account and the sanitized
status matches the competition journal.

### Gate 2 - Market-hours rehearsal

Regular US trading opens at 09:30 ET / 17:30 GST on 28 August. First run the
read-only decision:

```bash
PYTHONPATH=src python -m ipulse_options_alpha_agent evaluate-advisors-market
```

If and only if the complete decision is APPROVE, the paper switches may be
enabled for one cycle:

```bash
IPULSE_ENABLE_PAPER_EXECUTION=true \
IPULSE_ALPACA_ENVIRONMENT=paper \
PYTHONPATH=src python -m ipulse_options_alpha_agent run-paper-once
```

Never change the signal, quote, size, or gates just to obtain a fill. A WAIT is
a successful safety result.

Exit: complete cycle journal, broker verification if an order is approved, and
fresh `competition-status` snapshot.

### Gate 3 - Public release

1. Review and commit the local repository.
2. Create/push the public GitHub repository.
3. Enable GitHub Pages using the included workflow.
4. Test repository and demo in a signed-out browser.
5. Record URLs in the readiness environment variables.

Exit: repository and demo URL checks pass.

### Gate 4 - Presentation and video

1. Build the editable seven-slide deck from `presentation_outline.md`.
2. Export a public PDF or hosted slide link.
3. Record the three-minute path in `demo_script.md`.
4. Upload the video as public or unlisted and verify signed-out access.

Exit: slide and video URL checks pass.

### Gate 5 - Social proof

Use the approval package in the social workspace. Publish only claims supported
by the current journal. Unlock post 4 only after a real strategy-generated
options order. Unlock post 5 only after the final account snapshot.

Exit: each submitted X/LinkedIn URL opens publicly and tags both lablab.ai and
Alpaca.

### Gate 6 - Final form

1. Capture the final Alpaca competition snapshot.
2. Rebuild the public dashboard.
3. Run all tests, compile check, secret scan, clean clone, and URL audit.
4. Run `submission-readiness`; require every check to pass.
5. Complete the Lablab form without submitting, then audit it signed out.
6. Submit by 16:00 GST on 4 September and preserve the confirmation.

## Stop conditions

- Live environment detected.
- Market closed or quote older than 120 seconds.
- Missing broker/recent-order state.
- Duplicate option signal, pending order, or cooldown violation.
- Maximum loss over USD 500, more than one contract, or non-limit order.
- Daily loss circuit breaker or position cap reached.
- Public artifact exposes a credential or raw account identifier.
- Any required URL is private, broken, or still contains placeholder content.
