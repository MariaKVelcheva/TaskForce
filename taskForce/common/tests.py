from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from taskForce.common.grid_map import GridMap
from taskForce.common.house_map import BARRACKS, ENTRANCE
from taskForce.tasks.locations import LOCATIONS
from taskForce.tasks.models import ChoreItem, PantryItem, Task, TaskType
from taskForce.units.models import Membership
from taskForce.common.deploy_map import BASE
from taskForce.units.services import create_personal_unit, create_unit

User = get_user_model()

DEPLOY_QUERY_BUDGET = 12


class BaseMapTests(SimpleTestCase):
    def test_each_building_appears_exactly_once(self):
        text = "".join(BASE.rows)
        for char in BASE.places:
            with self.subTest(building=char):
                self.assertEqual(text.count(char), 1)

    def test_every_location_has_a_building(self):
        self.assertEqual(set(BASE.place_positions()), set(LOCATIONS))

    def test_every_building_reachable_from_hq(self):
        positions = BASE.place_positions()
        for key, pos in positions.items():
            with self.subTest(building=key):
                self.assertTrue(BASE.find_path(positions["hq"], pos))

    def test_paths_only_cross_roads(self):
        positions = BASE.place_positions()
        for key, pos in positions.items():
            path = BASE.find_path(positions["hq"], pos)
            for tile in path[1:-1]:
                with self.subTest(building=key, tile=tile):
                    self.assertEqual(BASE.char_at(tile), "=")


class CommonTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("operative", password="x")
        cls.mate = User.objects.create_user("mate", password="x")
        cls.stranger = User.objects.create_user("stranger", password="x")
        for user in (cls.user, cls.mate, cls.stranger):
            create_personal_unit(user)
        cls.family = create_unit(name="Family", commander=cls.user)
        Membership.objects.create(unit=cls.family, user=cls.mate, role="operative")

    def setUp(self):
        self.client.force_login(self.user)

    def make(self, **kwargs):
        kwargs.setdefault("user", self.user)
        kwargs.setdefault("unit", self.user.personal_unit)
        kwargs.setdefault("name", "mission")
        return Task.objects.create(**kwargs)

    def switch_to(self, unit):
        avatar = self.user.avatar
        avatar.active_unit = unit
        avatar.save(update_fields=["active_unit"])

    def building(self, response, key):
        return next(b for b in response.context["buildings"] if b["key"] == key)


class DeployIndexViewTests(CommonTestCase):
    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("deploy"))
        self.assertEqual(response.status_code, 302)

    def test_query_count(self):
        with self.assertNumQueries(DEPLOY_QUERY_BUDGET):
            self.client.get(reverse("deploy"))

    def test_every_location_links_from_the_personal_base(self):
        response = self.client.get(reverse("deploy"))
        for key in LOCATIONS:
            with self.subTest(location=key):
                self.assertContains(response, reverse("deploy-location", args=[key]))

    def test_defaults_to_the_personal_base(self):
        response = self.client.get(reverse("deploy"))
        self.assertEqual(response.context["unit"], self.user.personal_unit)

    def test_shows_only_the_active_units_missions(self):
        self.make(unit=self.family)

        response = self.client.get(reverse("deploy"))
        self.assertEqual(self.building(response, "hq")["count"], 0)

        self.switch_to(self.family)
        response = self.client.get(reverse("deploy"))
        self.assertEqual(self.building(response, "hq")["count"], 1)

    def test_falls_back_when_no_longer_a_member(self):
        outsider_unit = create_unit(name="Elsewhere", commander=self.stranger)
        self.switch_to(outsider_unit)
        response = self.client.get(reverse("deploy"))
        self.assertEqual(response.context["unit"], self.user.personal_unit)

    def test_other_users_missions_not_counted(self):
        self.make(user=self.stranger, unit=self.stranger.personal_unit)
        response = self.client.get(reverse("deploy"))
        self.assertEqual(self.building(response, "hq")["count"], 0)

    def test_training_is_off_limits_on_a_group_base(self):
        self.switch_to(self.family)
        response = self.client.get(reverse("deploy"))
        self.assertTrue(self.building(response, "training")["off_limits"])
        self.assertNotContains(response, reverse("deploy-location", args=["training"]))

    def test_training_is_open_on_the_personal_base(self):
        response = self.client.get(reverse("deploy"))
        self.assertFalse(self.building(response, "training")["off_limits"])


