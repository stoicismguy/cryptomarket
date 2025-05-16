from django.urls import path
from . import views

urlpatterns = [
    path('public/instrument', views.InstrumentListView.as_view(), name='instrument-list'),
    path('public/orderbook/<str:ticker>', views.OrderBookView.as_view(), name='orderbook'),
    path('public/transactions/<str:ticker>', views.TransactionHistoryView.as_view(), name='transaction-history'),
    
    # Административные API для инструментов
    path('admin/instrument', views.AdminInstrumentView.as_view(), name='admin-instrument-create'),
    path('admin/instrument/<str:ticker>', views.AdminInstrumentDetailView.as_view(), name='admin-instrument-delete'),
] 