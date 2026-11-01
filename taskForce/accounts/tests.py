from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from taskForce.tasks.models import TaskType
from taskForce.units.models import Membership, Unit
from taskForce.units.services import create_personal_unit, create_unit

User = get_user_model()
PASSWORD = "Str0ng-pass!"


class RegisterTests(TestCase):
    def register(self, username="newbie", next_url=None):
        url = reverse("register")
        if next_url:
            url += "?" + urlencode({"next": next_url})
        return self.client.post(url, {
            "username": username,
            "email": f"{username}@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })

    def test_register_creates_personal_unit_with_four_singletons(self):
        self.register()
        user = User.objects.get(username="newbie")

        self.assertEqual(
            set(user.personal_unit.tasks.values_list("type", flat=True)),
            {TaskType.GROCERIES, TaskType.PANTRY, TaskType.CHORES, TaskType.WORKOUT},
        )

    def test_register_logs_user_in(self):
        self.register()
        user = User.objects.get(username="newbie")

        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_safe_next_is_followed(self):
        response = self.register(next_url="/units/")
        self.assertRedirects(response, "/units/", fetch_redirect_response=False)

    def test_unsafe_next_is_ignored(self):
        attacks = ["//evil.com", "/\\evil.com", "https://evil.com", "javascript:alert(1)"]
        for i, bad in enumerate(attacks):
            with self.subTest(next=bad):
                self.client.logout()
                response = self.register(username=f"user{i}", next_url=bad)
                self.assertRedirects(response, reverse("index"), fetch_redirect_response=False)


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.cmd = User.objects.create_user(username="cmd", password=PASSWORD)
        self.op = User.objects.create_user(username="op", password=PASSWORD)
        create_personal_unit(self.cmd)
        create_personal_unit(self.op)
        self.family = create_unit(name="Family", commander=self.cmd)
        Membership.objects.create(user=self.op, unit=self.family, role="operative")

    def delete_account(self, user):
        self.client.force_login(user)
        return self.client.post(reverse("delete-user"))

    def test_commander_of_populated_unit_cannot_delete_account(self):
        self.delete_account(self.cmd)

        self.assertTrue(User.objects.filter(pk=self.cmd.pk).exists())

    def test_deleting_account_removes_personal_unit(self):
        unit_pk = self.op.personal_unit.pk
        self.delete_account(self.op)

        self.assertFalse(User.objects.filter(pk=self.op.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=unit_pk).exists())

    def test_family_unit_survives_its_creators_deletion(self):
        Membership.objects.filter(unit=self.family).update(role="operative")
        Membership.objects.filter(unit=self.family, user=self.op).update(role="commander")

        self.delete_account(self.cmd)

        self.assertFalse(User.objects.filter(pk=self.cmd.pk).exists())
        self.assertTrue(Unit.objects.filter(pk=self.family.pk).exists())