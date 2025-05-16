from django.contrib import admin
from .models import LimitOrder, MarketOrder, Transaction, Instrument

admin.site.register(LimitOrder)
admin.site.register(MarketOrder)
admin.site.register(Transaction)
admin.site.register(Instrument)
