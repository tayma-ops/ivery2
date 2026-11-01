from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="المستخدم"
    )

    phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")

    city = models.CharField(max_length=100, blank=True, verbose_name="المدينة")

    address = models.TextField(blank=True, verbose_name="العنوان")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "الملف الشخصي"
        verbose_name_plural = "الملفات الشخصية"

    def __str__(self):
        return self.user.username
