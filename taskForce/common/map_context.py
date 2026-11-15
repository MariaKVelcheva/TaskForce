SPRITE_LIFT = 16


def map_context(grid, start, goal=None, idle=None, stop_short=0):
    tile = grid.tile
    avatar = idle or start
    route = ""

    if goal is not None and goal != start:
        path = grid.find_path(start, goal)
        if len(path) > 2:
            walk = path[1:-1]
            route = " ".join(
                f"{c * tile + tile // 2},{r * tile + tile // 2}" for c, r in walk
            )
            avatar = walk[max(len(walk) - 1 - stop_short, 0)]

    return {
        "tiles": list(grid.tiles()),
        "map_width": grid.width,
        "map_height": grid.height,
        "route": route,
        "avatar_x": avatar[0] * tile,
        "avatar_y": avatar[1] * tile - SPRITE_LIFT,
    }

