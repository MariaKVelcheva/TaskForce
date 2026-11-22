from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from taskForce.budget.models import Spending
from taskForce.budget.services import can_delete_spending, log_spending, task_funds, Funds, unit_funds, month_range
from taskForce.tasks.models import Task, TaskType
from taskForce.units.models import Membership
from taskForce.units.services import create_personal_unit, create_unit

User = get_user_model()
PASSWORD = "pw12345!"
NOV = date(2026, 11, 15)


class SpendingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="kiara", password=PASSWORD)
        create_personal_unit(self.user)
        self.unit = create_unit(name="Family", commander=self.user)
        self.groceries = self.unit.tasks.get(type=TaskType.GROCERIES)

    def test_amount_must_be_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Spending.objects.create(unit=self.unit, amount=Decimal("0"), added_by=self.user)

    def test_unit_budget_must_be_positive(self):
        self.unit.monthly_budget = Decimal("-5")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.unit.save()

    def test_empty_budgets_are_allowed(self):
        self.unit.monthly_budget = None
        self.unit.save()
        self.groceries.monthly_budget = None
        self.groceries.save()

    def test_deleting_mission_keeps_spending_in_unit(self):
        spending = Spending.objects.create(
            unit=self.unit, task=self.groceries, amount=Decimal("30"), added_by=self.user,
        )
        self.groceries.delete()

        spending.refresh_from_db()
        self.assertIsNone(spending.task)
        self.assertEqual(spending.unit, self.unit)

    def test_deleting_unit_deletes_spending(self):
        Spending.objects.create(unit=self.unit, amount=Decimal("30"), added_by=self.user)
        self.unit.delete()

        self.assertFalse(Spending.objects.exists())

    def test_mission_from_another_unit_is_rejected(self):
        other_mission = self.user.personal_unit.tasks.get(type=TaskType.GROCERIES)
        spending = Spending(unit=self.unit, task=other_mission, amount=Decimal("10"), added_by=self.user)

        with self.assertRaises(ValidationError):
            spending.full_clean()


class MonthRangeTests(TestCase):
    def test_regular_month(self):
        self.assertEqual(month_range(NOV), (date(2026, 11, 1), date(2026, 12, 1)))

    def test_december_rolls_into_next_year(self):
        self.assertEqual(month_range(date(2026, 12, 31)), (date(2026, 12, 1), date(2027, 1, 1)))

    def test_february(self):
        self.assertEqual(month_range(date(2028, 2, 29)), (date(2028, 2, 1), date(2028, 3, 1)))


class FundsTests(TestCase):
    def test_under_budget(self):
        funds = Funds(spent=Decimal("1000"), budget=Decimal("12000"))

        self.assertFalse(funds.is_over)
        self.assertEqual(funds.remaining, Decimal("11000"))
        self.assertEqual(funds.overrun, Decimal("0"))

    def test_over_budget(self):
        funds = Funds(spent=Decimal("100000"), budget=Decimal("12000"))

        self.assertTrue(funds.is_over)
        self.assertEqual(funds.remaining, Decimal("0"))
        self.assertEqual(funds.overrun, Decimal("88000"))

    def test_exactly_on_budget_is_not_over(self):
        funds = Funds(spent=Decimal("500"), budget=Decimal("500"))

        self.assertFalse(funds.is_over)
        self.assertEqual(funds.remaining, Decimal("0"))

    def test_no_budget(self):
        funds = Funds(spent=Decimal("40"), budget=None)

        self.assertFalse(funds.has_budget)
        self.assertFalse(funds.is_over)
        self.assertIsNone(funds.remaining)


