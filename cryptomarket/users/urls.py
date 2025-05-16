from django.urls import path
from .views import RegisterView, DeleteUserView

urlpatterns = [
    path("public/register", RegisterView.as_view(), name="register"),
    path("admin/user/<uuid:user_id>", DeleteUserView.as_view(), name="delete_user"),
]