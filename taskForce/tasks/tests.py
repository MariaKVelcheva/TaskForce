from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from taskForce.tasks.forms import CreateTaskForm, LocationQuickAddForm, UpdateTaskForm
from taskForce.tasks.items import item_progress
from taskForce.tasks.locations import (
    LOCATIONS, location_previews, location_summary, missions_at, next_objective,
)
from taskForce.tasks.models import (
    ChoreItem, GroceryItem, ListItem, PantryItem, Task, TaskType, WorkoutItem,
)
from taskForce.tasks.urgency import bucket_for, group_by_urgency, urgency_key
from taskForce.units.models import Membership
from taskForce.units.services import create_personal_unit, create_unit

User = get_user_model()
PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=PARIS)


class TaskTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("operative", password="x")
        cls.unit = create_personal_unit(cls.user)

    def make(self, **kwargs):
        kwargs.setdefault("user", self.user)
        kwargs.setdefault("unit", self.unit)
        kwargs.setdefault("name", "mission")
        return Task.objects.create(**kwargs)

    def singleton(self, task_type, unit=None):
        return (unit or self.unit).tasks.get(type=task_type)

    def points(self, user):
        user.avatar.refresh_from_db()
        return user.avatar.points


class LocationTestCase(TaskTestCase):
    def at(self, key):
        with timezone.override(PARIS):
            return set(missions_at(self.unit, key, now=NOW))

    def summary(self, unit=None):
        with timezone.override(PARIS):
            return location_summary(unit or self.unit, now=NOW)

    def previews(self):
        with timezone.override(PARIS):
            return location_previews(self.unit, now=NOW)


class HqLocationTests(LocationTestCase):
    def test_standing_orders_are_at_hq(self):
        a = self.make(type=TaskType.ONEOFF)
        b = self.make(type=TaskType.ONEOFF, due_date=NOW)
        self.assertEqual(self.at("hq"), {a, b})

    def test_lists_and_singletons_never_at_hq(self):
        self.make(type=TaskType.LIST, due_date=NOW)
        self.assertEqual(self.at("hq"), set())

    def test_inactive_missions_not_at_hq(self):
        self.make(type=TaskType.ONEOFF, is_active=False)
        self.assertEqual(self.at("hq"), set())

    def test_other_units_missions_not_at_hq(self):
        stranger = User.objects.create_user("stranger", password="x")
        self.make(user=stranger, unit=create_personal_unit(stranger))
        self.assertEqual(self.at("hq"), set())


class LocationCoverageTests(LocationTestCase):
    def test_every_active_mission_is_in_exactly_one_location(self):
        for mission_type in (TaskType.ONEOFF, TaskType.LIST):
            for due in (None, NOW):
                self.make(type=mission_type, due_date=due)

        missions = list(Task.objects.filter(unit=self.unit, is_active=True))
        self.assertEqual({m.type for m in missions}, set(TaskType.values))

        placements = {key: self.at(key) for key in LOCATIONS}
        for mission in missions:
            found = [key for key, placed in placements.items() if mission in placed]
            with self.subTest(type=mission.type, due=mission.due_date):
                self.assertEqual(len(found), 1, f"found in {found}")

    def test_inactive_missions_are_in_no_location(self):
        mission = self.make(type=TaskType.ONEOFF, is_active=False)
        for key in LOCATIONS:
            with self.subTest(location=key):
                self.assertNotIn(mission, self.at(key))

    def test_only_creatable_types_can_be_created_at_a_location(self):
        for key, location in LOCATIONS.items():
            with self.subTest(location=key):
                self.assertIn(location["creates"], (None, TaskType.ONEOFF, TaskType.LIST))


