from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("destek/", views.support, name="support"),
    path("yasal/<slug:slug>/", views.legal, name="legal"),
]
