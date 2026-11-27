import re
from urllib.parse import urlencode, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
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


class UpdateProfileTests(TestCase):
    def test_saving_time_zone_redirects_to_profile(self):
        user = User.objects.create_user(username="tz", password=PASSWORD)
        create_personal_unit(user)
        self.client.force_login(user)

        response = self.client.post(reverse("update-profile"), {"time_zone": "Europe/Paris"})

        self.assertRedirects(response, reverse("details-profile"))
        user.avatar.refresh_from_db()
        self.assertEqual(user.avatar.time_zone, "Europe/Paris")


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.cmd = User.objects.create_user(username="cmd", password=PASSWORD)
        self.op = User.objects.create_user(username="op", password=PASSWORD)
        self.solo = User.objects.create_user(username="solo", password=PASSWORD)
        create_personal_unit(self.cmd)
        create_personal_unit(self.op)
        create_personal_unit(self.solo)
        self.family = create_unit(name="Family", commander=self.cmd)
        Membership.objects.create(user=self.op, unit=self.family, role=Membership.Role.OPERATIVE)

    def delete_account(self, user):
        self.client.force_login(user)
        return self.client.post(reverse("delete-user"))

    def test_commander_of_populated_unit_cannot_delete_account(self):
        self.delete_account(self.cmd)
        self.assertTrue(User.objects.filter(pk=self.cmd.pk).exists())

    def test_delete_refuses_get(self):
        self.client.force_login(self.solo)

        self.assertEqual(self.client.get(reverse("delete-user")).status_code, 405)

    def test_profile_lists_blocking_units_without_delete_button(self):
        self.client.force_login(self.cmd)
        response = self.client.get(reverse("details-profile"))

        self.assertContains(response, reverse("unit-settings", kwargs={"pk": self.family.pk}))
        self.assertNotContains(response, 'id="delete-account"')

    def test_profile_dialog_lists_solo_units(self):
        create_unit(name="Solo squad", commander=self.solo)
        self.client.force_login(self.solo)
        response = self.client.get(reverse("details-profile"))

        self.assertContains(response, 'id="delete-account"')
        self.assertContains(response, "Solo squad")

    def test_blocked_deletion_keeps_user_logged_in(self):
        response = self.delete_account(self.cmd)

        self.assertRedirects(response, reverse("details-profile"))
        self.assertEqual(self.client.get(reverse("all-units")).status_code, 200)

    def test_deleting_account_removes_personal_unit(self):
        unit_pk = self.op.personal_unit.pk
        self.delete_account(self.op)

        self.assertFalse(User.objects.filter(pk=self.op.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=unit_pk).exists())

    def test_family_unit_survives_its_creators_deletion(self):
        Membership.objects.filter(unit=self.family).update(role=Membership.Role.OPERATIVE)
        Membership.objects.filter(unit=self.family, user=self.op).update(role=Membership.Role.COMMANDER)

        self.delete_account(self.cmd)

        self.assertFalse(User.objects.filter(pk=self.cmd.pk).exists())
        self.assertTrue(Unit.objects.filter(pk=self.family.pk).exists())

    def test_solo_unit_is_deleted_with_user(self):
        unit = create_unit(name="Solo", commander=self.solo)

        self.delete_account(self.solo)

        self.assertFalse(User.objects.filter(pk=self.solo.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=unit.pk).exists())


class PasswordTests(TestCase):
    OLD = "Old-pass-123!"
    NEW = "New-pass-456!"

    def setUp(self):
        self.user = User.objects.create_user("operative", email="op@example.com", password=self.OLD)
        create_personal_unit(self.user)

    def change(self, old=OLD):
        return self.client.post(reverse("password-change"), {
            "old_password": old, "new_password1": self.NEW, "new_password2": self.NEW,
        })

    def reset_link(self, email="op@example.com"):
        self.client.post(reverse("password-reset"), {"email": email})
        self.assertEqual(len(mail.outbox), 1)
        return re.search(r"https?://\S+", mail.outbox[0].body).group()

    def test_change_needs_login(self):
        response = self.client.get(reverse("password-change"))
        self.assertEqual(response.status_code, 302)

    def test_change_keeps_you_logged_in(self):
        self.client.force_login(self.user)
        response = self.change()
        self.assertRedirects(response, reverse("details-profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))

    def test_change_refuses_a_wrong_old_password(self):
        self.client.force_login(self.user)
        self.change(old="nope")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.OLD))

    def open_reset_link(self, link):
        response = self.client.get(urlparse(link).path)
        self.assertEqual(response.status_code, 302, "the reset link did not redirect")
        return response["Location"]

    def set_new_password(self, url):
        return self.client.post(url, {"new_password1": self.NEW, "new_password2": self.NEW})

    def test_reset_link_sets_a_new_password(self):
        url = self.open_reset_link(self.reset_link(email="OP@example.com"))
        self.set_new_password(url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW))

    def test_reset_link_works_only_once(self):
        link = self.reset_link()
        self.set_new_password(self.open_reset_link(link))
        response = self.client.get(urlparse(link).path)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])

    def test_unknown_email_sends_nothing_and_looks_the_same(self):
        response = self.client.post(reverse("password-reset"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("password-reset-done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_login_page_links_to_reset(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password-reset"))

