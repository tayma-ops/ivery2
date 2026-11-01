from django.core.management.base import BaseCommand
from booking.models import Service, Resource, ScheduleLock


class Command(BaseCommand):
    help = "Create fictional demo services and resources, without changing existing records."

    def handle(self, *args, **options):
        ScheduleLock.objects.get_or_create(pk=1)
        for index, specialty in enumerate(
            ["طب الأسنان", "طب الأطفال", "الباطنية", "الجلدية", "العيون"], 1
        ):
            service, _ = Service.objects.get_or_create(
                code=f"specialty-{index}",
                defaults={"name": specialty, "price": 100, "duration": 30},
            )
            for city in ["الرياض", "جدة", "الدمام", "مكة المكرمة"]:
                Resource.objects.get_or_create(
                    name=f"عيادة تجريبية — {specialty} — {city}",
                    defaults={"specialty": specialty, "city": city, "service": service},
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Fictional demo services are ready. No accounts created."
            )
        )
