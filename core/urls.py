"""Core URL patterns for ChoreBank."""

from django.urls import path

from core.views import (
    ChoreTemplateLoadView,
    HomeRouterView,
    KidHomeView,
    LoginView,
    LogoutView,
    ParentChoreCreateView,
    ParentChoreDeleteView,
    ParentChoreEditView,
    ParentChoreListView,
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
    # Parent chore CRUD
    path("parent/chores/", ParentChoreListView.as_view(), name="chore_list"),
    path("parent/chores/create/", ParentChoreCreateView.as_view(), name="chore_create"),
    path("parent/chores/<int:pk>/edit/", ParentChoreEditView.as_view(), name="chore_edit"),
    path("parent/chores/<int:pk>/delete/", ParentChoreDeleteView.as_view(), name="chore_delete"),
    path("parent/chores/load-template/", ChoreTemplateLoadView.as_view(), name="chore_load_template"),
]
