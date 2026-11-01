from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy
from . import views

app_name = "accounts"
urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth.LoginView.as_view(
            template_name="accounts/form.html", extra_context={"title": "تسجيل الدخول"}
        ),
        name="login",
    ),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("", views.profile, name="profile"),
    path(
        "password/",
        auth.PasswordChangeView.as_view(
            template_name="accounts/form.html",
            success_url=reverse_lazy("accounts:profile"),
            extra_context={"title": "تغيير كلمة المرور"},
        ),
        name="password",
    ),
]
