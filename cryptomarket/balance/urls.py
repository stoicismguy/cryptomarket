from django.urls import path
from . import views

urlpatterns = [
    path('balance', views.BalanceView.as_view(), name='balance'),
    path('admin/balance/deposit', views.AdminBalanceDepositView.as_view(), name='admin-balance-deposit'),
    path('admin/balance/withdraw', views.AdminBalanceWithdrawView.as_view(), name='admin-balance-withdraw'),
] 