# Server-Authoritative Timer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move timer state to server-authoritative, polled by the frontend each second. Eliminates client/server clock drift (Bug #1: "stop at 30s remaining returns 1 minute back") and multi-tab desync (Bug #2: pause in one tab while the other keeps ticking).

**Architecture:** A new `TimerStateView` endpoint computes timer state (`idle` / `running` / `paused` / `ended`) plus `remaining_seconds` and balance fresh from `TimerSession` on every call. The frontend `templates/core/timer.html` strips out its independent JS countdown (`Date.now()` math, local `endTimeMs`) and instead polls `/kid/timer/state/` every 1 second, branching on the returned `status`. `TimerPauseView` and `TimerResumeView` become idempotent so two tabs racing the same action don't 400 each other. Auto-expire logic moves out of `TimerPageView.get_context_data` into the state endpoint so it runs on every poll instead of only on full page loads. No model changes, no migration.

**Tech Stack:** Django 5.2, vanilla JS (no new dependencies). Tests use Django's `TestCase` and `unittest.mock.patch` for time freezing.

---

### Task 1: Make Pause and Resume Idempotent

Two tabs racing pause/resume must not 400. The current views return `{"error": ...}, status=400` if you pause an already-paused session or resume an already-running session. We change them to a 200 OK no-op.

**Files:**
- Modify: `core/views.py:764-806` (TimerPauseView, TimerResumeView)
- Modify: `core/tests.py` — add idempotency tests

- [ ] **Step 1: Write failing tests**

Append to `core/tests.py`:

```python
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import TimeBankTransaction, TimerSession, User


def _make_kid(balance_minutes=60):
    """Create a kid with a starting bank balance."""
    kid = User.objects.create_user(
        username="zeke", password="x", first_name="Zeke", role=User.Role.KID
    )
    if balance_minutes:
        TimeBankTransaction.objects.create(
            kid=kid,
            transaction_type="earn",
            amount=balance_minutes,
            note="seed",
            created_by=kid,
        )
    return kid


class TimerPauseResumeIdempotencyTests(TestCase):
    def setUp(self):
        self.kid = _make_kid()
        self.client.force_login(self.kid)
        self.session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=10,
            started_at=timezone.now() - timedelta(seconds=30),
        )

    def test_pause_while_paused_is_noop_200(self):
        # First pause sets paused_at
        resp = self.client.post(reverse("timer_pause"))
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        first_paused_at = self.session.paused_at
        self.assertIsNotNone(first_paused_at)

        # Second pause is a no-op, must not 400 and must not change paused_at
        resp = self.client.post(reverse("timer_pause"))
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.paused_at, first_paused_at)

    def test_resume_while_running_is_noop_200(self):
        # Session is not paused; resume should no-op, not 400
        resp = self.client.post(reverse("timer_resume"))
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.paused_at)
        self.assertEqual(self.session.paused_seconds, 0)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python manage.py test core.tests.TimerPauseResumeIdempotencyTests -v 2`
Expected: FAIL — both tests get 400 from current views.

- [ ] **Step 3: Make pause idempotent**

Replace `TimerPauseView` in `core/views.py` (currently lines 764-776) with:

```python
class TimerPauseView(KidRequiredMixin, View):
    """Pause an active timer session. Idempotent: pause-while-paused is a no-op."""

    def post(self, request):
        session = TimerSession.objects.filter(
            kid=request.user, ended_at__isnull=True
        ).first()
        if not session:
            return JsonResponse({"error": "No active session"}, status=400)

        if session.paused_at is None:
            session.paused_at = timezone.now()
            session.save()
        return JsonResponse({"ok": True, "paused": True})
```

- [ ] **Step 4: Make resume idempotent**

Replace `TimerResumeView` in `core/views.py` (currently lines 779-806) with:

