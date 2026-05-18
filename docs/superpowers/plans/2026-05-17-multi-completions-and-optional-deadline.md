# Multi-completions + Optional Deadline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow a chore to be completed multiple times per day (with a visible counter and a parent-set cap or unlimited), and make `Chore.deadline_time` optional.

**Architecture:** Add `Chore.max_per_day` (nullable int, default 1) and `ChoreInstance.completion_count` (int, default 0). Each tap increments the count and creates one `EARN` transaction; `completed` becomes "count ≥ 1" (kept in sync on first tap for cheap reads). `deadline_time` becomes nullable; the penalty job treats a missing deadline as 23:59:59.

**Tech Stack:** Django, HTMX, Bootstrap, SQLite, Django TestCase.

**Spec:** `docs/superpowers/specs/2026-05-17-multi-completions-and-optional-deadline-design.md`

---

## Files Touched

- **Create:** `core/migrations/0015_multi_completions_and_optional_deadline.py`
- **Modify:** `core/models.py` — add `Chore.max_per_day`, `ChoreInstance.completion_count`, make `Chore.deadline_time` nullable
- **Modify:** `core/tasks.py` — penalty job treats missing deadline as 23:59:59
- **Modify:** `core/views.py` — `CompleteChoreView` increments counter, enforces cap, creates EARN per tap
- **Modify:** `core/forms.py` — `ChoreForm` gains synthetic `completion_limit` + `max_per_day_value`; `deadline_time` becomes optional
- **Modify:** `templates/core/chore_form.html` — render new radio + number; "Deadline (optional)" label; toggle JS
- **Modify:** `templates/core/_chore_item.html` — counter, cap-aware button, optional deadline display
- **Modify:** `core/tests.py` — new test classes for each behavior

No new files outside the migration. No new URLs. No new HTMX endpoints.

---

### Task 1: Schema changes — model fields + migration

**Files:**
- Modify: `core/models.py` (Chore @ line 115, ChoreInstance @ line 165)
- Create: `core/migrations/0015_multi_completions_and_optional_deadline.py`
- Modify: `core/tests.py` (add `MultiCompletionSchemaTests` class)

- [ ] **Step 1: Write the failing schema test**

First, add the new imports near the top of `core/tests.py`. Update the existing `from datetime import timedelta` line to `from datetime import date, time, timedelta`, and update `from core.models import TimeBankTransaction, TimerSession, User` to `from core.models import Chore, ChoreInstance, TimeBankTransaction, TimerSession, User`.

Then append to the end of `core/tests.py`:

```python
def _make_parent():
    return User.objects.create_user(
        username="mom", password="x", first_name="Mom", role=User.Role.PARENT
    )


def _make_chore(parent, **overrides):
    defaults = dict(
        name="Test Chore",
        chore_type=Chore.ChoreType.REQUIRED,
        reward_minutes=5,
        penalty_minutes=10,
        time_of_day=Chore.TimeOfDay.MORNING,
        deadline_time=time(9, 0),
        recurrence_type=Chore.RecurrenceType.DAILY,
        created_by=parent,
    )
    defaults.update(overrides)
    return Chore.objects.create(**defaults)


class MultiCompletionSchemaTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def test_chore_max_per_day_defaults_to_1(self):
        chore = _make_chore(self.parent)
        self.assertEqual(chore.max_per_day, 1)

    def test_chore_max_per_day_can_be_null(self):
        chore = _make_chore(self.parent, max_per_day=None)
        self.assertIsNone(chore.max_per_day)

    def test_chore_deadline_time_can_be_null(self):
        chore = _make_chore(self.parent, deadline_time=None)
        self.assertIsNone(chore.deadline_time)

    def test_chore_instance_completion_count_defaults_to_0(self):
        chore = _make_chore(self.parent)
        chore.assigned_to.add(self.kid)
        inst = ChoreInstance.objects.create(
            chore=chore, assigned_to=self.kid, due_date=date(2026, 1, 1)
        )
        self.assertEqual(inst.completion_count, 0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.MultiCompletionSchemaTests -v 2`
