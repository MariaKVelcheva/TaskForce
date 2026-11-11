from taskForce.common.grid_map import GridMap


MAP = """
TTTTTTTTTTTTTTTTTT
TT.....~~~~~...TTT
T.......~~~.....TT
T..t.....=....s..T
T..=.....=....=..T
TT.=..T..=..T.=.TT
T..============..T
T..=.....=....=..T
TT.b.....=....r.TT
T........H.......T
TTT......=.....TTT
TTTTTTTTT=TTTTTTTT
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

