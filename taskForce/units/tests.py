from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from taskForce.tasks.models import TaskType
from taskForce.units.services import create_personal_unit, create_unit
from taskForce.units.models import Unit, Membership

User = get_user_model()


class UnitCommandTests(TestCase):
    def setUp(self):
        self.commander = User.objects.create_user(username="cmd", password="x")
        self.operative = User.objects.create_user(username="op", password="x")

        self.unit = Unit.objects.create(name="Alpha")
        self.cmd_membership = Membership.objects.create(
            user=self.commander, unit=self.unit, role="commander"
        )
        self.op_membership = Membership.objects.create(
            user=self.operative, unit=self.unit, role="operative"
        )

    def test_unit_cannot_have_two_commanders(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.filter(pk=self.op_membership.pk).update(
                    role="commander"
                )

    def test_transfer_command_swaps_roles(self):
        self.client.force_login(self.commander)
        self.client.post(
            reverse("transfer-command", kwargs={
                "pk": self.unit.pk, "membership_pk": self.op_membership.pk
            })
        )

        self.cmd_membership.refresh_from_db()
        self.op_membership.refresh_from_db()
        self.assertEqual(self.cmd_membership.role, "operative")
        self.assertEqual(self.op_membership.role, "commander")

    def test_operative_cannot_transfer_command(self):
        self.client.force_login(self.operative)
        response = self.client.post(
            reverse("transfer-command", kwargs={
                "pk": self.unit.pk, "membership_pk": self.op_membership.pk
            })
        )

        self.assertEqual(response.status_code, 404)
        self.op_membership.refresh_from_db()
        self.assertEqual(self.op_membership.role, "operative")

    def test_commander_cannot_leave(self):
        self.client.force_login(self.commander)
        response = self.client.post(
            reverse("leave-unit", kwargs={"pk": self.unit.pk})
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Membership.objects.filter(pk=self.cmd_membership.pk).exists()
        )

    def test_operative_can_leave(self):
        self.client.force_login(self.operative)
        self.client.post(reverse("leave-unit", kwargs={"pk": self.unit.pk}))

        self.assertFalse(
            Membership.objects.filter(pk=self.op_membership.pk).exists()
        )


class PersonalUnitTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="x")
        self.unit = create_personal_unit(self.owner)
        self.stranger = User.objects.create_user(username="stranger", password="x")
        create_personal_unit(self.stranger)

    def test_personal_unit_cannot_be_deleted(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("delete-unit", kwargs={"pk": self.unit.pk}))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Unit.objects.filter(pk=self.unit.pk).exists())

    def test_personal_unit_cannot_be_joined(self):
        self.client.force_login(self.stranger)
        self.client.post(reverse("join-unit"), {"invite_code": self.unit.invite_code})

        self.assertFalse(
            Membership.objects.filter(user=self.stranger, unit=self.unit).exists()
        )


class CreateUnitViewTests(TestCase):
    def test_creates_group_unit_with_commander_singletons_and_switches_to_it(self):
        user = User.objects.create_user(username="cmd", password="x")
        create_personal_unit(user)
        self.client.force_login(user)

        self.client.post(reverse("create-unit"), {"name": "Family"})

        unit = Unit.objects.get(name="Family")
        self.assertIsNone(unit.personal_for)
        self.assertTrue(unit.memberships.filter(user=user, role="commander").exists())
        self.assertEqual(
            set(unit.tasks.values_list("type", flat=True)),
            {TaskType.GROCERIES, TaskType.PANTRY, TaskType.CHORES},
        )
        user.avatar.refresh_from_db()
        self.assertEqual(user.avatar.active_unit, unit)


class SwitchUnitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op", password="x")
        self.stranger = User.objects.create_user(username="stranger", password="x")
        create_personal_unit(self.user)
        create_personal_unit(self.stranger)
        self.family = create_unit(name="Family", commander=self.user)
        self.client.force_login(self.user)

    def test_switch_to_own_unit(self):
        self.client.post(reverse("switch-unit", args=[self.family.pk]))
        self.user.avatar.refresh_from_db()
        self.assertEqual(self.user.avatar.active_unit, self.family)

    def test_cannot_switch_to_a_unit_you_are_not_in(self):
        other = create_unit(name="Elsewhere", commander=self.stranger)
        response = self.client.post(reverse("switch-unit", args=[other.pk]))
        self.assertEqual(response.status_code, 404)
        self.user.avatar.refresh_from_db()
        self.assertNotEqual(self.user.avatar.active_unit, other)