Expected: FAIL — either `'max_per_day' is an invalid keyword argument`, `IntegrityError` on null `deadline_time`, or missing `completion_count` attribute.

- [ ] **Step 3: Modify the `Chore` model**

In `core/models.py`, edit the `Chore` class. Replace this line (around line 140):

```python
    deadline_time = models.TimeField()
```

with:

```python
    deadline_time = models.TimeField(null=True, blank=True)
```

And immediately after the `recurrence_type` block (after the `one_off_date = models.DateField(...)` line, before `is_active`), add:

```python
    max_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
        help_text="1 = once a day, N = capped at N, NULL = unlimited.",
    )
```

- [ ] **Step 4: Modify the `ChoreInstance` model**

In `core/models.py`, in the `ChoreInstance` class, immediately after `penalty_applied = models.BooleanField(default=False)`, add:

```python
    completion_count = models.PositiveIntegerField(default=0)
```

- [ ] **Step 5: Create the migration**

Create `core/migrations/0015_multi_completions_and_optional_deadline.py` with:

```python
from django.db import migrations, models


def backfill_completion_count(apps, schema_editor):
    """Existing ChoreInstance rows with completed=True get completion_count=1."""
    ChoreInstance = apps.get_model("core", "ChoreInstance")
    ChoreInstance.objects.filter(completed=True).update(completion_count=1)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_expand_unlockables"),
    ]

    operations = [
        migrations.AddField(
            model_name="chore",
            name="max_per_day",
            field=models.PositiveIntegerField(
                blank=True,
                default=1,
                null=True,
                help_text="1 = once a day, N = capped at N, NULL = unlimited.",
            ),
        ),
        migrations.AlterField(
            model_name="chore",
            name="deadline_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="choreinstance",
            name="completion_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(
            backfill_completion_count, migrations.RunPython.noop
        ),
    ]
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python manage.py test core.tests.MultiCompletionSchemaTests -v 2`
Expected: 4 tests pass.

- [ ] **Step 7: Apply the migration to the dev DB**

Run: `python manage.py migrate core`
Expected: `Applying core.0015_multi_completions_and_optional_deadline... OK`

- [ ] **Step 8: Commit**

```bash
git add core/models.py core/migrations/0015_multi_completions_and_optional_deadline.py core/tests.py
git commit -m "feat(chores): add max_per_day, completion_count, nullable deadline"
```

---

### Task 2: Penalty job handles null `deadline_time`

**Files:**
- Modify: `core/tasks.py` (`process_penalties` @ line 77)
- Modify: `core/tests.py` (add `PenaltyJobNullDeadlineTests` class)

- [ ] **Step 1: Write the failing test**

Add `from core.tasks import process_penalties` to the imports near the top of `core/tests.py`. Then append to the end of `core/tests.py`:

```python
class PenaltyJobNullDeadlineTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def test_required_chore_with_no_deadline_penalized_after_midnight(self):
        chore = _make_chore(
            self.parent,
            chore_type=Chore.ChoreType.REQUIRED,
            penalty_minutes=10,
            deadline_time=None,
        )
        chore.assigned_to.add(self.kid)
        yesterday = timezone.localdate() - timedelta(days=1)
        ChoreInstance.objects.create(
            chore=chore, assigned_to=self.kid, due_date=yesterday
        )

        applied = process_penalties()

        self.assertEqual(applied, 1)
        balance = TimeBankTransaction.get_balance(self.kid)
        self.assertEqual(balance, -10)

    def test_partial_multi_completion_not_penalized(self):
        chore = _make_chore(
            self.parent,
            chore_type=Chore.ChoreType.REQUIRED,
            penalty_minutes=10,
            max_per_day=3,
            deadline_time=None,
        )
        chore.assigned_to.add(self.kid)
        yesterday = timezone.localdate() - timedelta(days=1)
        # 1/3 done — completed is True, so penalty job's completed=False filter excludes it
        ChoreInstance.objects.create(
            chore=chore,
            assigned_to=self.kid,
            due_date=yesterday,
            completion_count=1,
            completed=True,
            completed_at=timezone.now() - timedelta(days=1),
        )

        applied = process_penalties()

        self.assertEqual(applied, 0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.PenaltyJobNullDeadlineTests -v 2`
