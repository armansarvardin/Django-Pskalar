from django.forms import ModelForm
from apps.finance.models import Payment
from django.core.exceptions import ValidationError

class PaymentAdminForm(ModelForm):
    class Meta:
        model = Payment
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get("method")
        external_ref = cleaned_data.get("external_ref")
        rental = cleaned_data.get("rental")
        sale = cleaned_data.get("sale")

        if rental and sale:
            raise ValidationError("Choose a rental or a sale, not both")
        if not rental and not sale:
            raise ValidationError("Choose a rental or a sale")

        if method and method.requires_reference and not external_ref:
            self.add_error("external_ref", "This payment method needs a transaction ID.")
            return cleaned_data