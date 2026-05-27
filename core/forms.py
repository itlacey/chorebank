"""Forms for ChoreBank chore management.

ChoreForm -- ModelForm for creating and editing chores with conditional
validation (bonus chores force penalty to 0, recurrence fields validated
based on recurrence_type selection).
"""

from django import forms

from core.models import Chore, User


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
            "timer_prerequisite",
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
        # Only add our custom error when there is no existing field-level error
        # on max_per_day_value (e.g. the min_value=2 validator already fired).
        # This avoids stacking two errors on the same field for value=1.
        limit = cleaned.get("completion_limit")
        if limit == self.LIMIT_MULTIPLE:
            if cleaned.get("max_per_day_value") is None and "max_per_day_value" not in self.errors:
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


class TimeAdjustForm(forms.Form):
    """Form for parent manual time bank adjustments."""

    kid = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.KID).order_by("first_name"),
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
    )
    amount = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Minutes",
                "id": "id_amount",
            }
        ),
        help_text="Positive to add, negative to subtract",
    )
    note = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Optional note (e.g., 'Extra chores today')",
            }
        ),
    )