class LocationSummaryTests(LocationTestCase):
    def test_counts_active_missions_per_location(self):
        self.make()
        self.make()
        self.make(is_active=False)
        s = self.summary()
        self.assertEqual(s["hq"]["count"], 2)
        self.assertEqual(s["supply"]["count"], 2)
        self.assertEqual(s["training"]["count"], 1)

    def test_overdue_mission_flags_only_its_location(self):
        self.make(due_date=NOW - timedelta(days=1))
        s = self.summary()
        self.assertTrue(s["hq"]["overdue"])
        self.assertFalse(s["rec_room"]["overdue"])

    def test_due_chore_flags_barracks(self):
        ChoreItem.objects.create(
            task=self.singleton(TaskType.CHORES), name="sweep",
            frequency_days=1, last_done_at=NOW - timedelta(days=30),
        )
        self.assertTrue(self.summary()["barracks"]["overdue"])

    def test_chore_done_recently_does_not_flag_barracks(self):
        ChoreItem.objects.create(
            task=self.singleton(TaskType.CHORES), name="sweep",
            frequency_days=7, last_done_at=NOW - timedelta(days=1),
        )
        self.assertFalse(self.summary()["barracks"]["overdue"])

    def test_low_stock_flags_supply(self):
        PantryItem.objects.create(
            task=self.singleton(TaskType.PANTRY), name="milk", quantity=1, threshold=2,
        )
        self.assertTrue(self.summary()["supply"]["overdue"])

    def test_stock_without_threshold_never_flags(self):
        PantryItem.objects.create(task=self.singleton(TaskType.PANTRY), name="salt", quantity=0)
        self.assertFalse(self.summary()["supply"]["overdue"])

    def test_critical_flags_only_its_location(self):
        self.make(priority=1)
        s = self.summary()
        self.assertTrue(s["hq"]["critical"])
        self.assertFalse(s["rec_room"]["critical"])

    def test_due_later_today_is_today_not_overdue(self):
        self.make(due_date=NOW + timedelta(hours=3))
        s = self.summary()["hq"]
        self.assertTrue(s["due_today"])
        self.assertFalse(s["overdue"])

    def test_just_after_midnight_paris_is_not_today(self):
        self.make(due_date=datetime(2026, 10, 19, 0, 30, tzinfo=PARIS))
        self.assertFalse(self.summary()["hq"]["due_today"])

    def test_counts_not_inflated_by_unit_members(self):
        mate = User.objects.create_user("mate", password="x")
        family = create_unit(name="Family", commander=self.user)
        Membership.objects.create(unit=family, user=mate, role="operative")
        self.make(unit=family)
        self.assertEqual(self.summary(family)["hq"]["count"], 1)


class PreviewAndObjectiveTests(LocationTestCase):
    def test_previews_keep_three_most_urgent(self):
        late = self.make(name="late", due_date=NOW - timedelta(days=1))
        for i in range(4):
            self.make(name=f"later-{i}", due_date=NOW + timedelta(days=5 + i))
        preview = self.previews()["hq"]
        self.assertEqual(len(preview), 3)
        self.assertEqual(preview[0], late)

    def test_critical_without_deadline_comes_first(self):
        self.make(name="dated", due_date=NOW + timedelta(days=5))
        critical = self.make(name="critical", priority=1)
        self.assertEqual(self.previews()["hq"][0], critical)

    def test_objective_prefers_action_required_over_today(self):
        self.make(due_date=NOW + timedelta(hours=2))
        ChoreItem.objects.create(
            task=self.singleton(TaskType.CHORES), name="sweep",
            frequency_days=1, last_done_at=NOW - timedelta(days=3),
        )
        self.assertEqual(next_objective(self.previews(), NOW), "barracks")

    def test_critical_mission_can_be_the_objective(self):
        self.make(name="critical", priority=1)
        self.assertEqual(next_objective(self.previews(), NOW), "hq")

    def test_no_objective_without_actionable_missions(self):
        self.make(due_date=NOW + timedelta(days=9))
        self.make(type=TaskType.LIST)
        self.assertIsNone(next_objective(self.previews(), NOW))


