"""ChoreBank URL configuration.

Plan 03 adds kid and parent landing page URLs.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("admin/", admin.site.urls),
]
