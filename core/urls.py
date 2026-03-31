"""Core URL patterns for ChoreBank."""

from django.urls import path

from core.views import (
    HomeRouterView,
    KidHomeView,
    LoginView,
    LogoutView,
    ParentHomeView,
    PinChangeView,
    PinResetView,
)

urlpatterns = [
    # Home router -- redirects to role-appropriate landing page
    path("", HomeRouterView.as_view(), name="home"),
    # Auth
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("pin/change/", PinChangeView.as_view(), name="pin_change"),
    path("pin/reset/", PinResetView.as_view(), name="pin_reset"),
    # Landing pages
    path("kid/", KidHomeView.as_view(), name="kid_home"),
    path("parent/", ParentHomeView.as_view(), name="parent_home"),
]
