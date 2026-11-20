from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from taskForce.accounts.tests import PASSWORD
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
            user=self.commander, unit=self.unit, role=Membership.Role.COMMANDER
        )
        self.op_membership = Membership.objects.create(
            user=self.operative, unit=self.unit, role=Membership.Role.OPERATIVE
        )

    def test_unit_cannot_have_two_commanders(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.filter(pk=self.op_membership.pk).update(
                    role=Membership.Role.COMMANDER,
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

    def test_operative_can_leave(self):
        self.client.force_login(self.operative)
        self.client.post(reverse("leave-unit", kwargs={"pk": self.unit.pk}))

        self.assertFalse(
            Membership.objects.filter(pk=self.op_membership.pk).exists()
        )


class LeaveUnitTests(TestCase):
    def setUp(self):
        self.cmd = User.objects.create_user(username="cmd", password=PASSWORD)
        self.op = User.objects.create_user(username="op", password=PASSWORD)
        create_personal_unit(self.cmd)
        create_personal_unit(self.op)
        self.family = create_unit(name="Family", commander=self.cmd)
        Membership.objects.create(user=self.op, unit=self.family, role=Membership.Role.OPERATIVE)

    def leave(self, user, unit):
        self.client.force_login(user)
        return self.client.post(reverse("leave-unit", kwargs={"pk": unit.pk}))

    def test_operative_can_leave(self):
        response = self.leave(self.op, self.family)

        self.assertRedirects(response, reverse("all-units"))
        self.assertFalse(self.family.memberships.filter(user=self.op).exists())

    def test_commander_is_redirected_with_a_message(self):
        response = self.leave(self.cmd, self.family)

        self.assertRedirects(response, reverse("details-unit", kwargs={"pk": self.family.pk}))
        self.assertTrue(self.family.memberships.filter(user=self.cmd).exists())

    def test_last_member_is_told_to_delete(self):
        solo = create_unit(name="Solo", commander=self.cmd)

        response = self.leave(self.cmd, solo)

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("You are the last member. Delete the unit instead.", messages)

    def test_cannot_leave_personal_unit(self):
        response = self.leave(self.op, self.op.personal_unit)

        self.assertEqual(response.status_code, 404)


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
        self.assertTrue(unit.memberships.filter(user=user, role=Membership.Role.COMMANDER).exists())
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


class InviteCodeTests(TestCase):
    def setUp(self):
        self.cmd = User.objects.create_user(username="cmd", password=PASSWORD)
        self.op = User.objects.create_user(username="op", password=PASSWORD)
        create_personal_unit(self.cmd)
        create_personal_unit(self.op)
        self.family = create_unit(name="Family", commander=self.cmd)
        self.op_membership = Membership.objects.create(
            user=self.op, unit=self.family, role=Membership.Role.OPERATIVE,
        )
        self.old_code = self.family.invite_code

    def post_as(self, user, name, data=None, **kwargs):
        self.client.force_login(user)
        return self.client.post(reverse(name, kwargs=kwargs), data or {})

    def test_commander_can_reset_code(self):
        self.post_as(self.cmd, "reset-invite-code", pk=self.family.pk)

        self.family.refresh_from_db()
        self.assertNotEqual(self.family.invite_code, self.old_code)

    def test_operative_cannot_reset_code(self):
        response = self.post_as(self.op, "reset-invite-code", pk=self.family.pk)

        self.assertEqual(response.status_code, 404)
        self.family.refresh_from_db()
        self.assertEqual(self.family.invite_code, self.old_code)

    def test_cannot_reset_personal_unit_code(self):
        response = self.post_as(self.cmd, "reset-invite-code", pk=self.cmd.personal_unit.pk)

        self.assertEqual(response.status_code, 404)

    def test_remove_with_reset_changes_code(self):
        self.post_as(
            self.cmd, "remove-member", {"reset_code": "on"},
            pk=self.family.pk, membership_pk=self.op_membership.pk,
        )

        self.family.refresh_from_db()
        self.assertFalse(self.family.memberships.filter(user=self.op).exists())
        self.assertNotEqual(self.family.invite_code, self.old_code)

    def test_remove_without_reset_keeps_code(self):
        self.post_as(
            self.cmd, "remove-member",
            pk=self.family.pk, membership_pk=self.op_membership.pk,
        )

        self.family.refresh_from_db()
        self.assertFalse(self.family.memberships.filter(user=self.op).exists())
        self.assertEqual(self.family.invite_code, self.old_code)