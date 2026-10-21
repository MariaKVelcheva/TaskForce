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


def map_rows():
    return MAP.strip().splitlines()


def building_positions():
    positions = {}
    for row, line in enumerate(map_rows()):
        for col, char in enumerate(line):
            if char in BUILDINGS:
                positions[BUILDINGS[char]] = (col, row)
    return positions