```python
class TimerResumeView(KidRequiredMixin, View):
    """Resume a paused timer session. Idempotent: resume-while-running is a no-op."""

    def post(self, request):
        session = TimerSession.objects.filter(
            kid=request.user, ended_at__isnull=True
        ).first()
        if not session:
            return JsonResponse({"error": "No active session"}, status=400)

        if session.paused_at is not None:
            now = timezone.now()
            session.paused_seconds += int(
                (now - session.paused_at).total_seconds()
            )
            session.paused_at = None
            session.save()
        return JsonResponse({"ok": True, "resumed": True})
```

Note: the old resume returned `end_time_ms`; we drop that field. The frontend will get authoritative remaining time from the state endpoint instead, and no other caller uses it.

- [ ] **Step 5: Run tests, verify they pass**

Run: `python manage.py test core.tests.TimerPauseResumeIdempotencyTests -v 2`
Expected: PASS, both tests.

- [ ] **Step 6: Commit**

```bash
git add core/views.py core/tests.py
git commit -m "fix(timer): make pause/resume idempotent

Two tabs racing the same action now no-op (200) instead of erroring (400).
Required for the upcoming server-authoritative state endpoint."
```

---

### Task 2: Add TimerStateView (Server-Authoritative State Endpoint)

The single source of truth for timer state. Computes status, remaining seconds, and balance fresh from the DB on every call. Auto-expires stale sessions (logic moved out of `TimerPageView`).

**Files:**
- Modify: `core/views.py` — add TimerStateView class near the other timer views (after TimerResumeView)
- Modify: `core/urls.py` — add URL for `/kid/timer/state/` named `timer_state`
- Modify: `core/tests.py` — add state endpoint tests

- [ ] **Step 1: Write failing tests for the idle case**

Append to `core/tests.py`:

```python
class TimerStateViewTests(TestCase):
    def setUp(self):
        self.kid = _make_kid(balance_minutes=30)
        self.client.force_login(self.kid)
        self.url = reverse("timer_state")

    def test_idle_when_no_session(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "idle")
        self.assertEqual(data["balance"], 30)
        self.assertEqual(data["balance_display"], "30m")
        self.assertNotIn("session_id", data)
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python manage.py test core.tests.TimerStateViewTests.test_idle_when_no_session -v 2`
Expected: FAIL — `NoReverseMatch: 'timer_state' is not a valid view function or pattern name.`

- [ ] **Step 3: Add the URL route**

In `core/urls.py`, add this line near the other timer routes (after `timer_resume`):

```python
    path("kid/timer/state/", TimerStateView.as_view(), name="timer_state"),
```

And add `TimerStateView` to the import block at the top of `core/urls.py` where the other timer views are imported.

- [ ] **Step 4: Implement minimal idle-case TimerStateView**

In `core/views.py`, add this class after `TimerResumeView`:

```python
class TimerStateView(KidRequiredMixin, View):
    """Server-authoritative timer state. Polled by the frontend each second.

    Returns one of: idle, running, paused, ended. Computes remaining seconds
    from started_at / paused_at / paused_seconds / requested_minutes on every
    request so all open tabs converge on the same view of reality.
    """

    def get(self, request):
        balance = TimeBankTransaction.get_balance(request.user)
        return JsonResponse({
            "status": "idle",
            "balance": balance,
            "balance_display": format_balance(balance),
        })
```

- [ ] **Step 5: Run test, verify it passes**

Run: `python manage.py test core.tests.TimerStateViewTests.test_idle_when_no_session -v 2`
Expected: PASS.

- [ ] **Step 6: Add test for the running case**

Append to `TimerStateViewTests` in `core/tests.py`:

```python
    def test_running_returns_remaining_seconds(self):
        started = timezone.now() - timedelta(seconds=120)
        session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=10,
            started_at=started,
        )

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["session_id"], session.pk)
        self.assertEqual(data["requested_minutes"], 10)
        # 600s requested - 120s elapsed = 480s remaining (allow 1s slop for clock)
        self.assertGreaterEqual(data["remaining_seconds"], 479)
        self.assertLessEqual(data["remaining_seconds"], 480)
```