class DeployLocationViewTests(CommonTestCase):
    def post(self, key, **data):
        data.setdefault("priority", 3)
        data.setdefault("when", "")
        return self.client.post(reverse("deploy-location", args=[key]), data)

    def test_barracks_opens_the_chore_rota(self):
        chores = self.user.personal_unit.tasks.get(type=TaskType.CHORES)
        response = self.client.get(reverse("deploy-location", args=["barracks"]))
        self.assertTrue(response.url.startswith(reverse("details-task", args=[chores.pk])))

    def test_nav_groceries_opens_the_active_units_list(self):
        self.switch_to(self.family)
        grocery = self.family.tasks.get(type=TaskType.GROCERIES)
        response = self.client.get(reverse("deploy"))
        nav = {entry["value"]: entry for entry in response.context["type_nav"]}
        self.assertEqual(nav[TaskType.GROCERIES]["url"], reverse("details-task", args=[grocery.pk]))

    def test_unknown_location_is_404(self):
        response = self.client.get(reverse("deploy-location", args=["nowhere"]))
        self.assertEqual(response.status_code, 404)

    def test_hq_quick_add_creates_a_standing_order_in_the_active_unit(self):
        self.switch_to(self.family)
        self.post("hq", name="Call plumber")
        task = Task.objects.get(name="Call plumber")
        self.assertEqual((task.type, task.unit), (TaskType.ONEOFF, self.family))

    def test_rec_room_quick_add_creates_a_list_and_opens_it(self):
        response = self.post("rec_room", name="Watchlist")
        task = Task.objects.get(name="Watchlist")
        self.assertEqual(task.type, TaskType.LIST)
        self.assertTrue(response.url.startswith(reverse("details-task", args=[task.pk])))

    def test_mission_created_at_a_location_appears_there(self):
        for key, location in LOCATIONS.items():
            if location["creates"] is None:
                continue
            with self.subTest(location=key):
                self.post(key, name=f"m-{key}")
                response = self.client.get(reverse("deploy-location", args=[key]))
                self.assertIn(Task.objects.get(name=f"m-{key}"), response.context["missions"])

    def test_singleton_locations_refuse_quick_add(self):
        for key, location in LOCATIONS.items():
            if location["creates"] is not None:
                continue
            with self.subTest(location=key):
                response = self.post(key, name=f"m-{key}")
                self.assertEqual(response.status_code, 404)
                self.assertFalse(Task.objects.filter(name=f"m-{key}").exists())

    def test_lists_only_the_active_units_missions(self):
        mine = self.make(name="mine")
        self.make(name="family", unit=self.family)
        response = self.client.get(reverse("deploy-location", args=["hq"]))
        self.assertEqual(list(response.context["missions"]), [mine])

    def test_training_on_a_group_base_is_empty_and_closed(self):
        self.switch_to(self.family)
        response = self.client.get(reverse("deploy-location", args=["training"]))
        self.assertTrue(response.context["off_limits"])
        self.assertEqual(list(response.context["missions"]), [])

    def test_low_stock_puts_supply_in_action_required(self):
        pantry = self.user.personal_unit.tasks.get(type=TaskType.PANTRY)
        PantryItem.objects.create(task=pantry, name="milk", quantity=0, threshold=1)
        response = self.client.get(reverse("deploy-location", args=["supply"]))
        keys = [key for key, _label, _missions in response.context["groups"]]
        self.assertEqual(keys[0], "overdue")


class DebriefViewTests(CommonTestCase):
    url_name = "debrief"

    def test_quick_create_lands_in_the_active_unit(self):
        self.switch_to(self.family)
        self.client.post(reverse(self.url_name), {"name": "Book dentist", "type": TaskType.ONEOFF})
        self.assertEqual(Task.objects.get(name="Book dentist").unit, self.family)

    def test_quick_create_always_makes_a_standing_order(self):
        self.client.post(reverse(self.url_name), {"name": "Second list", "type": TaskType.GROCERIES})
        self.assertEqual(Task.objects.get(name="Second list").type, TaskType.ONEOFF)

    def test_counts_ignore_singletons_and_count_accomplished(self):
        self.make(name="open")
        done = self.make(name="done")
        done.accomplish(self.user)

        response = self.client.get(reverse(self.url_name))
        self.assertEqual(response.context["open_tasks_count"], 1)
        self.assertEqual(response.context["done_tasks_count"], 1)

    def test_overdue_includes_low_stock(self):
        pantry = self.user.personal_unit.tasks.get(type=TaskType.PANTRY)
        PantryItem.objects.create(task=pantry, name="milk", quantity=0, threshold=1)
        response = self.client.get(reverse(self.url_name))
        self.assertIn(pantry, response.context["overdue_tasks"])


