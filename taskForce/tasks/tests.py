from django.contrib.auth import get_user_model
from django.test import TestCase

from taskForce.tasks.models import Task
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