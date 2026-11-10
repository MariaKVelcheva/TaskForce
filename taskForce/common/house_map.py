from taskForce.common.grid_map import GridMap


HOUSE = """
\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"
\"\"\"\"\"\"\"\"\"g\"\"\"\"\"\"\"\"\"\"
\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"\"
#########+##########
#_______#..#:::::::#
#___k___+..+:::r:::#
#_______#..#:::::::#
#_______#..#:::::::#
#########..#########
#.......#..#_______#
#...l...+.h+___b___#
#.......#..#_______#
#.......#..#_______#
#########@##########
\"\"\"\"\"\"\"\"\"=\"\"\"\"\"\"\"\"\"\"
"""

TERRAIN = {
    "#": "wall",
    ".": "floor-wood",
    "_": "floor-tile",
    ":": "floor-carpet",
    "+": "door",
    "@": "entrance",
    '"': "lawn",
    "=": "path",
    # Room markers: the floor drawn under the furniture.
    "k": "floor-tile",
    "b": "floor-tile",
    "r": "floor-carpet",
    "l": "floor-wood",
    "h": "floor-wood",
    "g": "lawn",
}

# Values match the Room TextChoices, except "general": its stored value is ""
# (which can't be a symbol id), so map it to Room.GENERAL in code.
ROOMS = {
    "k": "kitchen",
    "b": "bathroom",
    "r": "bedroom",
    "l": "living",
    "g": "outdoor",
    "h": "general",
}

ENTRANCE = "@"

# Everything the avatar may walk on (walls are the only obstacle).
WALKABLE = set('._:+@"=') | set(ROOMS)

TILE = 32

BARRACKS = GridMap(
    grid=HOUSE,
    terrain=TERRAIN,
    places=ROOMS,
    walkable=frozenset(WALKABLE),
    default_terrain="floor-wood",
    tile=TILE,
)

