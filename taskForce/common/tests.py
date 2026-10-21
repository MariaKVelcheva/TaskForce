from django.test import SimpleTestCase

from taskForce.common.deploy_map import map_rows, TERRAIN, BUILDINGS, building_positions
from taskForce.tasks.locations import LOCATIONS


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