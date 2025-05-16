from django.contrib import admin
from django.urls import include, path
from cryptomarket.settings import API_PREFIX

urlpatterns = [
    path('admin/', admin.site.urls),
    path(API_PREFIX.lstrip('/'), include('users.urls')),
    path(API_PREFIX.lstrip('/'), include('order.urls')),
    path(API_PREFIX.lstrip('/'), include('balance.urls')),
    path(API_PREFIX.lstrip('/'), include('public.urls')),
]
