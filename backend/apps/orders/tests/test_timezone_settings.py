import datetime

from django.conf import settings
from django.test import TestCase
from django.utils import timezone


class TimeZoneSettingsTests(TestCase):
    """T69 — TIME_ZONE = America/Bogota (RF-14 support, 003-RF-14)."""

    def test_time_zone_is_america_bogota(self):
        self.assertEqual(settings.TIME_ZONE, "America/Bogota")

    def test_localdate_reflects_bogota_not_utc(self):
        # 2026-03-10 02:00 UTC is still 2026-03-09 at night in Bogota (UTC-5).
        instant = datetime.datetime(2026, 3, 10, 2, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(timezone.localdate(instant), datetime.date(2026, 3, 9))