class BudgetServiceTests(TestCase):
    def setUp(self):
        self.cmd = User.objects.create_user(username="cmd", password=PASSWORD)
        self.op = User.objects.create_user(username="op", password=PASSWORD)
        create_personal_unit(self.cmd)
        create_personal_unit(self.op)
        self.unit = create_unit(name="Family", commander=self.cmd)
        Membership.objects.create(user=self.op, unit=self.unit, role=Membership.Role.OPERATIVE)
        self.unit.monthly_budget = Decimal("12000")
        self.unit.save()
        self.groceries = self.unit.tasks.get(type=TaskType.GROCERIES)
        self.chores = self.unit.tasks.get(type=TaskType.CHORES)

    def log(self, amount, task=None, day=NOV, user=None):
        return log_spending(
            amount=Decimal(amount), added_by=user or self.cmd,
            unit=self.unit, task=task, spent_on=day,
        )

    def test_unit_counts_mission_and_general_spending(self):
        self.log("300", task=self.groceries)
        self.log("700")

        self.assertEqual(unit_funds(self.unit, NOV).spent, Decimal("1000"))

    def test_other_months_are_ignored(self):
        self.log("100", day=date(2026, 10, 31))
        self.log("200", day=NOV)
        self.log("400", day=date(2026, 12, 1))

        self.assertEqual(unit_funds(self.unit, NOV).spent, Decimal("200"))

    def test_mission_with_budget_counts_only_its_own_spending(self):
        self.groceries.monthly_budget = Decimal("7000")
        self.groceries.save()
        self.log("300", task=self.groceries)
        self.log("700")

        funds = task_funds(self.groceries, NOV)

        self.assertEqual(funds, Funds(spent=Decimal("300"), budget=Decimal("7000")))

    def test_mission_without_budget_falls_back_to_unit(self):
        self.log("300", task=self.groceries)
        self.log("700")

        funds = task_funds(self.groceries, NOV)

        self.assertTrue(funds.is_unit_fallback)
        self.assertEqual(funds.spent, Decimal("1000"))
        self.assertEqual(funds.budget, Decimal("12000"))

    def test_log_takes_unit_from_mission(self):
        personal = self.cmd.personal_unit
        spending = log_spending(
            amount=Decimal("5"), added_by=self.cmd, unit=personal, task=self.groceries, spent_on=NOV,
        )

        self.assertEqual(spending.unit, self.unit)

    def test_log_rejects_zero(self):
        with self.assertRaises(ValidationError):
            self.log("0")
        self.assertFalse(Spending.objects.exists())

    def test_author_and_commander_can_delete(self):
        spending = self.log("20", user=self.op)

        self.assertTrue(can_delete_spending(spending, self.op))
        self.assertTrue(can_delete_spending(spending, self.cmd))

    def test_other_operative_cannot_delete(self):
        spending = self.log("20", user=self.cmd)

        self.assertFalse(can_delete_spending(spending, self.op))


