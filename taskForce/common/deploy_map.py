from collections import deque

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


def tiles():
    for row, line in enumerate(map_rows()):
        for col, char in enumerate(line):
            yield {"kind": TERRAIN.get(char, "grass"), "x": col * TILE, "y": row * TILE}


def find_path(start, goal):
    rows = map_rows()
    came_from = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        col, row = current
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (col + dc, row + dr)
            c, r = nxt
            if not (0 <= r < len(rows) and 0 <= c < len(rows[r])) or nxt in came_from:
                continue
            if rows[r][c] == "=" or nxt == goal:
                came_from[nxt] = current
                queue.append(nxt)

    if goal not in came_from:
        return []
    path, node = [], goal
    while node is not None:
        path.append(node)
        node = came_from[node]
    return path[::-1]