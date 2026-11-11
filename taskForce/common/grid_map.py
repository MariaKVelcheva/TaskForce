"""Maps drawn as text: one character = one tile.

A GridMap answers three questions about each character in the grid:

- terrain:  which tile sprite to draw under it (``tile-<kind>``)
- places:   is it a clickable spot? (a building on the base, a room in the barracks)
- walkable: may the avatar step on it?

The base map and the barracks floor plan are two instances of this one class,
so they share the drawing and path-finding code, and its tests.
"""

from collections import deque
from dataclasses import dataclass
from functools import cached_property

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass(frozen=True)
class GridMap:
    grid: str
    terrain: dict
    places: dict
    walkable: frozenset
    default_terrain: str
    tile: int = 32

    def __post_init__(self):
        widths = {len(line) for line in self.rows}
        if len(widths) != 1:
            raise ValueError(f"All rows must have the same width, got {sorted(widths)}")
        known = set(self.terrain) | set(self.places)
        unknown = {char for _, char in self.cells()} - known
        if unknown:
            raise ValueError(f"Characters missing from terrain/places: {sorted(unknown)}")

    @cached_property
    def rows(self):
        return self.grid.strip().splitlines()

    @property
    def width(self):
        return len(self.rows[0]) * self.tile

    @property
    def height(self):
        return len(self.rows) * self.tile

    def cells(self):
        for row, line in enumerate(self.rows):
            for col, char in enumerate(line):
                yield (col, row), char

    def char_at(self, pos):
        col, row = pos
        if 0 <= row < len(self.rows) and 0 <= col < len(self.rows[row]):
            return self.rows[row][col]
        return None

    def position_of(self, char):
        for pos, c in self.cells():
            if c == char:
                return pos
        raise ValueError(f"{char!r} is not on this map")

    def place_positions(self):
        return {self.places[char]: pos for pos, char in self.cells() if char in self.places}

    def tiles(self):
        for (col, row), char in self.cells():
            yield {
                "kind": self.terrain.get(char, self.default_terrain),
                "x": col * self.tile,
                "y": row * self.tile,
            }

    def find_path(self, start, goal):
        came_from = {start: None}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            col, row = current
            for dc, dr in STEPS:
                nxt = (col + dc, row + dr)
                if nxt in came_from:
                    continue
                if nxt == goal or self.char_at(nxt) in self.walkable:
                    came_from[nxt] = current
                    queue.append(nxt)

        if goal not in came_from:
            return []
        path, node = [], goal
        while node is not None:
            path.append(node)
            node = came_from[node]
        return path[::-1]

