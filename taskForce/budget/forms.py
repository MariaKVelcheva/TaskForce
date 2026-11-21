from decimal import Decimal

from django import forms


class SpendingForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    spent_on = forms.DateField(required=False)


class BudgetForm(forms.Form):
    monthly_budget = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"), required=False,
    )

