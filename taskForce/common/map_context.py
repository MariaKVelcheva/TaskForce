"""Template context for drawing a GridMap with the avatar on it.

Shared by the base map (Deploy) and the barracks floor plan: the template
needs the same things for both, only the map and the start/goal differ.
"""

# Buildings, rooms and the avatar are 32x48 sprites standing on a 32x32 tile,
# so they are drawn 16px higher than the tile itself.
SPRITE_LIFT = 16


def map_context(grid, start, goal=None, idle=None):
    """Tiles, size, route and avatar position for one map.

    With nowhere to go, the avatar waits at `idle` (default: the start tile).
    With a goal, it walks from start towards it and stops on the tile just
    before, so it stands in front of the building or room, not on top of it.
    """
    tile = grid.tile
    avatar = idle or start
    route = ""

    if goal is not None and goal != start:
        path = grid.find_path(start, goal)
        # path = [start, ..., goal]; 2 or fewer tiles means already next to it.
        if len(path) > 2:
            walk = path[1:-1]
            route = " ".join(
                f"{c * tile + tile // 2},{r * tile + tile // 2}" for c, r in walk
            )
            avatar = walk[-1]

    return {
        "tiles": list(grid.tiles()),
        "map_width": grid.width,
        "map_height": grid.height,
        "route": route,
        "avatar_x": avatar[0] * tile,
        "avatar_y": avatar[1] * tile - SPRITE_LIFT,
    }