Expected: FAIL — `test_required_chore_with_no_deadline_penalized_after_midnight` throws `TypeError: combine() argument 2 must be datetime.time, not None`. The second test should already pass (uses existing `completed=False` filter logic).

- [ ] **Step 3: Modify `process_penalties`**

In `core/tasks.py`, find the deadline computation block inside the loop (around line 109-113). Replace:

```python
        # Combine due_date + deadline_time into a timezone-aware datetime
        deadline_naive = datetime.combine(
            instance.due_date, instance.chore.deadline_time
        )
        deadline_aware = timezone.make_aware(deadline_naive)
```

with:

```python
        # Combine due_date + deadline_time into a timezone-aware datetime.
        # A missing deadline is treated as end-of-day for penalty purposes.
        deadline_time_val = instance.chore.deadline_time or time(23, 59, 59)
        deadline_naive = datetime.combine(instance.due_date, deadline_time_val)
        deadline_aware = timezone.make_aware(deadline_naive)
```

Also confirm the `time` symbol is imported. At the top of `core/tasks.py`, find the `from datetime import ...` line and ensure it includes `time`. If it imports only `datetime`, change it to `from datetime import datetime, time`. If `datetime` is imported some other way, add `from datetime import time` separately.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test core.tests.PenaltyJobNullDeadlineTests -v 2`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/tasks.py core/tests.py
git commit -m "feat(chores): penalty job treats missing deadline as end-of-day"
```

---

### Task 3: `CompleteChoreView` supports counter, cap, and unlimited

**Files:**
- Modify: `core/views.py` (`CompleteChoreView` @ line 537, imports @ line 36)
- Modify: `core/tests.py` (add `CompleteChoreCounterTests` class)

- [ ] **Step 1: Write the failing tests**

Append to `core/tests.py`:

```python
class CompleteChoreCounterTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)
        self.client.force_login(self.kid)

    def _make_instance(self, **chore_overrides):
        chore = _make_chore(self.parent, **chore_overrides)
        chore.assigned_to.add(self.kid)
        return ChoreInstance.objects.create(
            chore=chore,
            assigned_to=self.kid,
            due_date=timezone.localdate(),
        )

    def test_once_a_day_first_tap_completes(self):
        inst = self._make_instance(max_per_day=1, reward_minutes=5)
        resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
        self.assertEqual(resp.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 1)
        self.assertTrue(inst.completed)
        self.assertIsNotNone(inst.completed_at)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 5)

    def test_once_a_day_second_tap_rejected(self):
        inst = self._make_instance(max_per_day=1, reward_minutes=5)
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
        self.assertEqual(resp.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 1)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 5)

    def test_capped_chore_three_taps_then_rejected(self):
        inst = self._make_instance(max_per_day=3, reward_minutes=2)
        for _ in range(3):
            resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
        self.assertEqual(resp.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 3)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 6)
        # 3 EARN transactions
        earns = TimeBankTransaction.objects.filter(
            kid=self.kid, transaction_type="earn"
        )
        self.assertEqual(earns.count(), 3)

    def test_unlimited_chore_five_taps_all_accepted(self):
        inst = self._make_instance(max_per_day=None, reward_minutes=1)
        for _ in range(5):
            resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
            self.assertEqual(resp.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 5)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 5)

    def test_completed_at_set_on_first_tap_only(self):
        inst = self._make_instance(max_per_day=3, reward_minutes=2)
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        inst.refresh_from_db()
        first_completed_at = inst.completed_at
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        inst.refresh_from_db()
        self.assertEqual(inst.completed_at, first_completed_at)

    def test_zero_reward_chore_increments_count_no_transaction(self):
        inst = self._make_instance(
            max_per_day=2,
            reward_minutes=0,
            chore_type=Chore.ChoreType.BONUS,
            penalty_minutes=0,
        )
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 1)
        self.assertEqual(TimeBankTransaction.objects.filter(kid=self.kid).count(), 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.CompleteChoreCounterTests -v 2`