class UrgencyTests(SimpleTestCase):
    def bucket(self, task):
        with timezone.override(PARIS):
            return bucket_for(task, NOW)

    def test_buckets_by_due_date(self):
        cases = [
            (None, "unscheduled"),
            (NOW - timedelta(minutes=1), "overdue"),
            (NOW + timedelta(hours=3), "today"),
            (NOW + timedelta(days=1), "soon"),
            (NOW + timedelta(days=5), "later"),
            (datetime(2026, 10, 19, 0, 30, tzinfo=PARIS), "soon"),
        ]
        for due, expected in cases:
            with self.subTest(due=due):
                self.assertEqual(self.bucket(Task(name="m", due_date=due)), expected)

    def test_due_chores_require_action_without_a_date(self):
        task = Task(name="m", type=TaskType.CHORES)
        task.has_due_chores = True
        self.assertEqual(self.bucket(task), "overdue")

    def test_low_stock_requires_action(self):
        task = Task(name="m", type=TaskType.PANTRY)
        task.has_low_stock = True
        self.assertEqual(self.bucket(task), "overdue")

    def test_actionable_missions_sort_first(self):
        dated = Task(name="dated", due_date=NOW + timedelta(days=5))
        critical = Task(name="critical", priority=1)
        for task in (dated, critical):
            task.bucket = self.bucket(task)
        ranked = sorted([dated, critical], key=lambda t: urgency_key(t, NOW))
        self.assertEqual(ranked[0], critical)

    def test_empty_groups_are_dropped_and_order_is_kept(self):
        tasks = [Task(name="later", due_date=NOW + timedelta(days=5)),
                 Task(name="late", due_date=NOW - timedelta(days=1))]
        keys = [key for key, _label, _tasks in group_by_urgency(tasks, NOW)]
        self.assertEqual(keys, ["overdue", "later"])


class VisibilityTests(TaskTestCase):
    def test_unit_missions_visible_to_members_only(self):
        mate = User.objects.create_user("mate", password="x")
        outsider = User.objects.create_user("outsider", password="x")
        family = create_unit(name="Family", commander=self.user)
        Membership.objects.create(unit=family, user=mate, role="operative")
        task = self.make(unit=family)

        self.assertIn(task, Task.objects.visible_to(mate))
        self.assertNotIn(task, Task.objects.visible_to(outsider))

    def test_visible_missions_are_not_duplicated(self):
        task = self.make()
        self.assertEqual(list(Task.objects.visible_to(self.user)).count(task), 1)


class ConstraintTests(TaskTestCase):
    def assertRefused(self, action):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                action()

    def test_second_grocery_list_is_refused(self):
        self.assertRefused(lambda: self.make(type=TaskType.GROCERIES))

    def test_singleton_cannot_be_deactivated(self):
        grocery = self.singleton(TaskType.GROCERIES)
        self.assertRefused(lambda: Task.objects.filter(pk=grocery.pk).update(is_active=False))

    def test_due_date_refused_on_singletons(self):
        chores = self.singleton(TaskType.CHORES)
        self.assertRefused(lambda: Task.objects.filter(pk=chores.pk).update(due_date=NOW))

    def test_only_one_off_missions_can_be_accomplished(self):
        task = self.make(type=TaskType.LIST)
        self.assertRefused(lambda: Task.objects.filter(pk=task.pk).update(is_accomplished=True))


class ItemCheckTests(TaskTestCase):
    def setUp(self):
        self.mate = User.objects.create_user("mate", password="x")
        self.family = create_unit(name="Family", commander=self.user)
        Membership.objects.create(unit=self.family, user=self.mate, role="operative")
        self.item = ListItem.objects.create(
            task=self.make(type=TaskType.LIST, unit=self.family), name="entry",
        )

    def test_tick_awards_one_point_to_the_checker(self):
        self.assertTrue(self.item.tick(self.mate))
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_checked)
        self.assertEqual(self.item.checked_by, self.mate)
        self.assertEqual(self.points(self.mate), 1)

    def test_second_tick_awards_nothing(self):
        self.item.tick(self.mate)
        self.assertFalse(self.item.tick(self.user))
        self.assertEqual(self.points(self.mate), 1)
        self.assertEqual(self.points(self.user), 0)

    def test_untick_takes_the_point_from_the_earner(self):
        self.item.tick(self.mate)
        self.assertTrue(self.item.untick())
        self.assertEqual(self.points(self.mate), 0)
        self.assertEqual(self.points(self.user), 0)


