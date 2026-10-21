from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("kayit/", views.register, name="register"),
    path("giris/", views.LoginView.as_view(), name="login"),
    path("cikis/", views.LogoutView.as_view(), name="logout"),
    path("ayarlar/", views.settings_view, name="settings"),
    path("acik-riza/", views.consent, name="consent"),
    path("acik-riza/geri-al/", views.withdraw_consent, name="withdraw_consent"),
    path("verilerim/", views.export_data, name="export"),
    path("sil/", views.delete_account, name="delete"),
    path("parola/", views.PasswordChangeView.as_view(), name="password_change"),
    path("parola/tamam/", views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("parola-sifirla/", views.PasswordResetView.as_view(), name="password_reset"),
    path("parola-sifirla/gonderildi/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "parola-sifirla/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("parola-sifirla/tamam/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
