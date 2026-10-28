from django import forms
from django.utils.translation import gettext_lazy as _


class ReportFilterForm(forms.Form):
    REPORT_CHOICES = (
        ("inventory", _("Current Inventory")),
        ("stock_in", _("Stock In")),
        ("stock_out", _("Stock Out")),
        ("low_stock", _("Low Stock")),
        ("products", _("Products")),
        ("categories", _("Categories")),
    )

    report = forms.ChoiceField(choices=REPORT_CHOICES)
    date_from = forms.DateField(required=False)
    date_to = forms.DateField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from and date_to and date_from > date_to:
            self.add_error("date_to", _("The end date must be on or after the start date."))
        return cleaned_data
