from django.contrib import admin
from .models import Order, OzonSync, StockBalance

admin.site.register(Order)
admin.site.register(StockBalance)
admin.site.register(OzonSync)