class BudgetViewTests(TestCase):
    def setUp(self):
        self.cmd = User.objects.create_user(username="cmd", password=PASSWORD)
        self.op = User.objects.create_user(username="op", password=PASSWORD)
        self.outsider = User.objects.create_user(username="out", password=PASSWORD)
        for user in (self.cmd, self.op, self.outsider):
            create_personal_unit(user)
        self.unit = create_unit(name="Family", commander=self.cmd)
        Membership.objects.create(user=self.op, unit=self.unit, role=Membership.Role.OPERATIVE)
        self.groceries = self.unit.tasks.get(type=TaskType.GROCERIES)

    def post_as(self, user, name, data=None, **kwargs):
        self.client.force_login(user)
        return self.client.post(reverse(name, kwargs=kwargs), data or {})

    def test_log_on_unit(self):
        self.post_as(self.op, "unit-log-spending", {"amount": "12.50"}, unit_pk=self.unit.pk)

        spending = Spending.objects.get()
        self.assertEqual(spending.amount, Decimal("12.50"))
        self.assertIsNone(spending.task)
        self.assertEqual(spending.added_by, self.op)

    def test_log_on_mission_sets_mission_and_unit(self):
        self.post_as(self.op, "mission-log-spending", {"amount": "30"}, task_pk=self.groceries.pk)

        spending = Spending.objects.get()
        self.assertEqual(spending.task, self.groceries)
        self.assertEqual(spending.unit, self.unit)

    def test_invalid_amount_logs_nothing(self):
        self.post_as(self.op, "unit-log-spending", {"amount": "0"}, unit_pk=self.unit.pk)

        self.assertFalse(Spending.objects.exists())

    def test_outsider_gets_404(self):
        response = self.post_as(self.outsider, "unit-log-spending", {"amount": "5"}, unit_pk=self.unit.pk)

        self.assertEqual(response.status_code, 404)

    def test_log_refuses_get(self):
        self.client.force_login(self.op)
        response = self.client.get(reverse("unit-log-spending", kwargs={"unit_pk": self.unit.pk}))

        self.assertEqual(response.status_code, 405)

    def test_operative_can_set_and_clear_budget(self):
        self.post_as(self.op, "mission-set-budget", {"monthly_budget": "7000"}, task_pk=self.groceries.pk)
        self.groceries.refresh_from_db()
        self.assertEqual(self.groceries.monthly_budget, Decimal("7000"))

        self.post_as(self.op, "mission-set-budget", {"monthly_budget": ""}, task_pk=self.groceries.pk)
        self.groceries.refresh_from_db()
        self.assertIsNone(self.groceries.monthly_budget)

    def test_other_operative_cannot_delete(self):
        spending = log_spending(amount=Decimal("5"), added_by=self.cmd, unit=self.unit)

        response = self.post_as(self.op, "delete-spending", pk=spending.pk)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Spending.objects.exists())

    def test_commander_can_delete_others_entry(self):
        spending = log_spending(amount=Decimal("5"), added_by=self.op, unit=self.unit)

        self.post_as(self.cmd, "delete-spending", pk=spending.pk)

        self.assertFalse(Spending.objects.exists())

    def test_unit_page_shows_funds(self):
        self.unit.monthly_budget = Decimal("12000")
        self.unit.save()
        log_spending(amount=Decimal("1000"), added_by=self.cmd, unit=self.unit)
        self.client.force_login(self.op)

        response = self.client.get(reverse("details-unit", args=[self.unit.pk]))

        self.assertContains(response, "remaining")
        self.assertEqual(response.context["funds_panel"]["funds"].remaining, Decimal("11000"))

    def test_mission_page_falls_back_to_unit_funds(self):
        self.unit.monthly_budget = Decimal("12000")
        self.unit.save()
        log_spending(amount=Decimal("1000"), added_by=self.cmd, unit=self.unit)
        self.client.force_login(self.op)

        response = self.client.get(reverse("details-task", args=[self.groceries.pk]))

        funds = response.context["funds_panel"]["funds"]
        self.assertTrue(funds.is_unit_fallback)
        self.assertEqual(funds.spent, Decimal("1000"))
        self.assertContains(response, "Funds (unit)")

    def test_mission_page_uses_its_own_budget(self):
        self.groceries.monthly_budget = Decimal("7000")
        self.groceries.save()
        log_spending(amount=Decimal("300"), added_by=self.cmd, task=self.groceries)
        log_spending(amount=Decimal("700"), added_by=self.cmd, unit=self.unit)
        self.client.force_login(self.op)

        response = self.client.get(reverse("details-task", args=[self.groceries.pk]))

        funds = response.context["funds_panel"]["funds"]
        self.assertFalse(funds.is_unit_fallback)
        self.assertEqual(funds.spent, Decimal("300"))
        self.assertEqual(funds.budget, Decimal("7000"))


class MapFundsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="kiara", password=PASSWORD)
        create_personal_unit(self.user)
        self.base = self.user.personal_unit
        self.base.monthly_budget = Decimal("500")
        self.base.save()
        log_spending(amount=Decimal("120"), added_by=self.user, unit=self.base)
        self.client.force_login(self.user)

    def location(self, key):
        return self.client.get(reverse("deploy-location", args=[key]))

    def test_deploy_map_shows_unit_funds(self):
        response = self.client.get(reverse("deploy"))

        self.assertEqual(response.context["funds"].spent, Decimal("120"))
        self.assertContains(response, "Log spending")

    def test_supply_has_one_funds_panel_per_mission(self):
        response = self.location("supply")

        panels = response.context["panels"]
        self.assertEqual(len(panels), 2)
        anchors = {p["funds"]["anchor"] for p in panels}
        self.assertEqual(len(anchors), 2)
        for p in panels:
            self.assertContains(response, f'id="{p["funds"]["anchor"]}"')

    def test_barracks_has_funds_panel(self):
        response = self.location("barracks")

        self.assertTrue(response.context["funds_panel"]["funds"].is_unit_fallback)

    def test_supply_shows_funds_for_groceries_only(self):
        response = self.client.get(reverse("deploy-location", args=["supply"]))
        funds = {p["task"].type: p.get("funds") for p in response.context["panels"]}
        self.assertIsNotNone(funds[TaskType.GROCERIES])
        self.assertIsNone(funds[TaskType.PANTRY])

    def test_training_has_funds_panel(self):
        response = self.location("training")

        self.assertIn("funds_panel", response.context)