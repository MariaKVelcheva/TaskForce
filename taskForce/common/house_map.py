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

"""
basic room bedroom in barracks sprites:
  <symbol id="room-bedroom" viewBox="0 0 32 48">
    <ellipse class="hb-shadow" cx="16" cy="44" rx="15" ry="3"/>
    <rect x="3" y="10" width="2" height="34" fill="#545846" class="hb-line"/>
    <rect x="27" y="10" width="2" height="34" fill="#545846" class="hb-line"/>

    <rect x="5" y="12.5" width="22" height="4" rx="1" fill="url(#hb-olive)" class="hb-line"/>
    <rect x="6" y="11.5" width="6" height="3" rx="1.2" fill="#e8dcb8" class="hb-line"/>
    <rect x="4" y="16" width="24" height="3" fill="url(#hb-steel)" class="hb-line"/>

    <rect x="5" y="30.5" width="22" height="4" rx="1" fill="url(#hb-olive)" class="hb-line"/>
    <rect x="6" y="29.5" width="6" height="3" rx="1.2" fill="#e8dcb8" class="hb-line"/>
    <rect x="4" y="34" width="24" height="3" fill="url(#hb-steel)" class="hb-line"/>

    <path d="M22 19v11.5M25 19v11.5M22 22.5h3M22 26.5h3" stroke="#373b2c" stroke-width=".7"/>

    <rect x="9" y="38" width="14" height="5.5" rx=".8" fill="url(#hb-wood)" class="hb-line"/>
    <path d="M12 38v5.5M20 38v5.5" stroke="#4d5549" stroke-width="1"/>
  </symbol>
  """