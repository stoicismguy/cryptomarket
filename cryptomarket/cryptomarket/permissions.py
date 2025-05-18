from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        print(request.user.is_authenticated, request.user.role)
        if request.user.is_authenticated and request.user.role == "ADMIN":
            return True
        raise PermissionDenied({
            "detail": [
                {
                "loc": [
                    "string",
                    0
                ],
                "msg": "You are not authorized to perform this action",
                "type": "permission_denied"
                }
            ]
        })