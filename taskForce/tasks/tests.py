from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from taskForce.accounts.tests import PARIS, NOW
from taskForce.tasks.forms import LocationQuickAddForm
from taskForce.tasks.items import item_progress
from taskForce.tasks.locations import location_summary, LOCATIONS, missions_at
from taskForce.tasks.models import Task, GroceryItem, ChoreItem, ChoreCompletion, WorkoutItem
from taskForce.tasks.urgency import group_by_urgency, bucket_for
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

    def test_second_completion_shows_no_success_message(self):
        task = Task.objects.create(user=self.user, name="mission")
        url = reverse("complete-task", args=[task.pk])
        self.client.post(url, follow=True)
        response = self.client.post(url, follow=True)
        texts = [str(m) for m in response.context["messages"]]
        self.assertFalse(any("pts" in t for t in texts))
        self.assertTrue(any("already accomplished" in t for t in texts))

    def test_item_progress_counts(self):
        task = Task.objects.create(user=self.user, name="run", type="workout")
        WorkoutItem.objects.create(task=task, name="a", is_done=True)
        WorkoutItem.objects.create(task=task, name="b")
        WorkoutItem.objects.create(task=task, name="c")
        annotated = Task.objects.annotate(**item_progress()).get(pk=task.pk)
        self.assertEqual((annotated.items_done, annotated.items_total), (1, 3))

    def test_mission_without_items_counts_zero(self):
        task = Task.objects.create(user=self.user, name="empty", type="workout")
        annotated = Task.objects.annotate(**item_progress()).get(pk=task.pk)
        self.assertEqual((annotated.items_done, annotated.items_total), (0, 0))

    def test_today_chip_sets_end_of_day(self):
        with timezone.override(PARIS):
            form = LocationQuickAddForm({"name": "m", "priority": 3, "when": "today"}, now=NOW)
            self.assertTrue(form.is_valid(), form.errors)
            due = timezone.localtime(form.cleaned_data["due_date"])
        self.assertEqual((due.date(), due.hour, due.minute), (NOW.date(), 23, 59))

    def test_pick_without_date_is_an_error(self):
        form = LocationQuickAddForm({"name": "m", "priority": 3, "when": "pick"})
        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)

    def test_no_date_ignores_a_submitted_date(self):
        form = LocationQuickAddForm({"name": "m", "priority": 3, "when": "",
                                     "due_date": "2026-11-01T10:00"})
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["due_date"])

    def test_mission_created_at_a_location_appears_there(self):
        for key in LOCATIONS:
            with self.subTest(location=key):
                url = reverse("deploy-location", args=[key])
                self.client.post(url, {"name": f"m-{key}", "priority": 3, "when": ""})
                task = Task.objects.get(name=f"m-{key}")
                self.assertIn(task, missions_at(self.user, key))


class UrgencyTests(SimpleTestCase):
    def bucket(self, **kwargs):
        with timezone.override(PARIS):
            return bucket_for(Task(name="m", **kwargs), NOW)

    def test_buckets(self):
        cases = [
            (None, "unscheduled"),
            (NOW - timedelta(minutes=1), "overdue"),
            (NOW + timedelta(hours=3), "today"),
            (NOW + timedelta(days=1), "soon"),
            (NOW + timedelta(days=5), "later"),
            (datetime(2026, 10, 19, 0, 30, tzinfo=PARIS), "soon"),  # just after midnight: tomorrow
        ]
        for due, expected in cases:
            with self.subTest(due=due):
                self.assertEqual(self.bucket(due_date=due), expected)

    def test_due_chores_count_as_overdue_even_without_date(self):
        task = Task(name="m", type="chores")
        task.has_due_chores = True
        self.assertEqual(bucket_for(task, NOW), "overdue")

    def test_empty_groups_are_dropped_and_order_is_kept(self):
        tasks = [Task(name="later", due_date=NOW + timedelta(days=5)),
                 Task(name="late", due_date=NOW - timedelta(days=1))]
        keys = [key for key, _, _ in group_by_urgency(tasks, NOW)]
        self.assertEqual(keys, ["overdue", "later"])