class RecurringItemTests(TaskTestCase):
    def setUp(self):
        self.item = GroceryItem.objects.create(
            task=self.singleton(TaskType.GROCERIES), name="milk", frequency_days=7,
        )

    def test_never_bought_recurring_item_is_due(self):
        self.assertTrue(self.item.is_due_now)
        self.assertFalse(self.item.is_done)

    def test_tick_hides_it_and_awards_a_point(self):
        self.assertTrue(self.item.tick(self.user))
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_done)
        self.assertFalse(self.item.is_checked)
        self.assertEqual(self.points(self.user), 1)

    def test_cannot_tick_before_it_is_due_again(self):
        self.item.tick(self.user)
        self.item.refresh_from_db()
        self.assertFalse(self.item.tick(self.user))
        self.assertEqual(self.points(self.user), 1)

    def test_untick_restores_previous_state_once(self):
        self.item.tick(self.user)
        self.item.refresh_from_db()
        self.assertTrue(self.item.untick())
        self.item.refresh_from_db()
        self.assertIsNone(self.item.last_done_at)
        self.assertEqual(self.points(self.user), 0)
        self.assertFalse(self.item.untick())

    def test_need_now_makes_it_due_and_keeps_the_point(self):
        self.item.tick(self.user)
        self.item.need_now()
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_due_now)
        self.assertEqual(self.points(self.user), 1)


class AccomplishTests(TaskTestCase):
    def test_accomplish_deactivates_and_awards_a_point(self):
        task = self.make()
        self.assertTrue(task.accomplish(self.user))
        task.refresh_from_db()
        self.assertTrue(task.is_accomplished)
        self.assertFalse(task.is_active)
        self.assertEqual(task.accomplished_by, self.user)
        self.assertEqual(self.points(self.user), 1)

    def test_cannot_accomplish_twice(self):
        task = self.make()
        task.accomplish(self.user)
        self.assertFalse(task.accomplish(self.user))
        self.assertEqual(self.points(self.user), 1)

    def test_lists_cannot_be_accomplished(self):
        self.assertFalse(self.make(type=TaskType.LIST).accomplish(self.user))
        self.assertEqual(self.points(self.user), 0)

    def test_unaccomplish_reactivates_and_takes_the_point(self):
        task = self.make()
        task.accomplish(self.user)
        self.assertTrue(task.unaccomplish())
        task.refresh_from_db()
        self.assertFalse(task.is_accomplished)
        self.assertTrue(task.is_active)
        self.assertEqual(self.points(self.user), 0)


class ItemProgressTests(TaskTestCase):
    def annotated(self, task):
        return Task.objects.annotate(**item_progress(now=NOW)).get(pk=task.pk)

    def test_counts_checked_items(self):
        task = self.singleton(TaskType.WORKOUT)
        WorkoutItem.objects.create(task=task, name="a", is_checked=True, checked_by=self.user)
        WorkoutItem.objects.create(task=task, name="b")
        WorkoutItem.objects.create(task=task, name="c")
        result = self.annotated(task)
        self.assertEqual((result.items_done, result.items_total), (1, 3))

    def test_recurring_item_done_until_due_again(self):
        task = self.singleton(TaskType.GROCERIES)
        GroceryItem.objects.create(
            task=task, name="milk", frequency_days=7, last_done_at=NOW - timedelta(days=1),
        )
        GroceryItem.objects.create(task=task, name="eggs", frequency_days=7)
        result = self.annotated(task)
        self.assertEqual((result.items_done, result.items_total), (1, 2))

    def test_mission_without_items_counts_zero(self):
        result = self.annotated(self.singleton(TaskType.WORKOUT))
        self.assertEqual((result.items_done, result.items_total), (0, 0))

    def test_low_stock_is_counted(self):
        pantry = self.singleton(TaskType.PANTRY)
        PantryItem.objects.create(task=pantry, name="milk", quantity=0, threshold=1)
        PantryItem.objects.create(task=pantry, name="rice", quantity=5, threshold=1)
        self.assertEqual(self.annotated(pantry).stock_low, 1)


