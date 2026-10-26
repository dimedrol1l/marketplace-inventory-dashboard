from django import forms

from .models import StockBalance


class OwnStockForm(forms.ModelForm):
    class Meta:
        model = StockBalance
        fields = ["warehouse", "sku", "product_name", "available_quantity"]
        widgets = {
            "warehouse": forms.TextInput(attrs={"placeholder": "Например, Основной склад"}),
            "sku": forms.TextInput(attrs={"placeholder": "Артикул продавца"}),
            "product_name": forms.TextInput(attrs={"placeholder": "Название товара"}),
            "available_quantity": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_warehouse(self):
        warehouse = self.cleaned_data["warehouse"].strip()
        if not warehouse:
            raise forms.ValidationError("Укажите название склада.")
        return warehouse

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip()
        if not sku:
            raise forms.ValidationError("Укажите артикул.")
        return sku