- [ ] **Step 7: Run, verify failure**

Run: `python manage.py test core.tests.TimerStateViewTests.test_running_returns_remaining_seconds -v 2`
Expected: FAIL — view returns idle status when a session exists.

- [ ] **Step 8: Implement running case in TimerStateView**

Replace `TimerStateView.get` in `core/views.py` with:

```python
    def get(self, request):
        balance = TimeBankTransaction.get_balance(request.user)
        session = (
            TimerSession.objects.filter(kid=request.user, ended_at__isnull=True)
            .first()
        )

        if session is None:
            return JsonResponse({
                "status": "idle",
                "balance": balance,
                "balance_display": format_balance(balance),
            })

        now = timezone.now()
        effective_paused = session.paused_seconds
        if session.paused_at is not None:
            effective_paused += int((now - session.paused_at).total_seconds())
            status = "paused"
        else:
            status = "running"

        elapsed = (now - session.started_at).total_seconds() - effective_paused
        remaining_seconds = max(0, session.requested_minutes * 60 - int(elapsed))

        return JsonResponse({
            "status": status,
            "session_id": session.pk,
            "requested_minutes": session.requested_minutes,
            "remaining_seconds": remaining_seconds,
            "balance": balance,
            "balance_display": format_balance(balance),
        })
```

- [ ] **Step 9: Run running-case test, verify pass**

Run: `python manage.py test core.tests.TimerStateViewTests.test_running_returns_remaining_seconds -v 2`
Expected: PASS.

- [ ] **Step 10: Add test for paused case (frozen remaining across polls)**

Append to `TimerStateViewTests`:

```python
    def test_paused_freezes_remaining_across_polls(self):
        started = timezone.now() - timedelta(seconds=60)
        paused = timezone.now() - timedelta(seconds=30)
        session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=10,
            started_at=started,
            paused_at=paused,
        )

        # First poll
        resp1 = self.client.get(self.url)
        data1 = resp1.json()
        self.assertEqual(data1["status"], "paused")
        first_remaining = data1["remaining_seconds"]
        # 600 requested - 60s started ago + 30s paused = 570 remaining
        self.assertGreaterEqual(first_remaining, 569)
        self.assertLessEqual(first_remaining, 570)

        # Wait the equivalent of 5 seconds via mock — paused remaining should not drift
        with patch("core.views.timezone.now") as mock_now:
            mock_now.return_value = timezone.now() + timedelta(seconds=5)
            resp2 = self.client.get(self.url)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "paused")
        # While paused, the elapsed-paused time increases in lockstep with elapsed,
        # so remaining_seconds should not drop.
        self.assertEqual(data2["remaining_seconds"], first_remaining)
```

- [ ] **Step 11: Run paused-case test, verify pass**

Run: `python manage.py test core.tests.TimerStateViewTests.test_paused_freezes_remaining_across_polls -v 2`
Expected: PASS — the paused-case logic is already in the implementation from Step 8.

- [ ] **Step 12: Add test for auto-expire (ended status + closes session)**

Append to `TimerStateViewTests`:

```python
    def test_expired_session_is_auto_closed_and_returns_ended(self):
        # A 5-min session started 10 minutes ago: expired
        started = timezone.now() - timedelta(minutes=10)
        session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=5,
            started_at=started,
        )

        resp = self.client.get(self.url)
        data = resp.json()
        self.assertEqual(data["status"], "ended")

        session.refresh_from_db()
        self.assertIsNotNone(session.ended_at)
        self.assertEqual(session.ended_reason, "timer_expired")
```

- [ ] **Step 13: Run, verify it fails**