class TaskFormTests(TaskTestCase):
    def test_create_form_offers_only_creatable_types(self):
        form = CreateTaskForm(user=self.user)
        offered = {value for value, _label in form.fields["type"].choices}
        self.assertEqual(offered, {TaskType.ONEOFF, TaskType.LIST})

    def test_update_form_hides_due_date_on_singletons(self):
        form = UpdateTaskForm(instance=self.singleton(TaskType.GROCERIES), user=self.user)
        self.assertNotIn("due_date", form.fields)

    def test_update_form_keeps_due_date_on_one_offs(self):
        form = UpdateTaskForm(instance=self.make(), user=self.user)
        self.assertIn("due_date", form.fields)

    def test_update_form_cannot_change_type(self):
        form = UpdateTaskForm(instance=self.make(), user=self.user)
        self.assertNotIn("type", form.fields)


class QuickAddFormTests(SimpleTestCase):
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


class TaskViewTests(TaskTestCase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_back_link_follows_next(self):
        url = reverse("details-task", args=[self.make().pk])
        response = self.client.get(url, {"next": "/deploy/barracks/"})
        self.assertEqual(response.context["back_url"], "/deploy/barracks/")

    def test_unsafe_next_is_ignored(self):
        url = reverse("details-task", args=[self.make().pk])
        response = self.client.get(url, {"next": "https://evil.example/"})
        self.assertEqual(response.context["back_url"], reverse("all-tasks"))

    def test_standing_order_shows_accomplish_button(self):
        task = self.make()
        response = self.client.get(reverse("details-task", args=[task.pk]))
        self.assertContains(response, reverse("accomplish-task", args=[task.pk]))

    def test_delete_returns_to_next(self):
        url = reverse("delete-task", args=[self.make().pk])
        response = self.client.post(url, {"next": "/deploy/barracks/"})
        self.assertRedirects(response, "/deploy/barracks/", fetch_redirect_response=False)

    def test_singletons_cannot_be_deleted(self):
        grocery = self.singleton(TaskType.GROCERIES)
        response = self.client.post(reverse("delete-task", args=[grocery.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=grocery.pk).exists())

    def test_singletons_cannot_be_deactivated(self):
        grocery = self.singleton(TaskType.GROCERIES)
        response = self.client.post(reverse("deactivate-task", args=[grocery.pk]))
        self.assertEqual(response.status_code, 404)

    def test_toggle_without_javascript_redirects_and_awards_a_point(self):
        task = self.make(type=TaskType.LIST)
        item = ListItem.objects.create(task=task, name="entry")
        response = self.client.post(reverse("toggle-item", args=[task.pk, item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.points(self.user), 1)

    def test_pantry_items_cannot_be_toggled(self):
        pantry = self.singleton(TaskType.PANTRY)
        item = PantryItem.objects.create(task=pantry, name="milk")
        response = self.client.post(reverse("toggle-item", args=[pantry.pk, item.pk]))
        self.assertEqual(response.status_code, 404)

    def test_accomplished_mission_cannot_be_reactivated_by_hand(self):
        task = self.make()
        task.accomplish(self.user)
        response = self.client.post(reverse("reactivate-task", args=[task.pk]))
        self.assertEqual(response.status_code, 404)


    def test_stock_buttons_adjust_by_one(self):
        pantry = self.singleton(TaskType.PANTRY)
        rice = PantryItem.objects.create(task=pantry, name="rice", quantity=3)
        url = reverse("adjust-stock", args=[pantry.pk, rice.pk])
        self.client.post(url, {"delta": "-1"})
        rice.refresh_from_db()
        self.assertEqual(rice.quantity, 2)

    def test_stock_rejects_other_amounts(self):
        pantry = self.singleton(TaskType.PANTRY)
        rice = PantryItem.objects.create(task=pantry, name="rice", quantity=3)
        response = self.client.post(reverse("adjust-stock", args=[pantry.pk, rice.pk]), {"delta": "-50"})
        self.assertEqual(response.status_code, 400)
        rice.refresh_from_db()
        self.assertEqual(rice.quantity, 3)

    def test_amount_can_be_edited_on_linked_items(self):
        pantry = self.singleton(TaskType.PANTRY)
        milk = PantryItem.objects.create(task=pantry, name="milk", quantity=0, threshold=1)
        item = GroceryItem.objects.get(pantry_item=milk)
        groceries = self.singleton(TaskType.GROCERIES)
        self.client.post(reverse("set-item-amount", args=[groceries.pk, item.pk]), {"amount": "6"})
        item.refresh_from_db()
        self.assertEqual(item.amount, 6)

    def test_clear_bought_removes_only_checked_items_and_keeps_points(self):
        groceries = self.singleton(TaskType.GROCERIES)
        bought = GroceryItem.objects.create(task=groceries, name="bread")
        bought.tick(self.user)
        pending = GroceryItem.objects.create(task=groceries, name="eggs")
        self.client.post(reverse("clear-bought", args=[groceries.pk]))
        self.assertFalse(GroceryItem.objects.filter(pk=bought.pk).exists())
        self.assertTrue(GroceryItem.objects.filter(pk=pending.pk).exists())
        self.assertEqual(self.points(self.user), 1)


class PantryLinkTests(TaskTestCase):
    def setUp(self):
        self.pantry = self.singleton(TaskType.PANTRY)
        self.groceries = self.singleton(TaskType.GROCERIES)

    def product(self, **kwargs):
        kwargs.setdefault("name", "milk")
        kwargs.setdefault("quantity", 3)
        kwargs.setdefault("threshold", 1)
        return PantryItem.objects.create(task=self.pantry, **kwargs)

    def on_list(self, product):
        return GroceryItem.objects.filter(pantry_item=product, is_checked=False).first()

    def test_crossing_into_low_puts_it_on_the_list(self):
        milk = self.product(quantity=2)
        self.assertIsNone(self.on_list(milk))
        milk.adjust(-1)
        item = self.on_list(milk)
        self.assertEqual((item.task, item.amount), (self.groceries, 1))

    def test_creating_a_low_product_puts_it_on_the_list(self):
        milk = self.product(quantity=0)
        self.assertEqual(self.on_list(milk).amount, 2)

    def test_deleted_list_item_stays_deleted_while_still_low(self):
        milk = self.product(quantity=1)
        GroceryItem.objects.filter(pantry_item=milk).delete()
        milk.adjust(-1)
        self.assertIsNone(self.on_list(milk))

    def test_buying_restocks_the_shelf_and_earns_a_point(self):
        milk = self.product(quantity=0)
        item = self.on_list(milk)
        item.tick(self.user)
        milk.refresh_from_db()
        self.assertEqual(milk.quantity, 2)
        self.assertEqual(self.points(self.user), 1)

    def test_running_low_again_reuses_the_bought_item_and_keeps_the_point(self):
        milk = self.product(quantity=0)
        self.on_list(milk).tick(self.user)
        milk.refresh_from_db()
        milk.adjust(-2)
        self.assertEqual(GroceryItem.objects.filter(pantry_item=milk).count(), 1)
        self.assertIsNotNone(self.on_list(milk))
        self.assertEqual(self.points(self.user), 1)

    def test_untick_takes_stock_back_but_not_below_zero(self):
        milk = self.product(quantity=0)
        item = self.on_list(milk)
        item.tick(self.user)
        milk.refresh_from_db()
        milk.adjust(-2)
        item.refresh_from_db()
        item.untick()
        milk.refresh_from_db()
        self.assertEqual(milk.quantity, 0)

    def test_stock_never_goes_below_zero(self):
        milk = self.product(quantity=0, threshold=None)
        self.assertEqual(milk.adjust(-1).quantity, 0)

    def test_linked_item_cannot_be_recurring(self):
        milk = self.product(quantity=0)
        item = self.on_list(milk)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GroceryItem.objects.filter(pk=item.pk).update(frequency_days=7)


