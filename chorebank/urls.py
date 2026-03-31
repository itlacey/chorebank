"""ChoreBank URL configuration.

Plan 02 adds auth URLs (login, logout, PIN change).
Plan 03 adds kid and parent landing page URLs.
"""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
