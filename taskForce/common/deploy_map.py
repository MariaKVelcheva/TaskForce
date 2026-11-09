from taskForce.common.grid_map import GridMap

MAP = """
TTTTTTTTTTTTTTTTTTTTTTTT
TT....TTT...~~~...TTT.TT
T.........~~~~~~.......T
T...t.....~~~~~.....s..T
T...=.......=.......=..T
TT..=..T....=....T..=..T
T...=.......=.......=.TT
T...=.......=.......=..T
T...=================..T
T...=.......=.......=..T
TT..=..T....=....T..=.TT
T...b.......=.......r..T
T...........=..........T
TT..........H.........TT
TTT.........=........TTT
TTTTTTTTTTTT=TTTTTTTTTTT
"""

TERRAIN = {
    "T": "forest",
    ".": "grass",
    "=": "road",
    "~": "water",
}

BUILDINGS = {
    "H": "hq",
    "t": "training",
    "s": "supply",
    "b": "barracks",
    "r": "rec_room",
}

TILE = 32

BASE = GridMap(
    grid=MAP,
    terrain=TERRAIN,
    places=BUILDINGS,
    walkable=frozenset("="),
    default_terrain="grass",
    tile=TILE,
)


def map_rows():
    return BASE.rows


def building_positions():
    return BASE.place_positions()


def tiles():
    return BASE.tiles()


def find_path(start, goal):
    return BASE.find_path(start, goal)