class TypeNavTests(CommonTestCase):
    def nav(self):
        response = self.client.get(reverse("deploy"))
        return {entry["value"]: entry for entry in response.context["type_nav"]}

    def test_labels_are_types_not_priorities(self):
        self.make()
        nav = self.nav()
        self.assertEqual(nav["none"]["label"], TaskType.ONEOFF.label)
        self.assertEqual(nav["chores"]["label"], TaskType.CHORES.label)

    def test_due_chores_raise_attention(self):
        chores = self.user.personal_unit.tasks.get(type=TaskType.CHORES)
        ChoreItem.objects.create(
            task=chores, name="sweep", frequency_days=1,
            last_done_at=timezone.now() - timedelta(days=3),
        )
        nav = self.nav()
        self.assertTrue(nav["chores"]["attention"])
        self.assertFalse(nav["groceries"]["attention"])


TINY = """
#####
#a.b#
#.#.#
#@..#
#####
"""


def tiny(**overrides):
    kwargs = dict(
        grid=TINY,
        terrain={"#": "wall", ".": "floor", "@": "floor"},
        places={"a": "alpha", "b": "bravo"},
        walkable=frozenset(".@"),
        default_terrain="floor",
    )
    kwargs.update(overrides)
    return GridMap(**kwargs)


class GridMapShapeTests(SimpleTestCase):
    def test_size_in_pixels(self):
        grid = tiny()
        self.assertEqual((grid.width, grid.height), (5 * 32, 5 * 32))

    def test_ragged_rows_are_rejected(self):
        with self.assertRaisesMessage(ValueError, "same width"):
            tiny(grid="###\n##\n")

    def test_unknown_characters_are_rejected(self):
        with self.assertRaisesMessage(ValueError, "['?']"):
            tiny(grid="#?#\n###\n")

    def test_place_positions(self):
        self.assertEqual(tiny().place_positions(), {"alpha": (1, 1), "bravo": (3, 1)})

    def test_position_of(self):
        self.assertEqual(tiny().position_of("@"), (1, 3))

    def test_places_without_terrain_use_the_default(self):
        kinds = {(t["x"], t["y"]): t["kind"] for t in tiny().BASE.tiles()}
        self.assertEqual(kinds[(32, 32)], "floor")
        self.assertEqual(kinds[(0, 0)], "wall")


class FindPathTests(SimpleTestCase):
    def test_path_goes_around_walls(self):
        path = tiny().find_path((1, 3), (3, 1))
        self.assertEqual(path, [(1, 3), (2, 3), (3, 3), (3, 2), (3, 1)])

    def test_goal_does_not_need_to_be_walkable(self):
        self.assertEqual(tiny().find_path((1, 3), (1, 1)), [(1, 3), (1, 2), (1, 1)])

    def test_no_route_returns_empty_list(self):
        path = tiny(walkable=frozenset("@")).find_path((1, 3), (3, 1))
        self.assertEqual(path, [])

    def test_start_equals_goal(self):
        self.assertEqual(tiny().find_path((1, 3), (1, 3)), [(1, 3)])


class BarracksMapTests(SimpleTestCase):
    def test_every_room_is_reachable_from_the_entrance(self):
        start = BARRACKS.position_of(ENTRANCE)
        for room, pos in BARRACKS.place_positions().items():
            with self.subTest(room=room):
                path = BARRACKS.find_path(start, pos)
                self.assertTrue(path)
                self.assertNotIn("#", [BARRACKS.char_at(p) for p in path])

    def test_rooms_are_entered_through_a_door(self):
        start = BARRACKS.position_of(ENTRANCE)
        for room in ("kitchen", "bedroom", "living", "bathroom"):
            with self.subTest(room=room):
                path = BARRACKS.find_path(start, BARRACKS.place_positions()[room])
                self.assertIn("+", [BARRACKS.char_at(p) for p in path])

    def test_every_room_appears_once(self):
        expected = {"kitchen", "bathroom", "bedroom", "living", "outdoor", "general"}
        self.assertEqual(set(BARRACKS.place_positions()), expected)

