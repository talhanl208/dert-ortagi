from django.urls import path

from . import views

app_name = "sohbet"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("istek/<uuid:public_id>/", views.request_chat, name="request"),
    path("eslestir/<uuid:public_id>/<uuid:user_id>/", views.match_request, name="match"),
    path("<uuid:public_id>/", views.detail, name="detail"),
    path("<uuid:public_id>/gonder/", views.send, name="send"),
    path("<uuid:public_id>/yeni/", views.poll, name="poll"),
    path("<uuid:public_id>/kabul/", views.accept, name="accept"),
    path("<uuid:public_id>/reddet/", views.decline, name="decline"),
    path("<uuid:public_id>/bitir/", views.close, name="close"),
]