Expected: most fail — current view filters `completed=False` on the lookup, so the second tap returns 404 instead of 400; counter and unlimited cases all fail.

- [ ] **Step 3: Add `HttpResponseBadRequest` to view imports**

In `core/views.py`, find the line:

```python
from django.http import Http404, JsonResponse
```

and change it to:

```python
from django.http import Http404, HttpResponseBadRequest, JsonResponse
```

- [ ] **Step 4: Rewrite `CompleteChoreView.post`**

In `core/views.py`, replace the entire body of `CompleteChoreView.post` (around lines 540-569). The new body:

```python
    def post(self, request, instance_id):
        instance = get_object_or_404(
            ChoreInstance,
            pk=instance_id,
            assigned_to=request.user,
        )
        cap = instance.chore.max_per_day  # None = unlimited
        if cap is not None and instance.completion_count >= cap:
            return HttpResponseBadRequest("Already at daily limit")

        with transaction.atomic():
            locked = (
                ChoreInstance.objects.select_for_update()
                .get(pk=instance.pk)
            )
            if cap is not None and locked.completion_count >= cap:
                return HttpResponseBadRequest("Already at daily limit")
            locked.completion_count += 1
            if not locked.completed:
                locked.completed = True
                locked.completed_at = timezone.now()
            locked.save(
                update_fields=["completion_count", "completed", "completed_at"]
            )

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

        response = render(
            request, "core/_chore_item.html", {"instance": locked}
        )
        response["HX-Trigger"] = "chore-completed"
        return response
```

Key changes vs. the old version:
- Removed `completed=False` from the `get_object_or_404` lookup.
- Pre-check then `select_for_update` re-check on the cap.
- Counter increments unconditionally on a valid tap.
- `completed` / `completed_at` only set on the 0→1 transition.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test core.tests.CompleteChoreCounterTests -v 2`
Expected: 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add core/views.py core/tests.py
git commit -m "feat(chores): CompleteChoreView counter + cap + unlimited support"
```

---

### Task 4: `ChoreForm` synthetic completion_limit fields

**Files:**
- Modify: `core/forms.py` (`ChoreForm` @ line 13)
- Modify: `core/tests.py` (add `ChoreFormCompletionLimitTests` class)

- [ ] **Step 1: Write the failing tests**

Add `from core.forms import ChoreForm` to the imports near the top of `core/tests.py`. Then append to the end of `core/tests.py`:

```python
class ChoreFormCompletionLimitTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def _base_data(self, **overrides):
        data = dict(
            name="Test",
            chore_type="required",
            reward_minutes="5",
            penalty_minutes="10",
            time_of_day="morning",
            deadline_time="09:00",
            assigned_to=[str(self.kid.pk)],
            recurrence_type="daily",
            completion_limit="once",
            max_per_day_value="",
        )
        data.update(overrides)
        return data

    def test_once_saves_max_per_day_1(self):
        form = ChoreForm(data=self._base_data(completion_limit="once"))
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertEqual(chore.max_per_day, 1)

    def test_multiple_with_3_saves_max_per_day_3(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="3")
        )
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertEqual(chore.max_per_day, 3)

    def test_unlimited_saves_max_per_day_null(self):
        form = ChoreForm(data=self._base_data(completion_limit="unlimited"))
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertIsNone(chore.max_per_day)

    def test_multiple_with_no_value_is_invalid(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("max_per_day_value", form.errors)

    def test_multiple_with_1_is_invalid(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="1")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("max_per_day_value", form.errors)

    def test_deadline_time_optional(self):
        form = ChoreForm(data=self._base_data(deadline_time=""))
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertIsNone(chore.deadline_time)

    def test_editing_unlimited_chore_initializes_radio(self):
        chore = _make_chore(self.parent, max_per_day=None)
        form = ChoreForm(instance=chore)
        self.assertEqual(form.fields["completion_limit"].initial, "unlimited")

    def test_editing_multiple_chore_initializes_radio_and_value(self):
        chore = _make_chore(self.parent, max_per_day=5)
        form = ChoreForm(instance=chore)
        self.assertEqual(form.fields["completion_limit"].initial, "multiple")
        self.assertEqual(form.fields["max_per_day_value"].initial, 5)

    def test_editing_once_chore_initializes_radio(self):
        chore = _make_chore(self.parent, max_per_day=1)
        form = ChoreForm(instance=chore)
        self.assertEqual(form.fields["completion_limit"].initial, "once")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.ChoreFormCompletionLimitTests -v 2`
