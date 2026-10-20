from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from taskForce.tasks.locations import missions_at, LOCATIONS
from taskForce.tasks.models import Task

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=PARIS)


class HqLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("operative", password="x")
        cls.other = User.objects.create_user("stranger", password="x")

    def make(self, **kwargs):
        kwargs.setdefault("user", self.user)
        kwargs.setdefault("name", "mission")
        return Task.objects.create(**kwargs)

    def hq(self):
        with timezone.override(PARIS):
            return set(missions_at(self.user, "hq", now=NOW))

    def test_untyped_missions_both_null_and_empty(self):
        a = self.make(type=None)
        b = self.make(type="")
        self.assertEqual(self.hq(), {a, b})

    def test_typed_missions_never_at_hq(self):
        self.make(type="workout", due_date=NOW)
        self.make(type="chores", due_date=NOW - timedelta(days=3))
        self.make(type="groceries", due_date=None)
        self.assertEqual(self.hq(), set())

    def test_just_after_midnight_paris_is_tomorrow(self):
        self.make(type="workout", due_date=datetime(2026, 10, 19, 0, 30, tzinfo=PARIS))
        self.assertEqual(self.hq(), set())

    def test_done_and_invisible_missions_excluded(self):
        self.make(type=None, is_done=True)
        self.make(type=None, user=self.other)
        self.assertEqual(self.hq(), set())


class LocationCoverageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("operative", password="x")

    def test_every_open_mission_is_in_exactly_one_location(self):
        types = [None, ""] + [value for value, _ in Task.TYPE_CHOICES]
        missions = [
            Task.objects.create(user=self.user, name=f"m-{t}-{due}", type=t, due_date=due)
            for t in types
            for due in (None, NOW)
        ]

        with timezone.override(PARIS):
            placements = {
                key: set(missions_at(self.user, key, now=NOW))
                for key in LOCATIONS
            }

        for mission in missions:
            found = [key for key, placed in placements.items() if mission in placed]
            with self.subTest(type=mission.type, due=mission.due_date):
                self.assertEqual(len(found), 1, f"found in {found}")