Run: `python manage.py test core.tests.TimerStateViewTests.test_expired_session_is_auto_closed_and_returns_ended -v 2`
Expected: FAIL — session is still open and view returns "running" with `remaining_seconds: 0` (or paused).

- [ ] **Step 14: Implement auto-expire in TimerStateView**

Replace `TimerStateView.get` in `core/views.py` with:

```python
    def get(self, request):
        balance = TimeBankTransaction.get_balance(request.user)
        session = (
            TimerSession.objects.filter(kid=request.user, ended_at__isnull=True)
            .first()
        )

        if session is None:
            return JsonResponse({
                "status": "idle",
                "balance": balance,
                "balance_display": format_balance(balance),
            })

        now = timezone.now()

        # Auto-expire: close out sessions whose expected_end is in the past.
        expected_end = session.started_at + timedelta(
            minutes=session.requested_minutes,
            seconds=session.paused_seconds,
        )
        if session.paused_at is not None:
            expected_end += now - session.paused_at
        if expected_end <= now:
            session.ended_at = expected_end
            session.ended_reason = "timer_expired"
            session.save()
            return JsonResponse({
                "status": "ended",
                "session_id": session.pk,
                "balance": balance,
                "balance_display": format_balance(balance),
            })

        effective_paused = session.paused_seconds
        if session.paused_at is not None:
            effective_paused += int((now - session.paused_at).total_seconds())
            status = "paused"
        else:
            status = "running"

        elapsed = (now - session.started_at).total_seconds() - effective_paused
        remaining_seconds = max(0, session.requested_minutes * 60 - int(elapsed))

        return JsonResponse({
            "status": status,
            "session_id": session.pk,
            "requested_minutes": session.requested_minutes,
            "remaining_seconds": remaining_seconds,
            "balance": balance,
            "balance_display": format_balance(balance),
        })
```

- [ ] **Step 15: Run all state tests, verify they pass**

Run: `python manage.py test core.tests.TimerStateViewTests -v 2`
Expected: 4 tests PASS.

- [ ] **Step 16: Commit**

```bash
git add core/views.py core/urls.py core/tests.py
git commit -m "feat(timer): add server-authoritative state endpoint

GET /kid/timer/state/ returns {status, remaining_seconds, balance}
computed fresh from TimerSession on every call. Handles idle, running,
paused (with frozen remaining), and auto-expired sessions. Will be
polled by the frontend on a 1s tick to replace the JS countdown."
```

---

### Task 3: Simplify TimerPageView

Now that the state endpoint is the single source of truth, `TimerPageView.get_context_data` no longer needs to compute `active_session`, `active_session_end_time_ms`, `is_paused`, `paused_seconds`, or auto-expire. Initial page render only needs balance for the setup-state UI; everything else is hydrated by the first poll.

**Files:**
- Modify: `core/views.py:598-651` (TimerPageView)

- [ ] **Step 1: Replace TimerPageView with the simplified version**

Replace `TimerPageView` in `core/views.py` (currently lines 598-651) with:

```python
class TimerPageView(KidRequiredMixin, TemplateView):
    """Renders the timer page shell. Live state is hydrated by polling /kid/timer/state/."""

    template_name = "core/timer.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        balance = TimeBankTransaction.get_balance(self.request.user)
        ctx["balance"] = balance
        ctx["balance_display"] = format_balance(balance)
        return ctx
```

- [ ] **Step 2: Run all timer tests to ensure no regression**

Run: `python manage.py test core.tests -v 2`
Expected: all tests PASS. (The simplification removes inline logic that's now covered by TimerStateView's auto-expire.)

- [ ] **Step 3: Commit**

```bash
git add core/views.py
git commit -m "refactor(timer): thin TimerPageView; live state comes from poll endpoint

TimerPageView no longer hydrates active_session into the template
context or runs auto-expire on render. The page is now a shell;
the frontend polls /kid/timer/state/ for live state."
```

---

### Task 4: Rewrite Frontend to Poll for State

