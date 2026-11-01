from django.contrib import admin
from django.urls import path, include
from .frontend import frontend
from booking import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("bookings/", views.history),
    path("bookings/<int:pk>/cancel/", views.cancel_page),
    path("api/session/", views.session),
    path("api/resources/", views.resources),
    path("api/availability/", views.availability),
    path("api/bookings/", views.bookings),
    path("api/bookings/create/", views.create),
    path("api/bookings/<int:pk>/cancel/", views.cancel_api),
    path("", frontend),
    path("<path:path>", frontend),
]
