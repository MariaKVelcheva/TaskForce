from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from taskForce.accounts.tests import NOW, PARIS
from taskForce.common.deploy_map import map_rows, TERRAIN, BUILDINGS, building_positions, find_path
from taskForce.tasks.locations import LOCATIONS, location_previews, next_objective
from taskForce.tasks.models import Task


User = get_user_model()


class DeployMapTests(SimpleTestCase):
    def test_all_rows_same_length(self):
        widths = {len(line) for line in map_rows()}
        self.assertEqual(len(widths), 1, f"row widths: {widths}")

    def test_only_known_characters(self):
        known = set(TERRAIN) | set(BUILDINGS)
        used = set("".join(map_rows()))
        self.assertEqual(used - known, set())

    def test_each_building_appears_exactly_once(self):
        text = "".join(map_rows())
        for char in BUILDINGS:
            with self.subTest(building=char):
                self.assertEqual(text.count(char), 1)

    def test_every_location_has_a_building(self):
        self.assertEqual(set(building_positions()), set(LOCATIONS))

    def test_every_building_reachable_from_hq(self):
        positions = building_positions()
        for key, pos in positions.items():
            with self.subTest(building=key):
                self.assertTrue(find_path(positions["hq"], pos))

    def test_paths_only_cross_roads(self):
        rows = map_rows()
        positions = building_positions()
        for key, pos in positions.items():
            path = find_path(positions["hq"], pos)
            for col, row in path[1:-1]:
                with self.subTest(building=key, tile=(col, row)):
                    self.assertEqual(rows[row][col], "=")


class DeployIndexViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("operative", password="x")
        cls.other = User.objects.create_user("stranger", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def test_query_count(self):
        with self.assertNumQueries(7):
            self.client.get(reverse("deploy"))

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("deploy"))
        self.assertEqual(response.status_code, 302)

    def test_every_location_links_from_the_map(self):
        response = self.client.get(reverse("deploy"))
        for key in LOCATIONS:
            with self.subTest(location=key):
                self.assertContains(response, reverse("deploy-location", args=[key]))

    def test_other_users_missions_not_counted(self):
        Task.objects.create(user=self.other, name="secret", type="workout")
        response = self.client.get(reverse("deploy"))
        training = next(b for b in response.context["buildings"] if b["key"] == "training")
        self.assertEqual(training["count"], 0)

    def test_unknown_location_is_404(self):
        response = self.client.get(reverse("deploy-location", args=["nowhere"]))
        self.assertEqual(response.status_code, 404)