The big one. Strip out the JS-side countdown (`Date.now()`, `endTimeMs`, `setInterval(updateDisplay)`) and replace with a single `pollState()` loop that fetches `/kid/timer/state/` and dispatches on `status`.

**Files:**
- Modify: `templates/core/timer.html` (entire `<script>` block + the `{% if active_session %}` initialization in `DOMContentLoaded`)

- [ ] **Step 1: Replace the `<script>` block**

In `templates/core/timer.html`, replace the entire `<script>...</script>` block (currently starts at line 118 and ends at line 367) with:

```html
<script>
// State held only for visual polish (color shift, alarm de-duplication).
// The truth lives on the server; we only render what /state/ tells us.
let pollInterval = null;
let audioCtx = null;
let totalSeconds = null;       // requested_minutes * 60, captured for color shift
let lastStatus = "idle";
let alarmFired = false;        // ensure alarm only plays once per ended session
let lastSessionId = null;      // detect new sessions to reset alarmFired
let consecutiveFailures = 0;

const POLL_MS = 1000;

// CSRF helper
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
}

// Audio init (must be on user gesture)
function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

// Alarm: three beeps at 880Hz
function playAlarm() {
    if (!audioCtx) return;
    [0, 0.4, 0.8].forEach(function(delay) {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.value = 880;
        osc.type = "sine";
        gain.gain.value = 0.3;
        osc.start(audioCtx.currentTime + delay);
        osc.stop(audioCtx.currentTime + delay + 0.25);
    });
}

// Visual flash on expiry
function flashScreen() {
    const overlay = document.querySelector(".timer-overlay");
    let count = 0;
    const flash = setInterval(function() {
        overlay.style.backgroundColor = count % 2 === 0 ? "#F0B4B0" : "#FAF8FC";
        count++;
        if (count >= 6) {
            clearInterval(flash);
            overlay.style.backgroundColor = "#F0B4B0";
        }
    }, 300);
}

// Color shift based on remaining percentage
function updateColorShift(remainingSeconds) {
    const overlay = document.querySelector(".timer-overlay");
    if (!totalSeconds) return;
    const pct = remainingSeconds / totalSeconds;
    if (pct > 0.25) {
        overlay.style.backgroundColor = "#C8E6D0";  // Calm green
    } else if (pct > 0.10) {
        overlay.style.backgroundColor = "#F5D6A8";  // Warning orange
    } else {
        overlay.style.backgroundColor = "#F0B4B0";  // Urgent red
    }
}

// Render mm:ss
function renderTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    document.getElementById("timer-display").textContent =
        String(mins).padStart(2, "0") + ":" + String(secs).padStart(2, "0");
}

// State dispatch
function applyState(data) {
    consecutiveFailures = 0;
    document.getElementById("reconnecting-badge").style.display = "none";

    if (data.session_id && data.session_id !== lastSessionId) {
        lastSessionId = data.session_id;
        alarmFired = false;
        if (data.requested_minutes) {
            totalSeconds = data.requested_minutes * 60;
        }
    }

    const setup = document.getElementById("setup-state");
    const overlay = document.querySelector(".timer-overlay");
    const pauseBtn = document.getElementById("pause-btn");
    const resumeBtn = document.getElementById("resume-btn");

    if (data.status === "running") {
        setup.style.display = "none";
        overlay.style.display = "flex";
        pauseBtn.style.display = "";
        resumeBtn.style.display = "none";
        renderTime(data.remaining_seconds);
        updateColorShift(data.remaining_seconds);
    } else if (data.status === "paused") {
        setup.style.display = "none";
        overlay.style.display = "flex";
        pauseBtn.style.display = "none";
        resumeBtn.style.display = "";
        overlay.style.backgroundColor = "#D0D8E0";
        renderTime(data.remaining_seconds);
    } else if (data.status === "ended") {
        // Animate expiry once, then reload to setup with refreshed balance.
        if (!alarmFired) {
            alarmFired = true;
            playAlarm();
            flashScreen();
            setTimeout(function() { window.location.reload(); }, 2200);
        }
    } else {
        // idle
        if (lastStatus === "running" || lastStatus === "paused") {
            // We just stopped/ended via a sibling tab — reload to refresh balance display.
            window.location.reload();
            return;
        }
        setup.style.display = "";
        overlay.style.display = "none";
    }

    lastStatus = data.status;
}

// Single polling tick
async function pollState() {
    try {
        const resp = await fetch("/kid/timer/state/", {headers: {"Accept": "application/json"}});
        if (!resp.ok) throw new Error("non-200");
        const data = await resp.json();
        applyState(data);
    } catch (err) {
        consecutiveFailures += 1;
        if (consecutiveFailures >= 5) {
            document.getElementById("reconnecting-badge").style.display = "";
        }
    }
}

// Start polling and ensure first paint comes from the server, not the template
function startPolling() {
    if (pollInterval) return;
    pollState();
    pollInterval = setInterval(pollState, POLL_MS);
}

// Set minutes from preset button
function setMinutes(val) {
    document.getElementById("minutes-input").value = val;
    document.getElementById("start-btn").disabled = false;
}

// Start timer
async function startTimer() {
    const minutesInput = document.getElementById("minutes-input");
    const minutes = parseInt(minutesInput.value);
    if (!minutes || minutes < 1) return;

    initAudio();

    const startBtn = document.getElementById("start-btn");
    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Starting...';

    try {
        const resp = await fetch("/kid/timer/start/", {
            method: "POST",
            headers: {"X-CSRFToken": getCookie("csrftoken"), "Content-Type": "application/json"},
            body: JSON.stringify({minutes: minutes}),
        });
        const data = await resp.json();
        if (!resp.ok) {
            alert(data.error || "Could not start timer");
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Start Timer';
            return;
        }
        // Let the next poll render the running state.
        pollState();
    } catch (err) {
        alert("Network error -- try again");
        startBtn.disabled = false;
        startBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Start Timer';
    }
}

async function pauseTimer() {
    try {
        await fetch("/kid/timer/pause/", {
            method: "POST",
            headers: {"X-CSRFToken": getCookie("csrftoken"), "Content-Type": "application/json"},
        });
    } catch (err) {}
    pollState();  // Pick up new state immediately.
}

async function resumeTimer() {
    try {
        await fetch("/kid/timer/resume/", {
            method: "POST",
            headers: {"X-CSRFToken": getCookie("csrftoken"), "Content-Type": "application/json"},
        });
    } catch (err) {}
    pollState();
}

async function stopTimer() {
    const stopBtn = document.getElementById("stop-btn");
    stopBtn.disabled = true;
    stopBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Stopping...';
    try {
        const resp = await fetch("/kid/timer/stop/", {
            method: "POST",
            headers: {"X-CSRFToken": getCookie("csrftoken"), "Content-Type": "application/json"},
        });
        if (resp.ok) {
            window.location.reload();
            return;
        }
    } catch (err) {}
    stopBtn.disabled = false;
    stopBtn.innerHTML = '<i class="bi bi-stop-fill me-2"></i>Retry Stop';
}

// Boot
document.addEventListener("DOMContentLoaded", function() {
    const minutesInput = document.getElementById("minutes-input");
    if (minutesInput) {
        minutesInput.addEventListener("input", function() {
            const val = parseInt(this.value);
            const startBtn = document.getElementById("start-btn");
            if (startBtn) startBtn.disabled = !val || val < 1;
        });
    }
    // Audio context cannot be created without a user gesture — defer until startTimer/active session.
    startPolling();
});

// Warn before closing tab during active timer
window.addEventListener("beforeunload", function(e) {
    if (lastStatus === "running" || lastStatus === "paused") {
        e.preventDefault();
        e.returnValue = "";
    }
});
</script>
```

