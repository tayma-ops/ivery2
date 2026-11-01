from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Service, Resource, Reservation
from .services import cancel


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price", "duration", "active")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "specialty", "city", "active")
    list_filter = ("specialty", "city", "active")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "resource", "start", "status", "total")
    list_filter = ("status", "resource", "start")
    search_fields = ("customer", "phone", "user__username")
    readonly_fields = tuple(f.name for f in Reservation._meta.fields)
    actions = ("confirm", "complete", "cancel_selected")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="تأكيد الحجوزات المنتظرة")
    def confirm(self, request, queryset):
        queryset.filter(status="pending").update(status="confirmed")

    @admin.action(description="إنهاء الحجوزات التي بدأ موعدها")
    def complete(self, request, queryset):
        from django.utils import timezone

        queryset.filter(status="confirmed", end__lte=timezone.now()).update(
            status="completed"
        )

    @admin.action(description="إلغاء الحجوزات القادمة وإتاحة أوقاتها")
    def cancel_selected(self, request, queryset):
        for row in queryset:
            try:
                cancel(row.pk, request.user, staff=True)
            except ValidationError as exc:
                self.message_user(request, " ".join(exc.messages), messages.ERROR)
