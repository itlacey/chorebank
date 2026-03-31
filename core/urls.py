"""Core URL patterns for ChoreBank authentication."""

from django.urls import path

from core.views import LoginView, LogoutView, PinChangeView, PinResetView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("pin/change/", PinChangeView.as_view(), name="pin_change"),
    path("pin/reset/", PinResetView.as_view(), name="pin_reset"),
]
