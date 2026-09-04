# Delivery Board to Final Submission

Last updated: 4 September 2026
Hard deadline: 4 September 2026, 19:00 GST
Internal submission target: 4 September 2026, 16:00 GST

## Current scorecard

| Workstream | State | Exit condition |
| --- | --- | --- |
| Competition eligibility | DONE | Dedicated active Alpaca paper account, USD 100,000 baseline, options enabled |
| Core agent | DONE | Six advisors, consensus, deterministic risk authority, WAIT/REJECT path |
| Alpaca/MCP integration | DONE | Official MCP path, paper account reads, order receipts, and sanitized status verified |
| Autonomous runner | DONE | Finite 1-78 cycle runner; cooldown and failure stop enforced |
| Competition telemetry | DONE | Sanitized baseline/P&L journal; raw identifiers excluded |
| Public dashboard | DONE | Public HTTPS URL works signed out |
| Repository | DONE | Public GitHub URL, tests pass, no public secrets |
| Paper evidence | DONE | Three exploratory v0 fills retained; latest frozen v1 decision is WAIT |
| One-page write-up | DONE | Technical brief matches running code |
| Cover image | DONE | Correct 16:9 cover, no broker logo or performance claim |
| Slides | FINAL V06 READY | Ten-slide editable deck and PDF work without authentication |
| Demo video | FINAL V03 READY | 4:54 video and English captions work without authentication |
| Social links | COPY PACKAGE READY | Up to five verified public posts; no placeholder facts |
| Lablab form | FINAL ACTION | Corrected copy, private account ID, assets, and final Submit confirmation |

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

1. Use the editable ten-slide deck in `docs/submission_assets`.
2. Publish its final PDF and editable PPTX.
3. Use the 4:54 narration in `demo_script.md`.
4. Publish the MP4 with English captions and verify signed-out access.

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
