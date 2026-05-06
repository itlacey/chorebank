# Server-Authoritative Timer Design

**Date:** 2026-05-06
**Status:** Draft — pending review

## Problem

Two timer bugs reported by Zeke:

1. **"Stop at 30s remaining returns 1 minute back."** Refund math doesn't match what the kid sees on the display. Root cause is client/server clock skew: the JS countdown computes `endTimeMs - Date.now()` against a server-provided `endTimeMs`, so any drift in the kid's local clock makes the display lie. The server's `math.ceil(used_seconds / 60)` is correct given its own elapsed time, but the kid is judging by the displayed countdown — which is wrong.

2. **"Two tabs has no shared state."** With multiple tabs open, the JS countdown in each tab runs independently. If a kid pauses in Tab B, Tab A keeps ticking visually. Server state diverges from at least one tab's display, leading to confusing or incorrect-feeling refunds. Not necessarily an intentional exploit — more like accidental desync from having two tabs open.

Underlying cause for both: **the client owns the clock.** The frontend has its own concept of "remaining time" derived from `Date.now()` and a server-provided end timestamp. That makes the display drift-prone (bug 1) and per-tab (bug 2).

## Goals

- Eliminate clock drift between display and server state.
- All open tabs converge on the same timer state within ~1 second.
- No model changes; no migration; no new dependencies.
- Pause feature stays as-is in behavior.

## Non-goals

- Adversarial defense against deliberate exploits (e.g., pause-and-play). This is a personal family tool; if a kid weaponizes pause, that's a parenting conversation, not a software-design one.
- Single-tab enforcement (controller-token / heartbeat). Considered and rejected — polling already gives all tabs a shared view; the added complexity isn't worth it.
- Changing the rounding/charging logic. The `math.ceil` math is correct given accurate elapsed time; the symptom of "free minute at 00:30" disappears once the display is honest. Defer ledger-granularity changes to a future change if needed.
- Migrating in-flight timer sessions during deployment. Deploy when no kid has an active timer.

## Architecture

**Server is the sole source of truth. Frontend is a thin renderer that polls.**

The existing `TimerSession` model already stores everything needed (`started_at`, `paused_at`, `paused_seconds`, `requested_minutes`, `ended_at`). No schema changes.

A new endpoint, `GET /kid/timer/state/`, computes timer state fresh from the DB on every request. The frontend polls this endpoint while on the timer page and renders whatever it returns. There is no JS-side countdown math, no `endTimeMs`, no `Date.now()`.

### State endpoint contract

`GET /kid/timer/state/` returns JSON:

```json
{
  "status": "idle" | "running" | "paused" | "ended",
  "session_id": 42,
  "remaining_seconds": 503,
  "requested_minutes": 10,
  "balance": 25,
  "balance_display": "25m"
}
```

Computation:

1. Find the kid's open session (`TimerSession.objects.filter(kid=user, ended_at__isnull=True).first()`).
2. If no session → return `{"status": "idle", "balance": ..., "balance_display": ...}`.
3. If session's `expected_end < now` → close it as `timer_expired`, return `{"status": "ended", ...}`. (Moves the auto-expire logic from `TimerView.get_context_data` into the state endpoint, where it's hit on every poll instead of only on full page load.)
4. Otherwise compute live:
   - `now = timezone.now()`
   - If `paused_at`: `effective_paused = paused_seconds + (now - paused_at).total_seconds()`; `status = "paused"`.
   - Else: `effective_paused = paused_seconds`; `status = "running"`.
   - `elapsed = (now - started_at).total_seconds() - effective_paused`
   - `remaining_seconds = max(0, requested_minutes * 60 - int(elapsed))`
5. Return state.

### Existing views

- `TimerStartView` — unchanged behavior. Could optionally return the same shape as the state endpoint to skip the first poll round-trip, but not required.
- `TimerPauseView` / `TimerResumeView` — unchanged math. **Relax to no-op idempotency:** pause-while-paused and resume-while-running return 200 with current state instead of 400. Two tabs racing the same action shouldn't error.
- `TimerStopView` — unchanged math. The existing `math.ceil(used_seconds / 60)` charge logic stays. Once the display reflects server reality, the "30s remaining → 1 min back" symptom can't occur.
- `TimerView` (the page itself) — becomes a thin shell. Stops passing `active_session`, `active_session_end_time_ms`, `is_paused`, `paused_seconds` into the template. Stops doing auto-expire on render (moved to state endpoint).

### Frontend (`templates/core/timer.html`)

