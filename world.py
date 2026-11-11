from math import hypot

from town import (
    FARMING_LOOT, PICKUP_ICON_HALF_SIZE, PICKUP_REACH,
    STONE_POINTS, STONE_RESPAWN_SECONDS, STONE_SPAWN_CLEARANCE,
    BUILDING_LAYOUTS, BUILDING_SCALES, BUILDINGS, FURNITURE,
    MAP_HEIGHT, MAP_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH,
    TREE_TRUNKS, TREE_TRUNK_HALF_HEIGHT, TREE_TRUNK_HALF_WIDTH,
)


class World:
    def __init__(self):
        self.buildings = []
        self.trees = TREE_TRUNKS
        self.walls = [
            (x - TREE_TRUNK_HALF_WIDTH, y - TREE_TRUNK_HALF_HEIGHT,
             x + TREE_TRUNK_HALF_WIDTH, y + TREE_TRUNK_HALF_HEIGHT)
            for x, y in self.trees
        ]
        self.furniture = {}
        for kind, x, y in BUILDINGS:
            (image_width, image_height), rooms, walls = BUILDING_LAYOUTS[kind]
            scale = BUILDING_SCALES.get(kind, 1)
            width, height = round(image_width * scale), round(image_height * scale)
            left, bottom = x - width // 2, y - height // 2
            footprint = tuple(
                (left + a * scale, bottom + b * scale, left + c * scale, bottom + d * scale)
                for a, b, c, d in rooms
            )
            self.buildings.append((kind, x, y, width, height, footprint))
            self.furniture[x, y] = []
            for name, px, py, prop_width, prop_height in FURNITURE[kind]:
                cx, cy = left + round(px * scale), bottom + round(py * scale)
                self.furniture[x, y].append((name, cx, cy))
                half_width, half_height = prop_width / 2, prop_height / 2
                self.walls.append((cx - half_width, cy - half_height,
                                   cx + half_width, cy + half_height))
            self.walls.extend(
                (left + a * scale, bottom + b * scale, left + c * scale, bottom + d * scale)
                for a, b, c, d in walls
            )

        # Pickup records contain the item, world position, and optional building index.
        self.pickups = {
            f"stone:{index}": ("stone", x, y, None)
            for index, (x, y) in enumerate(STONE_POINTS)
        }
        for index, ((_, x, y, *_), loot) in enumerate(zip(self.buildings, FARMING_LOOT, strict=True)):
            for slot, (item, dx, dy) in enumerate(loot):
                self.pickups[f"loot:{index}:{slot}"] = (item, x + dx, y + dy, index)
        self.stone_respawns = {}
        self.resource_time = 0.0

    def camera(self, x, y):
        return (
            min(max(round(x) - SCREEN_WIDTH // 2, 0), MAP_WIDTH - SCREEN_WIDTH),
            min(max(round(y) - SCREEN_HEIGHT // 2, 0), MAP_HEIGHT - SCREEN_HEIGHT),
        )


    def move(self, x, y, dx, dy, radius):
        # Sweep each axis separately so the actor can slide along a wall.
        next_x = min(max(x + dx, radius), MAP_WIDTH - radius)
        for left, bottom, right, top in self.walls:
            if bottom - radius < y < top + radius:
                if x <= left - radius:
                    next_x = min(next_x, left - radius)
                elif x >= right + radius:
                    next_x = max(next_x, right + radius)

        next_y = min(max(y + dy, radius), MAP_HEIGHT - radius)
        for left, bottom, right, top in self.walls:
            if left - radius < next_x < right + radius:
                if y <= bottom - radius:
                    next_y = min(next_y, bottom - radius)
                elif y >= top + radius:
                    next_y = max(next_y, top + radius)
        return next_x, next_y
