"""Barracks floor plan: placeholder layout (data only, no engine yet).

Same conventions as common/deploy_map.py: one character = one 32x32 tile.

Room markers work like buildings on the base map: they mark where the room's
furniture sprite, badge and label sit. Each marker is ALSO listed in TERRAIN,
so tiles() draws the right floor underneath it.

The avatar starts on the entrance tile ("@"), like it starts at HQ outside.
"""

from common.grid_map import GridMap

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

