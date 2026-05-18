# Multi-completions per day + optional chore deadline

**Date:** 2026-05-17
**Status:** Design, awaiting plan

## Problem

Two intertwined gaps in the chore model:

1. A chore can only be completed once per day. Some real-world chores (feed the dog, tidy the playroom, take dishes to the sink) happen multiple times. Kids should be able to mark them done each time and earn reward minutes for each completion, with a visible counter so they can see their progress.
2. `Chore.deadline_time` is required, which forces parents to invent a time even for chores that don't have one. It should be optional.

## Requirements

**Parent-facing**
- On the chore form, set a daily completion limit per chore: **Once a day** (default), **Multiple times** (specify N), or **Unlimited**.
- `deadline_time` becomes optional. Label changes to "Deadline (optional)".

**Kid-facing**
- For multi-completion chores, the Done button stays tappable until the cap is hit; a counter (e.g. `2/3`) is visible.
- At the cap, the button disables and shows e.g. `✓ 3/3 done`.
- Unlimited chores never disable; show e.g. `Done! ×4`.
- Once-a-day chores look and behave exactly as today.

**System**
- Each tap creates one `EARN` `TimeBankTransaction` (so the ledger is the per-tap event log).
- A required multi-chore at `0/N` triggers a single end-of-day penalty. Partial completion (e.g. `1/3`) does **not** trigger a penalty.
- A required chore with no `deadline_time` is treated as due at end-of-day (23:59:59) for penalty purposes.
- Streaks: a chore counts as "done for the day" once `completion_count >= 1` (matches today's existing `completed=True` semantics — no streak logic change).
- Achievements: count unique daily chores completed, not taps (matches today's `completed` flag — no achievement code change).

## Non-goals

- No per-tap entries in the chore log view — one row per `ChoreInstance` with a count is enough.
- No analytics changes; existing "% days completed" stat continues to work.
- No new ChoreCompletion event table. The transaction ledger already serves as the per-tap log.

## Schema changes

### `Chore` (`core/models.py:115`)

```python
max_per_day = models.PositiveIntegerField(null=True, blank=True, default=1)
deadline_time = models.TimeField(null=True, blank=True)  # was required
```

`max_per_day` semantics:
- `1` — once per day (today's behavior, default for all existing chores)
- `N ≥ 2` — capped at N
- `NULL` — unlimited

### `ChoreInstance` (`core/models.py:165`)

```python
completion_count = models.PositiveIntegerField(default=0)
```

- `completed` (BooleanField) stays. It now means "`completion_count >= 1`" and is kept in sync on the first completion of the day.
- `completed_at` stays. Set on the 0→1 transition only; subsequent taps do not update it.
- `unique_together = (chore, assigned_to, due_date)` is preserved — still one row per slot.

### Migration

One Django migration:
1. `AddField` `Chore.max_per_day` with `default=1`.
2. `AlterField` `Chore.deadline_time` to `null=True, blank=True`.
3. `AddField` `ChoreInstance.completion_count` with `default=0`.
4. `RunPython`: set `completion_count = 1` for all rows where `completed = True` so historical data reports correctly.

## Completion view changes

### `CompleteChoreView` (`core/views.py:537`)

Replace the body:

```python
def post(self, request, instance_id):
    instance = get_object_or_404(
        ChoreInstance, pk=instance_id, assigned_to=request.user
    )
    cap = instance.chore.max_per_day  # None = unlimited
    if cap is not None and instance.completion_count >= cap:
        return HttpResponseBadRequest("Already at daily limit")

    with transaction.atomic():
        locked = ChoreInstance.objects.select_for_update().get(pk=instance.pk)
        if cap is not None and locked.completion_count >= cap:
            return HttpResponseBadRequest("Already at daily limit")
        locked.completion_count += 1
        if not locked.completed:
            locked.completed = True
            locked.completed_at = timezone.now()
        locked.save(update_fields=["completion_count", "completed", "completed_at"])

        if locked.chore.reward_minutes > 0:
            TimeBankTransaction.objects.create(
                kid=request.user,
                transaction_type=TimeBankTransaction.TransactionType.EARN,
                amount=locked.chore.reward_minutes,
                note=f"Completed: {locked.chore.name}",
                created_by=request.user,
                chore_instance=locked,
            )

    check_achievements(request.user)
    response = render(request, "core/_chore_item.html", {"instance": locked})
    response["HX-Trigger"] = "chore-completed"
    return response
```

Notes:
- The pre-check + `select_for_update` re-check prevents two concurrent taps from going over the cap.
- The initial `get_object_or_404` no longer filters `completed=False` — multi-completion instances may be tapped while already completed.
- Once-a-day chores (`max_per_day=1`) hit the cap at `completion_count=1`, which gives them today's exact behavior: one tap → button disappears.

## Penalty job changes

### `process_penalties` (`core/tasks.py:77`)

Same query (`completed=False`, `penalty_applied=False`). Only the deadline calculation changes:

```python
deadline_time = instance.chore.deadline_time or time(23, 59, 59)
deadline_naive = datetime.combine(instance.due_date, deadline_time)
```

(Where `time` is `datetime.time`.) No change to the `completed=False` filter — a multi-completion chore with `completion_count >= 1` already has `completed=True`, so partial completion is excluded from penalties, matching the "partial = no penalty" requirement.

## Form changes

### `ChoreForm` (`core/forms.py:13`)

Add a synthetic radio + number group that translates to the model's `max_per_day`:

```python
class ChoreForm(forms.ModelForm):
    LIMIT_ONCE = "once"
    LIMIT_MULTIPLE = "multiple"
    LIMIT_UNLIMITED = "unlimited"
    LIMIT_CHOICES = [
        (LIMIT_ONCE, "Once a day"),
        (LIMIT_MULTIPLE, "Multiple times per day"),
        (LIMIT_UNLIMITED, "Unlimited"),
    ]

    completion_limit = forms.ChoiceField(
        choices=LIMIT_CHOICES, widget=forms.RadioSelect, initial=LIMIT_ONCE
    )
    max_per_day_value = forms.IntegerField(
        min_value=2, required=False, initial=2,
        widget=forms.NumberInput(attrs={"min": 2}),
    )

    class Meta:
        model = Chore
        fields = [
            "name",
            "chore_type",
            "reward_minutes",
            "penalty_minutes",
            "time_of_day",
            "deadline_time",
            "assigned_to",
            "recurrence_type",
            "recurrence_days",
            "recurrence_interval",
            "one_off_date",
        ]
        # max_per_day is intentionally NOT in fields; the synthetic
        # completion_limit / max_per_day_value fields above feed it via save().
```

- In `__init__`: flip `self.fields["deadline_time"].required = False`. When editing, derive initial values for `completion_limit` and `max_per_day_value` from `self.instance.max_per_day` (`None` → unlimited, `1` → once, `≥2` → multiple).
- In `clean()`: validate the synthetic fields. If `completion_limit == multiple`, require `max_per_day_value >= 2` (add error otherwise).
- Override `save(commit=True)`: before persisting, set `self.instance.max_per_day` based on the cleaned synthetic fields:
  - `once` → `1`
  - `multiple` → `cleaned_data["max_per_day_value"]`
  - `unlimited` → `None`

The existing "required chores must have a penalty > 0" rule is unchanged. No new "required chores must have a deadline" rule — required chores without a deadline get penalized at midnight.

## Template changes

### `_chore_item.html` (`templates/core/_chore_item.html`)

- Deadline `<small>` is wrapped in `{% if instance.chore.deadline_time %}` and omitted otherwise.
- Done button / completed state becomes cap-aware:

  | State                                         | Render                                |
  | --------------------------------------------- | ------------------------------------- |
  | `max_per_day == 1`, not completed              | `Done!` button (today's behavior)     |
  | `max_per_day == 1`, completed                  | `✓` checkmark (today's behavior)      |
  | `max_per_day == N`, `count < N`                | `Done! count/N` button                |
  | `max_per_day == N`, `count == N`               | `✓ N/N done` static badge             |
  | `max_per_day` is `NULL` (unlimited), any count | `Done! ×count` button (always active) |

- Strikethrough on the chore name applies only when the cap is hit (for `N`-capped) or `completion_count >= 1` (for once-a-day). Unlimited chores never strike through.
- Earned-minutes badge shows `+<reward_minutes × completion_count> min earned` once `completion_count > 0`.

### `chore_form.html` (`templates/core/chore_form.html`)

- Render the new `completion_limit` radio group in Bootstrap radio style (match existing radio rendering for `chore_type`).
- Render `max_per_day_value` number input wrapped in a container hidden with `d-none` by default; reveal via a small inline `<script>` that watches the radio group (pattern matches existing conditional fields in this template).
- Change the `deadline_time` label to "Deadline (optional)".

No new templates, no new HTMX endpoints — the existing `complete_chore` URL returns the updated `_chore_item.html` partial on each tap.

## Minor ordering note

`ChoreInstance.Meta.ordering` is `["due_date", "chore__time_of_day", "chore__deadline_time"]`. With nullable `deadline_time`, SQLite sorts NULLs first within a time-of-day group. Acceptable — no-deadline chores appearing at the top of their morning/afternoon/evening section is reasonable. If we want them last instead, add an explicit `F("chore__deadline_time").asc(nulls_last=True)` later; not required for v1.

## Out-of-scope ripples we confirmed are safe

- **Streak logic** (`ChoreInstance._streak_data`, `core/models.py:191`): groups by `(due_date, completed)`. `completed=True` now means "≥1 tap that day" — exactly the streak rule we want. No change.
- **Achievements** (`core/achievements.py`): counts based on `completed=True` flag = unique daily chores. Matches the requested semantics. No change.
- **Chore log** (`core/views.py:1348`, `chore_log.html`): one row per `ChoreInstance`. Multi-completion chores naturally appear once per day with `completed=True`. Optional follow-up: show `completion_count` on the row.
- **Analytics** (`core/views.py:1400`): `Count(filter=Q(completed=True))` continues to mean "days the chore was done at all," which is still meaningful. Optional follow-up: add a "total taps" stat.

## Test plan (high level)

- **Model migration:** existing instances get `completion_count = 1` when `completed = True`, `0` otherwise.
- **Once-a-day chores** behave identically to today (regression test on existing `CompleteChoreView` tests).
- **Capped multi-chore:** 3 taps allowed, 4th returns 400; counter renders `1/3`, `2/3`, `3/3` correctly; cap re-checked under `select_for_update`.
- **Unlimited chore:** any number of taps allowed; counter shows `×N`; never disables.
- **Reward minutes:** one EARN transaction per tap; balance increases by `reward_minutes × completion_count`.
- **Penalty job:** required chore with `completion_count = 0` and no `deadline_time` gets penalized after midnight; required chore with `completion_count >= 1` does not get penalized regardless of cap.
- **Form:** editing an existing chore round-trips correctly through the synthetic fields (once → `max_per_day=1`, multiple+N → `N`, unlimited → `NULL`).
- **Streak unchanged:** a kid who taps a multi-chore once still gets streak credit for that day.
