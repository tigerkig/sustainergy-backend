from sustainergy_dashboard.models import User
from django.core.exceptions import PermissionDenied
from rest_framework import permissions



class IsInstallerMixin(permissions.BasePermission):
    """Permission class to check if user is an installer"""
    def has_permission(self, request, view):
        is_installer = True if request.user.is_installer() else False
        return is_installer