from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import ProfileForm, SignupForm
from .models import Profile


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Profile.objects.create(user=user)
        login(request, user)
        return redirect("/")
    return render(request, "accounts/form.html", {"form": form, "title": "إنشاء حساب"})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "حُفظت بياناتك.")
        return redirect("accounts:profile")
    return render(request, "accounts/form.html", {"form": form, "title": "حسابي"})