- [ ] **Step 2: Add the reconnecting badge element**

In `templates/core/timer.html`, inside the `.timer-overlay` div (currently around line 80-98), just before its closing `</div>`, add:

```html
    <div id="reconnecting-badge" class="position-fixed bottom-0 end-0 m-3 badge bg-secondary" style="display: none;">
      Reconnecting…
    </div>
```

(Position-fixed so it shows even when the overlay is hidden.)

- [ ] **Step 3: Verify the template compiles and the page renders**

Run: `python manage.py runserver` (in another shell), then in a browser go to `/kid/timer/` (logged in as a kid).
Expected: page renders setup state cleanly. No JS errors in console. Network tab shows `GET /kid/timer/state/` firing every 1s and returning idle.

- [ ] **Step 4: Smoke test the running state in the browser**

Start a 1-minute timer. Confirm:
- The countdown updates each second (driven by polling, not local clock).
- Color shift transitions to orange around 15s remaining and red around 6s.
- At 0s, alarm beeps, screen flashes red, page reloads.

- [ ] **Step 5: Commit**

```bash
git add templates/core/timer.html
git commit -m "feat(timer): poll server state instead of running local countdown

The frontend no longer maintains an independent clock. Every 1s it
polls /kid/timer/state/ and renders the returned remaining_seconds.
Eliminates client/server clock drift (Bug #1) and makes all open
tabs converge on the same state within ~1s (Bug #2)."
```