Expected: all fail — `completion_limit` field doesn't exist on the form.

- [ ] **Step 3: Rewrite `ChoreForm`**

Replace the entire `ChoreForm` class in `core/forms.py` (lines 13-94) with:

```python
class ChoreForm(forms.ModelForm):
    """Form for parent chore creation and editing."""

    LIMIT_ONCE = "once"
    LIMIT_MULTIPLE = "multiple"
    LIMIT_UNLIMITED = "unlimited"
    LIMIT_CHOICES = [
        (LIMIT_ONCE, "Once a day"),
        (LIMIT_MULTIPLE, "Multiple times per day"),
        (LIMIT_UNLIMITED, "Unlimited"),
    ]

    completion_limit = forms.ChoiceField(
        choices=LIMIT_CHOICES,
        widget=forms.RadioSelect,
        initial=LIMIT_ONCE,
    )
    max_per_day_value = forms.IntegerField(
        min_value=2,
        required=False,
        initial=2,
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
        widgets = {
            "chore_type": forms.RadioSelect,
            "recurrence_type": forms.RadioSelect,
            "assigned_to": forms.CheckboxSelectMultiple,
            "deadline_time": forms.TimeInput(attrs={"type": "time"}),
            "one_off_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show kids in assigned_to
        self.fields["assigned_to"].queryset = User.objects.filter(
            role=User.Role.KID
        ).order_by("first_name")
        # Make penalty_minutes not required at form level (validation in clean)
        self.fields["penalty_minutes"].required = False
        # Deadline is now optional
        self.fields["deadline_time"].required = False
        # Recurrence sub-fields are conditionally required
        self.fields["recurrence_days"].required = False
        self.fields["recurrence_interval"].required = False
        self.fields["one_off_date"].required = False

        # When editing, derive initial values for synthetic fields
        # from the model's max_per_day.
        if self.instance and self.instance.pk is not None:
            mpd = self.instance.max_per_day
            if mpd is None:
                self.fields["completion_limit"].initial = self.LIMIT_UNLIMITED
            elif mpd == 1:
                self.fields["completion_limit"].initial = self.LIMIT_ONCE
            else:
                self.fields["completion_limit"].initial = self.LIMIT_MULTIPLE
                self.fields["max_per_day_value"].initial = mpd

    def clean(self):
        cleaned = super().clean()
        chore_type = cleaned.get("chore_type")
        recurrence_type = cleaned.get("recurrence_type")

        # Bonus chores: force penalty to 0
        if chore_type == Chore.ChoreType.BONUS:
            cleaned["penalty_minutes"] = 0

        # Required chores: penalty must be > 0
        if chore_type == Chore.ChoreType.REQUIRED:
            penalty = cleaned.get("penalty_minutes")
            if not penalty or penalty <= 0:
                self.add_error(
                    "penalty_minutes",
                    "Required chores must have a penalty greater than 0.",
                )

        # Recurrence-specific validation
        if recurrence_type == Chore.RecurrenceType.ONCE:
            if not cleaned.get("one_off_date"):
                self.add_error(
                    "one_off_date",
                    "A date is required for one-off chores.",
                )

        if recurrence_type == Chore.RecurrenceType.CUSTOM:
            interval = cleaned.get("recurrence_interval")
            if not interval or interval <= 0:
                self.add_error(
                    "recurrence_interval",
                    "Custom recurrence requires an interval greater than 0.",
                )

        if recurrence_type == Chore.RecurrenceType.WEEKLY:
            days = cleaned.get("recurrence_days", "")
            if not days or not days.strip():
                self.add_error(
                    "recurrence_days",
                    "Weekly recurrence requires at least one day selected.",
                )

        # Completion limit: validate the synthetic pair.
        limit = cleaned.get("completion_limit")
        if limit == self.LIMIT_MULTIPLE:
            value = cleaned.get("max_per_day_value")
            if not value or value < 2:
                self.add_error(
                    "max_per_day_value",
                    "Choose a number of 2 or more when allowing multiple completions.",
                )

        return cleaned

    def save(self, commit=True):
        # Translate the synthetic completion_limit / max_per_day_value
        # pair into the model's max_per_day field.
        limit = self.cleaned_data.get("completion_limit")
        if limit == self.LIMIT_ONCE:
            self.instance.max_per_day = 1
        elif limit == self.LIMIT_UNLIMITED:
            self.instance.max_per_day = None
        elif limit == self.LIMIT_MULTIPLE:
            self.instance.max_per_day = self.cleaned_data.get("max_per_day_value")
        return super().save(commit=commit)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python manage.py test core.tests.ChoreFormCompletionLimitTests -v 2`
