from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from taskForce.accounts.tests import PARIS, NOW
from taskForce.tasks.locations import location_summary
from taskForce.tasks.models import Task, GroceryItem, ChoreItem, ChoreCompletion
from taskForce.units.models import Unit, Membership

User = get_user_model()


class TaskCompletionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="x")
        self.mate = User.objects.create_user(username="mate", password="x")

        self.unit = Unit.objects.create(name="Alpha")
        Membership.objects.create(user=self.owner, unit=self.unit, role="commander")
        Membership.objects.create(user=self.mate, unit=self.unit, role="operative")

        self.task = Task.objects.create(
            name="Secure the perimeter",
            user=self.owner,
            unit=self.unit,
            appointed_points=5,
        )

    def test_unit_member_can_complete_another_members_task(self):
        self.assertTrue(self.task.complete(self.mate))

        self.task.refresh_from_db()
        self.mate.avatar.refresh_from_db()
        self.owner.avatar.refresh_from_db()

        self.assertTrue(self.task.is_done)
        self.assertEqual(self.task.assigned_to, self.mate)
        self.assertIsNotNone(self.task.accomplished_at)
        self.assertEqual(self.mate.avatar.points, 5)
        self.assertEqual(self.owner.avatar.points, 0)

    def test_completing_twice_awards_points_once(self):
        self.assertTrue(self.task.complete(self.mate))
        self.assertFalse(self.task.complete(self.mate))

        self.mate.avatar.refresh_from_db()
        self.assertEqual(self.mate.avatar.points, 5)

    def test_task_visible_to_unit_member(self):
        self.assertIn(self.task, Task.objects.visible_to(self.mate))

    def test_task_not_visible_to_outsider(self):
        outsider = User.objects.create_user(username="outsider", password="x")
        self.assertNotIn(self.task, Task.objects.visible_to(outsider))

    def test_outsider_cannot_toggle_item(self):
        self.task.type = "groceries"
        self.task.save()
        item = GroceryItem.objects.create(task=self.task, name="Rations")

        outsider = User.objects.create_user(username="outsider2", password="x")
        self.client.force_login(outsider)

        response = self.client.post(
            reverse("toggle-item", kwargs={"task_pk": self.task.pk, "item_pk": item.pk})
        )

        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertFalse(item.is_done)


class ChoreRecurrenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="chores", password="x")
        self.task = Task.objects.create(
            name="Weekly clean", user=self.user, type="chores"
        )

    def test_never_done_recurring_chore_is_due(self):
        chore = ChoreItem.objects.create(
            task=self.task, name="Mop", frequency_days=7
        )
        annotated = ChoreItem.objects.with_due_state().get(pk=chore.pk)
        self.assertTrue(annotated.is_due)

    def test_chore_is_due_after_frequency_elapses(self):
        overdue = ChoreItem.objects.create(
            task=self.task, name="Mop", frequency_days=1,
            last_done_at=timezone.now() - timedelta(days=3),
        )
        fresh = ChoreItem.objects.create(
            task=self.task, name="Dust", frequency_days=30,
            last_done_at=timezone.now(),
        )
        states = dict(
            ChoreItem.objects.with_due_state().values_list("pk", "is_due")
        )
        self.assertTrue(states[overdue.pk])
        self.assertFalse(states[fresh.pk])

    def test_non_recurring_chore_is_never_due(self):
        chore = ChoreItem.objects.create(task=self.task, name="Fix the sink")
        annotated = ChoreItem.objects.with_due_state().get(pk=chore.pk)
        self.assertFalse(annotated.is_due)

    def test_toggling_recurring_chore_logs_completion(self):
        chore = ChoreItem.objects.with_due_state().get(
            pk=ChoreItem.objects.create(
                task=self.task, name="Mop", frequency_days=7
            ).pk
        )
        chore.toggle()

        chore.refresh_from_db()
        self.assertEqual(chore.completions.count(), 1)
        self.assertIsNotNone(chore.last_done_at)

    def test_untoggling_restores_previous_completion(self):
        chore = ChoreItem.objects.create(
            task=self.task, name="Mop", frequency_days=7
        )
        old = timezone.now() - timedelta(days=30)
        ChoreCompletion.objects.create(chore_item=chore, done_at=old)
        chore.last_done_at = old
        chore.save(update_fields=["last_done_at"])

        ChoreItem.objects.with_due_state().get(pk=chore.pk).toggle()
        ChoreItem.objects.with_due_state().get(pk=chore.pk).toggle()

        chore.refresh_from_db()
        self.assertEqual(chore.completions.count(), 1)
        self.assertEqual(chore.last_done_at, old)

    def test_untoggling_only_completion_clears_last_done_at(self):
        chore = ChoreItem.objects.create(
            task=self.task, name="Mop", frequency_days=7
        )
        ChoreItem.objects.with_due_state().get(pk=chore.pk).toggle()
        ChoreItem.objects.with_due_state().get(pk=chore.pk).toggle()

        chore.refresh_from_db()
        self.assertEqual(chore.completions.count(), 0)
        self.assertIsNone(chore.last_done_at)


class LocationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("operative", password="x")
        cls.other = User.objects.create_user("stranger", password="x")

    def make(self, **kwargs):
        kwargs.setdefault("user", self.user)
        kwargs.setdefault("name", "mission")
        return Task.objects.create(**kwargs)


class LocationSummaryTests(LocationTestCase):
    def summary(self):
        with timezone.override(PARIS):
            return location_summary(self.user, now=NOW)

    def test_counts_open_missions_per_location(self):
        self.make(type="workout")
        self.make(type="workout")
        self.make(type="workout", is_done=True)
        self.make(type=None)
        s = self.summary()
        self.assertEqual(s["training"]["count"], 2)
        self.assertEqual(s["hq"]["count"], 1)
        self.assertEqual(s["supply"]["count"], 0)

    def test_overdue_mission_flags_only_its_location(self):
        self.make(type="groceries", due_date=NOW - timedelta(days=1))
        self.make(type="workout", due_date=NOW + timedelta(days=2))
        s = self.summary()
        self.assertTrue(s["supply"]["overdue"])
        self.assertFalse(s["training"]["overdue"])

    def test_due_chore_flags_barracks(self):
        task = self.make(type="chores")
        ChoreItem.objects.create(
            task=task, name="sweep",
            frequency_days=1, last_done_at=NOW - timedelta(days=30),
        )
        self.assertTrue(self.summary()["barracks"]["overdue"])

    def test_just_after_midnight_paris_is_not_today(self):
        self.make(type="workout", due_date=datetime(2026, 10, 19, 0, 30, tzinfo=PARIS))
        self.assertFalse(self.summary()["training"]["due_today"])

    def test_counts_not_inflated_by_unit_membership(self):
        unit = Unit.objects.create(name="Alpha", created_by=self.user)
        Membership.objects.create(unit=unit, user=self.user, role="commander")
        Membership.objects.create(unit=unit, user=self.other, role="member")
        self.make(type="workout", unit=unit)
        self.assertEqual(self.summary()["training"]["count"], 1)

    def test_critical_flags_only_its_location(self):
        self.make(type="groceries", priority=1)
        s = self.summary()
        self.assertTrue(s["supply"]["critical"])
        self.assertFalse(s["training"]["critical"])

    def test_due_later_today_is_not_overdue(self):
        self.make(type="workout", due_date=NOW + timedelta(hours=3))
        s = self.summary()["training"]
        self.assertTrue(s["due_today"])
        self.assertFalse(s["overdue"])


class TaskNextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("operative", password="x")
        cls.task = Task.objects.create(user=cls.user, name="mission")

    def setUp(self):
        self.client.force_login(self.user)

    def test_back_link_follows_next(self):
        url = reverse("details-task", args=[self.task.pk])
        response = self.client.get(url, {"next": "/deploy/barracks/"})
        self.assertEqual(response.context["back_url"], "/deploy/barracks/")

    def test_unsafe_next_is_ignored(self):
        url = reverse("details-task", args=[self.task.pk])
        response = self.client.get(url, {"next": "https://evil.example/"})
        self.assertEqual(response.context["back_url"], reverse("all-tasks"))

    def test_delete_returns_to_next(self):
        url = reverse("delete-task", args=[self.task.pk])  # your actual name
        response = self.client.post(url, {"next": "/deploy/barracks/"})
        self.assertRedirects(response, "/deploy/barracks/", fetch_redirect_response=False)