---

### Task 5: Multi-Tab UAT and Regression Check

Verify the fix end-to-end against the original two bugs.

**Files:** none (manual validation).

- [ ] **Step 1: Verify Bug #1 (clock-drift refund) is fixed**

In one tab, start a 5-minute timer. Watch the countdown. When the display reads "00:30", click Stop.
Expected: bank balance is unchanged from when you started (i.e., refund is 0). The "free 30 seconds" or "1 minute back" no longer happens because the display now reflects exactly what the server sees.

- [ ] **Step 2: Verify Bug #2 (multi-tab desync) is fixed**

Open two browser tabs side by side, both at `/kid/timer/`.
- Start a 10-minute timer in Tab A.
- Tab B should pick up the running timer within ~1 second and show the same `mm:ss`.
- Click Pause in Tab B. Within ~1 second, Tab A should freeze its display and swap Pause → Resume.
- Click Resume in Tab A. Within ~1 second, Tab B should resume the countdown.
- Click Stop in either tab. Both should return to setup state with the correct refund applied.

- [ ] **Step 3: Verify graceful network handling**

In DevTools, go offline for ~6 seconds while a timer is running.
Expected: countdown freezes (no new state arrives); the "Reconnecting…" badge appears. Restore network. Within 1s the badge disappears and the countdown resumes from the correct server-side remaining time.

- [ ] **Step 4: Verify reload-mid-session works**

Start a timer, wait a few seconds, then refresh the page.
Expected: page reloads into the running overlay state from the first poll, without flicker into the setup state.

- [ ] **Step 5: Final commit (UAT log)**

If any defect surfaced and was fixed, commit those fixes with appropriate messages. Otherwise, no further commit needed.

---

## Self-Review Notes

- **Spec coverage**: All four spec sections (Architecture, Components, Data Flow, Error Handling) map to tasks 1–4. Testing section maps to embedded tests in tasks 1–2 plus manual UAT in task 5.
- **No model changes**: confirmed; nothing in `core/models.py` is modified.
- **Backwards compatibility**: existing `TimerSession` rows continue to work. The dropped `end_time_ms` field from resume's response was only consumed by the timer template, which is rewritten in task 4.
- **Idempotent operations**: pause-while-paused and resume-while-running both return 200; verified by tests in task 1.
- **Display–server consistency**: the countdown is computed on the server once per poll; the client only formats and renders it.
