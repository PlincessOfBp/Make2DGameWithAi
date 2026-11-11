from math import cos, hypot, sin
from random import Random

from item_data import WEAPON_DAMAGE, WOOD_TOOLS
from zombie import Zombie

from town import (
    FARMING_LOOT, PICKUP_ICON_HALF_SIZE, PICKUP_REACH,
    STONE_POINTS, STONE_RESPAWN_SECONDS, STONE_SPAWN_CLEARANCE,
    BUILDING_LAYOUTS, BUILDING_SCALES, BUILDINGS, FURNITURE,
    MAP_HEIGHT, MAP_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH,
    TREE_RESPAWN_SECONDS, TREE_TRUNKS, TREE_TRUNK_HALF_HEIGHT, TREE_TRUNK_HALF_WIDTH, ZOMBIE_POINTS,
)


class World:
    def __init__(self):
        self.buildings = []
        self.trees = list(TREE_TRUNKS)
        self.tree_walls = {
            (x, y): (x - TREE_TRUNK_HALF_WIDTH, y - TREE_TRUNK_HALF_HEIGHT,
                     x + TREE_TRUNK_HALF_WIDTH, y + TREE_TRUNK_HALF_HEIGHT)
            for x, y in self.trees
        }
        self.walls = list(self.tree_walls.values())
        self.tree_respawns = {}
        self.barricades = []
        self.random = Random()
        self.zombies = [Zombie(index, x, y) for index, (x, y) in enumerate(ZOMBIE_POINTS)]
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

    def building_at(self, x, y):

        for index, (_, _, _, _, _, footprint) in enumerate(self.buildings):
            if any(left <= x <= right and bottom <= y <= top
                   for left, bottom, right, top in footprint):
                return index
        return None

    def visible_pickups(self, x, y):

        building = self.building_at(x, y)
        for pickup_id, (item, px, py, location) in self.pickups.items():
            if location is None or location == building:
                yield pickup_id, item, px, py

    def pickup_path_clear(self, x, y, target_x, target_y):

        dx, dy = target_x - x, target_y - y
        for left, bottom, right, top in self.walls:
            # Intersect the segment's parameter range with the rectangle on each axis.
            start, end = 0.0, 1.0
            for origin, delta, low, high in ((x, dx, left, right), (y, dy, bottom, top)):
                if delta == 0:
                    if not low < origin < high:
                        break
                    continue
                first, last = sorted(((low - origin) / delta, (high - origin) / delta))
                start, end = max(start, first), min(end, last)
                if start >= end:
                    break
            else:
                return False
        return True

    def collect_pickup(self, x, y, mouse_x, mouse_y):

        candidates = (
            (hypot(mouse_x - px, mouse_y - py), pickup_id)
            for pickup_id, _, px, py in self.visible_pickups(x, y)
            if abs(mouse_x - px) <= PICKUP_ICON_HALF_SIZE
            and abs(mouse_y - py) <= PICKUP_ICON_HALF_SIZE
            and hypot(x - px, y - py) <= PICKUP_REACH
            and self.pickup_path_clear(x, y, px, py)
        )
        nearest = min(candidates, default=None)
        if nearest is None:
            return None
        _, pickup_id = nearest
        pickup = self.pickups.pop(pickup_id)
        if pickup[0] == "stone":
            self.stone_respawns[pickup_id] = (self.resource_time + STONE_RESPAWN_SECONDS, pickup)
        return pickup[0]

    def update_resources(self, dt, player_x, player_y):

        self.resource_time += dt
        for pickup_id, (ready_at, pickup) in tuple(self.stone_respawns.items()):
            _, x, y, _ = pickup
            if self.resource_time >= ready_at and hypot(player_x - x, player_y - y) >= STONE_SPAWN_CLEARANCE:
                self.pickups[pickup_id] = pickup
                del self.stone_respawns[pickup_id]

    def place_barricade(self, player, x, y):
        left, bottom, right, top = x - 29, y - 14, x + 29, y + 14
        if left < 0 or bottom < 0 or right > MAP_WIDTH or top > MAP_HEIGHT:
            return False
        if any(left < r and right > l and bottom < t and top > b for l, b, r, t in self.walls):
            return False
        actors = [player, *(z for z in self.zombies if z.state not in ("dead", "escaped"))]
        if any(left - 8 < actor.x < right + 8 and bottom - 8 < actor.y < top + 8 for actor in actors):
            return False
        if any(left <= px <= right and bottom <= py <= top for _, px, py, _ in self.pickups.values()):
            return False
        self.walls.append((left, bottom, right, top))
        self.barricades.append((x, y))
        return True
