from django.urls import path

from . import views

app_name = "dertler"

urlpatterns = [
    path("", views.dert_list, name="list"),
    path("anlat/", views.dert_create, name="create"),
    path("benim/", views.my_dertler, name="mine"),
    path("dinle/", views.listen, name="listen"),
    path("<uuid:public_id>/", views.dert_detail, name="detail"),
    path("<uuid:public_id>/duzenle/", views.dert_edit, name="edit"),
    path("<uuid:public_id>/sil/", views.dert_delete, name="delete"),
    path("<uuid:public_id>/durum/", views.dert_status, name="status"),
    path("<uuid:public_id>/tepki/", views.react, name="react"),
]