Removed:
- `endTimeMs`, `totalMs`, `isPaused` (state vars).
- `Date.now()`-based countdown math.
- `setInterval(updateDisplay, 1000)` driven by local clock.
- Template-side initial state hydration (`{% if active_session %}` block).

Added:
- `pollState()` — single function that fetches `/kid/timer/state/` and updates the UI.
- A `setInterval` at 1s while the page is open, calling `pollState()`.
- A small dispatch on `status`:
  - `idle` → show setup state, hide overlay.
  - `running` → show overlay, render `mm:ss` from `remaining_seconds`, run color shift, ensure pause button visible / resume hidden.
  - `paused` → show overlay with paused styling, freeze display at last `remaining_seconds`, swap pause/resume buttons.
  - `ended` → trigger expired animation (alarm + flash), then transition to setup with refreshed balance.
- Initial poll runs on `DOMContentLoaded` so the page hydrates from server state, not template context.

The `beforeunload` warning stays (don't surprise kids whose timer is still running).

## Data flow examples

**Two-tab pause sync:**
```
Tab A: timer running, polling /state/ each second.
Tab B: opens timer page, first poll returns {status: "running", remaining_seconds: 240}.
Tab A: kid clicks Pause → POST /pause/ → server sets paused_at.
Tab A: next /state/ poll (within 1s) → {status: "paused", remaining_seconds: 240}, display freezes.
Tab B: next /state/ poll (within 1s) → {status: "paused", remaining_seconds: 240}, display freezes.
Tab B: kid clicks Resume → POST /resume/ → server clears paused_at, accumulates paused_seconds.
Both tabs: next /state/ poll → {status: "running", remaining_seconds: ~239}, display resumes.
```

**Stop sync:**
```
Tab A: kid clicks Stop → POST /stop/ → server ends session, computes refund.
Tab A: next /state/ poll → {status: "idle", balance: <updated>}, transitions to setup.
Tab B: next /state/ poll → {status: "idle", balance: <updated>}, transitions to setup.
```

## Error handling & edge cases

- **Poll network failure:** silent retry on next interval. After 5 consecutive failures (~5s offline), show a small "reconnecting…" badge but keep the last known display. Don't toast errors during normal play.
- **Pause/resume/stop POST failure:** ignore the local action's UI effect; let the next /state/ poll recover truth. If polls are also failing, the reconnecting badge is the user-facing signal.
- **Tab backgrounded:** browsers throttle `setInterval` to ~1/min for hidden tabs. That's fine — the next foreground tick re-syncs. Optionally use the Page Visibility API to skip polls entirely while hidden, reducing request volume.
- **Server-side expiry while client is offline:** next /state/ poll returns `status: "ended"` with the final balance; client runs the expired animation and transitions to setup.
- **Page loaded mid-session:** initial /state/ poll on `DOMContentLoaded` hydrates whichever state applies. No template-context initial state.
- **Two pause clicks racing:** pause-while-paused returns 200 no-op; same for resume-while-running. No 400s from concurrent tabs.
- **Clock skew:** irrelevant — the server clock is the only clock. The display reflects whatever the server computed, which is internally consistent with the charge math at stop time.

## Testing

Unit tests in `core/tests/test_timer.py`:

- `TimerStateView` returns `status: "idle"` when no session exists.
- Returns `status: "running"` with correct `remaining_seconds` for an active session (use `freeze_time` or mock `timezone.now()`).
- Returns `status: "paused"` with the correct frozen `remaining_seconds` when `paused_at` is set, and that `remaining_seconds` doesn't decrement across polls during pause.
- Auto-expires a session whose `expected_end` is in the past, returns `status: "ended"`.
- Pause-while-paused and resume-while-running return 200 with current state (idempotency).
- Regression: Tab-A-start → Tab-B-pause → Tab-A-stop scenario: assert refund equals `requested_minutes - ceil(actual_elapsed_minus_paused / 60)`.

Manual UAT:

- Open two tabs side by side. Pause in one — the other freezes within ~1s. Resume in the other — the first resumes. Stop in either — both return to setup with updated balance.
- Start a 5-min timer, stop with the display showing 00:30 — confirm refund is 0 (no more "free minute").
- Reload the page mid-session — confirm the running/paused state hydrates from the first poll without flicker.
- Network blip simulation (DevTools offline ~3s) — confirm display freezes, then catches up smoothly when reconnected.

## Out of scope (future)

- Migrating the bank ledger to second granularity for fairer rounding.
- Push-based sync (SSE/WebSocket) instead of polling — only worth doing if 1s polling becomes a problem.
- Single-tab "controller" enforcement.
- Pause-budget caps (e.g., auto-resume after N seconds).
