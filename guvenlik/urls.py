from django.urls import path

from . import views

app_name = "guvenlik"

urlpatterns = [
    path("sikayet/<str:target>/<uuid:public_id>/", views.report, name="report"),
    path("engelle/<str:target>/<uuid:public_id>/", views.block, name="block"),
    path("engeli-kaldir/<int:block_id>/", views.unblock_view, name="unblock"),
    path("engellediklerim/", views.blocked_list, name="blocked"),
]
