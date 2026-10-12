from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

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