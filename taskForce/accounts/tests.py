from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from taskForce.tasks.locations import missions_at
from taskForce.tasks.models import Task

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=PARIS)


class GateLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("operative", password="x")
        cls.other = User.objects.create_user("stranger", password="x")

    def make(self, **kwargs):
        kwargs.setdefault("user", self.user)
        kwargs.setdefault("name", "mission")
        return Task.objects.create(**kwargs)

    def gate(self):
        with timezone.override(PARIS):
            return set(missions_at(self.user, "gate", now=NOW))

    def test_untyped_missions_both_null_and_empty(self):
        a = self.make(type=None)
        b = self.make(type="")
        self.assertEqual(self.gate(), {a, b})

    def test_typed_missions_due_today_or_overdue(self):
        today = self.make(type="workout", due_date=NOW + timedelta(hours=2))
        overdue = self.make(type="chores", due_date=NOW - timedelta(days=3))
        self.assertEqual(self.gate(), {today, overdue})

    def test_typed_missions_not_due_are_not_at_gate(self):
        self.make(type="workout", due_date=NOW + timedelta(days=2))
        self.make(type="groceries", due_date=None)
        self.assertEqual(self.gate(), set())

    def test_just_after_midnight_paris_is_tomorrow(self):
        self.make(type="workout", due_date=datetime(2026, 10, 19, 0, 30, tzinfo=PARIS))
        self.assertEqual(self.gate(), set())

    def test_done_and_invisible_missions_excluded(self):
        self.make(type=None, is_done=True)
        self.make(type=None, user=self.other)
        self.assertEqual(self.gate(), set())