Expected: 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add core/forms.py core/tests.py
git commit -m "feat(chores): ChoreForm completion_limit picker + optional deadline"
```

---

### Task 5: `chore_form.html` — completion limit picker + optional deadline label

**Files:**
- Modify: `templates/core/chore_form.html`

This task is template-only — verification is by loading the form in a browser. No automated test step.

- [ ] **Step 1: Update the "Deadline Time" label to mark it optional**

In `templates/core/chore_form.html` find the deadline label (around line 116):

```html
<label for="{{ form.deadline_time.id_for_label }}" class="form-label fw-semibold">Deadline Time</label>
```

Change to:

```html
<label for="{{ form.deadline_time.id_for_label }}" class="form-label fw-semibold">Deadline Time <span class="text-muted fw-normal">(optional)</span></label>
```

- [ ] **Step 2: Add the completion-limit picker after the Assigned-To row**

In `templates/core/chore_form.html` find the closing of "Row 5: Assigned To" (the `<!-- Row 6: Recurrence Type (radio) -->` comment around line 140). Immediately BEFORE that comment, insert:

```html
                    <!-- Row 5b: Completion limit -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold d-block">How many times per day?</label>
                        {% for radio in form.completion_limit %}
                        <div class="form-check form-check-inline">
                            {{ radio.tag }}
                            <label class="form-check-label" for="{{ radio.id_for_label }}">{{ radio.choice_label }}</label>
                        </div>
                        {% endfor %}
                        {% for error in form.completion_limit.errors %}
                        <div class="text-danger small">{{ error }}</div>
                        {% endfor %}

                        <div class="mt-2 {% if form.completion_limit.value != 'multiple' %}d-none{% endif %}" id="max-per-day-group" style="max-width: 240px;">
                            <label for="{{ form.max_per_day_value.id_for_label }}" class="form-label small">Max times per day</label>
                            <input type="number" name="max_per_day_value" id="{{ form.max_per_day_value.id_for_label }}"
                                   value="{{ form.max_per_day_value.value|default_if_none:'' }}"
                                   class="form-control {% if form.max_per_day_value.errors %}is-invalid{% endif %}"
                                   min="2">
                            {% for error in form.max_per_day_value.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                            {% endfor %}
                        </div>
                    </div>
```

- [ ] **Step 3: Add the toggle JS**

In `templates/core/chore_form.html` find the `{% block extra_js %}` script. Inside the IIFE, after the "Toggle recurrence sub-fields" block (after the `toggleRecurrence();` call around line 248), add:

```javascript

    // ----- 2b. Toggle max-per-day input by completion_limit -----
    const completionLimitRadios = document.querySelectorAll('input[name="completion_limit"]');
    const maxPerDayGroup = document.getElementById('max-per-day-group');

    function toggleMaxPerDay() {
        const selected = document.querySelector('input[name="completion_limit"]:checked');
        const val = selected ? selected.value : '';
        if (val === 'multiple') {
            maxPerDayGroup.classList.remove('d-none');
        } else {
            maxPerDayGroup.classList.add('d-none');
        }
    }
    completionLimitRadios.forEach(r => r.addEventListener('change', toggleMaxPerDay));
    toggleMaxPerDay();
```

- [ ] **Step 4: Manual smoke test**

Start the dev server: `python manage.py runserver`

Log in as the parent. Visit `/chores/new/`. Verify:
- The "How many times per day?" group shows three radios; "Once a day" is selected; the number input is hidden.
- Selecting "Multiple times per day" reveals the number input.
- Selecting "Unlimited" hides the number input again.
- The Deadline Time label reads "Deadline Time (optional)".
- Leaving deadline blank and submitting saves the chore (no validation error).

Create three test chores you'll use in Task 7 smoke test:
- `Smoke Once` — once a day, reward 1 min
- `Smoke Multi 3` — multiple, max 3, reward 1 min
- `Smoke Unlimited` — unlimited, reward 1 min

- [ ] **Step 5: Commit**

```bash
git add templates/core/chore_form.html
git commit -m "feat(chores): chore form completion-limit picker + optional deadline label"
```

---

### Task 6: `_chore_item.html` — counter, cap-aware button, optional deadline display

**Files:**
- Modify: `templates/core/_chore_item.html`

This task is template-only — verification is by tapping the smoke chores from Task 5 in the browser.

- [ ] **Step 1: Replace the chore-item template**

Replace the entire contents of `templates/core/_chore_item.html` with:

```html
{% with cap=instance.chore.max_per_day count=instance.completion_count %}
{% if cap == None %}
    {% with at_cap=False unlimited=True %}
    {# unlimited: always tappable, no strikethrough #}
    <div id="chore-{{ instance.id }}" class="chore-item card mb-2">
        <div class="card-body d-flex align-items-center py-2 px-3">
            <div class="me-3">
                <button
                    hx-post="{% url 'complete_chore' instance.id %}"
                    hx-target="#chore-{{ instance.id }}"
                    hx-swap="outerHTML"
                    hx-disabled-elt="this"
                    class="btn btn-success btn-sm rounded-pill"
                >
                    Done!{% if count > 0 %} ×{{ count }}{% endif %}
                </button>
            </div>
            <div class="flex-grow-1">
                <span class="chore-name fw-semibold">{{ instance.chore.name }}</span>
                {% if instance.chore.deadline_time %}
                <br><small class="text-muted">by {{ instance.chore.deadline_time|time:"g:i A" }}</small>
                {% endif %}
            </div>
            <div class="text-end">
                {% if count > 0 %}
                <span class="badge bg-success-subtle text-success">+{{ instance.chore.reward_minutes }} min × {{ count }}</span>
                {% else %}
                <span class="badge bg-success-subtle text-success">+{{ instance.chore.reward_minutes }} min each</span>
                {% endif %}
            </div>
        </div>
    </div>
    {% endwith %}
{% else %}
    {# capped (1 or N): button until cap, then static checkmark #}
    <div id="chore-{{ instance.id }}" class="chore-item card mb-2{% if count >= cap %} completed{% endif %}">
        <div class="card-body d-flex align-items-center py-2 px-3">
            <div class="me-3">
                {% if count >= cap %}
                    {% if cap == 1 %}
                    <span class="text-success fs-4"><i class="bi bi-check-circle-fill"></i></span>
                    {% else %}
                    <span class="badge bg-success rounded-pill">{{ count }}/{{ cap }} done</span>
                    {% endif %}
                {% else %}
                <button
                    hx-post="{% url 'complete_chore' instance.id %}"
                    hx-target="#chore-{{ instance.id }}"
                    hx-swap="outerHTML"
                    hx-disabled-elt="this"
                    class="btn btn-success btn-sm rounded-pill"
                >
                    Done!{% if cap > 1 %} {{ count|add:1 }}/{{ cap }}{% endif %}
                </button>
                {% endif %}
            </div>
            <div class="flex-grow-1">
                <span class="chore-name{% if count >= cap %} text-decoration-line-through text-muted{% endif %} fw-semibold">
                    {{ instance.chore.name }}
                </span>
                {% if instance.chore.deadline_time %}
                <br><small class="text-muted">by {{ instance.chore.deadline_time|time:"g:i A" }}</small>
                {% endif %}
            </div>
            <div class="text-end">
                {% if count > 0 %}
                    {% if cap > 1 %}
                    <span class="badge bg-success-subtle text-success">+{{ instance.chore.reward_minutes }} min × {{ count }} earned</span>
                    {% else %}
                    <span class="badge bg-success-subtle text-success">+{{ instance.chore.reward_minutes }} min earned</span>
                    {% endif %}
                {% elif instance.chore.chore_type == "bonus" %}
                <span class="badge bg-success-subtle text-success">+{{ instance.chore.reward_minutes }} min</span>
                {% else %}
                <span class="badge bg-info-subtle text-info">+{{ instance.chore.reward_minutes }} min</span>
                <span class="badge bg-danger-subtle text-danger">-{{ instance.chore.penalty_minutes }} min if missed</span>
                {% endif %}
            </div>
        </div>
    </div>
{% endif %}
{% endwith %}
```

Behavior summary:
- `max_per_day` is `None` (unlimited) → always tappable, "Done!" or "Done! ×N", reward shown as "× N earned"/"× N", no strikethrough.
- `max_per_day = 1` (once) → identical to today's rendering: green checkmark when done, button otherwise.
- `max_per_day = N ≥ 2` (capped, not at cap) → "Done! K+1/N" button.
- `max_per_day = N ≥ 2` (capped, at cap) → "N/N done" pill, name struck through.

- [ ] **Step 2: Manual smoke test**

Restart the dev server if needed. Log in as the kid. Visit the kid chore list.

- For `Smoke Once`: see "Done!" button. Tap → green checkmark. Verify balance is +1.
- For `Smoke Multi 3`: see "Done! 1/3". Tap → "Done! 2/3". Tap → "Done! 3/3". Tap → "3/3 done" pill, name struck through. Verify balance is +3 from this chore.
- For `Smoke Unlimited`: see "Done!". Tap multiple times → "Done! ×1", "Done! ×2", etc. Verify balance keeps climbing.

- [ ] **Step 3: Commit**

```bash
git add templates/core/_chore_item.html
git commit -m "feat(chores): kid chore row shows counter + cap-aware button"
```

---

### Task 7: Full verification

**Files:** none (verification checkpoint)

- [ ] **Step 1: Run all tests**

Run: `python manage.py test core -v 2`
Expected: all tests pass, including the four new test classes (`MultiCompletionSchemaTests`, `PenaltyJobNullDeadlineTests`, `CompleteChoreCounterTests`, `ChoreFormCompletionLimitTests`) and the pre-existing timer tests.

- [ ] **Step 2: Django system check**

Run: `python manage.py check`
Expected: `System check identified no issues.`

- [ ] **Step 3: Run migrations on a fresh DB**

```bash
rm db.sqlite3
python manage.py migrate
```

Expected: all migrations apply cleanly through `0015_multi_completions_and_optional_deadline`. (Re-seed any local test data afterward — this step verifies the migration chain, not preserving local data.)

- [ ] **Step 4: End-to-end smoke (parent + kid flow)**

Start the dev server, log in as the parent, create:
- A required chore with `max_per_day = 1`, deadline = `7:00 PM`.
- A required chore with `max_per_day = 3`, no deadline.
- A bonus chore with unlimited completions, reward 1 min.

Log in as the kid. Verify:
- The first chore shows the deadline; the second and third don't.
- Completing each multi/unlimited chore increments the counter and the balance badge.
- At the cap on chore #2, the button greys out.
- Reload the page — counts persist.
- Refresh as parent → chore log shows the completions; transaction history shows one EARN per tap.

- [ ] **Step 5: Final commit (no code changes)**

If anything came up in smoke testing that needs a quick fix, address it in a small follow-up commit. Otherwise nothing to commit — the feature is shipped.
