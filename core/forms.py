"""Forms for ChoreBank chore management.

ChoreForm -- ModelForm for creating and editing chores with conditional
validation (bonus chores force penalty to 0, recurrence fields validated
based on recurrence_type selection).
"""

from django import forms

from core.models import Chore, User


class ChoreForm(forms.ModelForm):
    """Form for parent chore creation and editing."""

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
        # Recurrence sub-fields are conditionally required
        self.fields["recurrence_days"].required = False
        self.fields["recurrence_interval"].required = False
        self.fields["one_off_date"].required = False

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

        return cleaned
