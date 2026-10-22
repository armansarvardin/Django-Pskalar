from django.forms import ModelForm
from apps.finance.models import Payment

class PaymentAdminForm(ModelForm):
    class Meta:
        model = Payment
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get("method")
        external_ref = cleaned_data.get("external_ref")

        if method and method.requires_reference and not external_ref:
            self.add_error("external_ref", "This payment method needs a transaction ID.")
            return cleaned_data