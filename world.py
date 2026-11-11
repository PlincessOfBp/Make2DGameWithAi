from itertools import count
from math import cos, hypot, pi, sin
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
        self.attack_target = None
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
        self.drop_ids = count()
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
        if pickup_id.startswith("stone:"):
            self.stone_respawns[pickup_id] = (self.resource_time + STONE_RESPAWN_SECONDS, pickup)
        return pickup[0]

    def update_resources(self, dt, player_x, player_y):

        self.resource_time += dt
        for pickup_id, (ready_at, pickup) in tuple(self.stone_respawns.items()):
            _, x, y, _ = pickup
            if self.resource_time >= ready_at and hypot(player_x - x, player_y - y) >= STONE_SPAWN_CLEARANCE:
                self.pickups[pickup_id] = pickup
                del self.stone_respawns[pickup_id]
        for (x, y), ready_at in tuple(self.tree_respawns.items()):
            wall = self.tree_walls[x, y]
            left, bottom, right, top = wall
            occupied = hypot(player_x - x, player_y - y) < 32 or any(
                hypot(z.x - x, z.y - y) < 24 for z in self.zombies if z.state not in ("dead", "escaped")
            )
            overlaps_wall = any(left < r and right > l and bottom < t and top > b
                                for l, b, r, t in self.walls)
            if self.resource_time >= ready_at and not occupied and not overlaps_wall:
                self.trees.append((x, y))
                self.walls.append(wall)
                del self.tree_respawns[x, y]

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

    def resolve_player_action(self, player, action, angle, weapon):
        forward_x, forward_y = -sin(angle), cos(angle)
        reach = 46 if action == "bite" else 78
        targets = [(z.x, z.y, z) for z in self.zombies if z.state == "zombie"
                   and (action != "bite" or z.purify_at is None)]
        if action == "attack" and weapon in WOOD_TOOLS:
            targets.extend((x, y, None) for x, y in self.trees)
        hits = []
        for x, y, zombie in targets:
            dx, dy = x - player.x, y - player.y
            distance = hypot(dx, dy)
            if distance > reach or dx * forward_x + dy * forward_y < distance * 0.65:
                continue
            if zombie is None and distance:
                # Stop the ray just before the target tree's own trunk.
                x -= dx * min(1, 15 / distance)
                y -= dy * min(1, 15 / distance)
            if self.pickup_path_clear(player.x, player.y, x, y):
                hits.append((distance, zombie, (player.x + dx, player.y + dy)))
        if not hits:
            return
        _, zombie, position = min(hits, key=lambda hit: hit[0])
        if zombie is None:
            self.harvest_tree(player, position)
        elif action == "bite":
            zombie.purify_at = self.resource_time + 10
            player.infection = min(100, player.infection + 10)
        else:
            self.attack_target = zombie
            self.hit_zombie(zombie, WEAPON_DAMAGE[weapon])

    def hit_zombie(self, zombie, damage):
        if zombie.state != "zombie":
            return
        zombie.health = max(0, zombie.health - damage)
        if zombie.health:
            return
        zombie.state = "dead"
        zombie.purify_at = None
        if self.random.random() < 0.35:
            item = self.random.choice(("axe", "knife", "canned_food"))
            self.pickups[f"zombie:{zombie.entity_id}"] = (
                item, zombie.x, zombie.y, self.building_at(zombie.x, zombie.y),
            )

    def harvest_tree(self, player, position):
        if position not in self.trees:
            return False
        self.trees.remove(position)
        self.walls.remove(self.tree_walls[position])
        self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
        player.inventory.add("wood")
        return True

    def ally_at(self, player, x, y):
        candidates = [z for z in self.zombies if z.state == "ally"
                      and hypot(z.x - x, z.y - y) <= 23
                      and hypot(z.x - player.x, z.y - player.y) <= 90
                      and self.pickup_path_clear(player.x, player.y, z.x, z.y)]
        return min(candidates, key=lambda z: hypot(z.x - x, z.y - y), default=None)

    def drop_item(self, player, item):
        pass
