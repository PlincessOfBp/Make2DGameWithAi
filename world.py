from heapq import heappop, heappush
from itertools import count
from math import cos, hypot, pi, sin
from random import Random

from item_data import TREE_DAMAGE, TREE_MAX_HP, WEAPON_DAMAGE
from zombie import Zombie

from town import (
    FARMING_LOOT, PICKUP_ICON_HALF_SIZE, PICKUP_REACH,
    STONE_POINTS, STONE_RESPAWN_SECONDS, STONE_SPAWN_CLEARANCE,
    BUILDING_LAYOUTS, BUILDING_SCALES, BUILDINGS, FURNITURE,
    MAP_HEIGHT, MAP_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH,
    TREE_RESPAWN_SECONDS, TREE_TRUNKS, TREE_TRUNK_HALF_HEIGHT, TREE_TRUNK_HALF_WIDTH, ZOMBIE_POINTS,
)


class World:
    def __init__(self, player=None):
        self.audio = None
        self.player = player
        self.buildings = []
        self.trees = dict.fromkeys(TREE_TRUNKS, TREE_MAX_HP)
        self.tree_walls = {
            (x, y): (x - TREE_TRUNK_HALF_WIDTH, y - TREE_TRUNK_HALF_HEIGHT,
                     x + TREE_TRUNK_HALF_WIDTH, y + TREE_TRUNK_HALF_HEIGHT)
            for x, y in self.trees
        }
        self.walls = list(self.tree_walls.values())
        self.tree_respawns = {}
        self.barricades = []
        self.attack_target = None
        self.attack_target_at = float('-inf')
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
        self.dropped_durability = {}
        self.resource_time = 0.0

    def camera(self, x, y):
        return (
            min(max(round(x) - SCREEN_WIDTH // 2, 0), MAP_WIDTH - SCREEN_WIDTH),
            min(max(round(y) - SCREEN_HEIGHT // 2, 0), MAP_HEIGHT - SCREEN_HEIGHT),
        )

    def sound(self, event, x=None, y=None):
        if self.audio is None:
            return
        if x is not None and self.player is not None:
            if hypot(x - self.player.x, y - self.player.y) > 300:
                return
            if event != "tree" and not self.pickup_path_clear(self.player.x, self.player.y, x, y):
                return
        self.audio.play(event)


    def move(self, x, y, dx, dy, radius, actor=None):
        obstacles = self.collision_obstacles(actor)

        # Sweep each axis separately so the actor can slide along solid objects.
        next_x = min(max(x + dx, radius), MAP_WIDTH - radius)
        for left, bottom, right, top in obstacles:
            if bottom - radius < y < top + radius:
                if x <= left - radius:
                    next_x = min(next_x, left - radius)
                elif x >= right + radius:
                    next_x = max(next_x, right + radius)

        next_y = min(max(y + dy, radius), MAP_HEIGHT - radius)
        for left, bottom, right, top in obstacles:
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

        building = self.revealed_building(x, y)
        for pickup_id, (item, px, py, location) in self.pickups.items():
            if location is None or location == building:
                yield pickup_id, item, px, py

    def revealed_building(self, x, y):
        inside = self.building_at(x, y)
        if inside is not None:
            return inside
        for index in range(len(self.buildings)):
            door_x, threshold = self.building_entrance(index)
            if abs(x - door_x) <= 24 and 0 <= threshold - y <= 44:
                return index
        return None

    def building_entrance(self, index):
        kind, cx, cy, width, height, _ = self.buildings[index]
        scale = BUILDING_SCALES.get(kind, 1)
        image_width = BUILDING_LAYOUTS[kind][0][0]
        door_x = cx - width // 2 + (70 if kind == "house_corner" else image_width / 2) * scale
        return door_x, cy - height // 2 + 3 * scale

    def pickup_path_clear(self, x, y, target_x, target_y, clearance=0, obstacles=None):

        dx, dy = target_x - x, target_y - y
        min_x, max_x = sorted((x, target_x))
        min_y, max_y = sorted((y, target_y))
        walls = self.walls if obstacles is None else obstacles
        for left, bottom, right, top in walls:
            left, bottom = left - clearance, bottom - clearance
            right, top = right + clearance, top + clearance
            if max_x <= left or min_x >= right or max_y <= bottom or min_y >= top:
                continue
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

    def collect_pickup(self, x, y, mouse_x, mouse_y, inventory=None):

        building = self.building_at(x, y)
        candidates = (
            (hypot(mouse_x - px, mouse_y - py), pickup_id)
            for pickup_id, _, px, py in self.visible_pickups(x, y)
            if abs(mouse_x - px) <= PICKUP_ICON_HALF_SIZE
            and self.pickups[pickup_id][3] in (None, building)
            and abs(mouse_y - py) <= PICKUP_ICON_HALF_SIZE
            and hypot(x - px, y - py) <= PICKUP_REACH
            and self.pickup_path_clear(x, y, px, py)
        )
        nearest = min(candidates, default=None)
        if nearest is None:
            return None
        pickup_id = nearest[1]
        durability = self.dropped_durability.pop(pickup_id, None)
        item = self.take_pickup(pickup_id)
        if inventory is not None:
            inventory.add(item, durability=durability)
        return item

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
            pickup_in_trunk = any(left <= px <= right and bottom <= py <= top
                                  for _, px, py, _ in self.pickups.values())
            if self.resource_time >= ready_at and not occupied and not overlaps_wall and not pickup_in_trunk:
                self.trees[x, y] = TREE_MAX_HP
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
        if action == "attack" and weapon in TREE_DAMAGE:
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
            self.hit_tree(position, weapon)
        elif action == "bite":
            self.sound("bite")
            zombie.purify_at = self.resource_time + 10
            player.infection = min(100, player.infection + 20)
        else:
            self.attack_target = zombie
            self.attack_target_at = self.resource_time
            self.hit_zombie(zombie, WEAPON_DAMAGE[weapon])
        if action == "attack":
            player.inventory.wear_tool(weapon)

    def hit_zombie(self, zombie, damage):
        if zombie.state != "zombie":
            return
        self.sound("hit", zombie.x, zombie.y)
        zombie.health = max(0, zombie.health - damage)
        if zombie.health:
            zombie.hurt_until = self.resource_time + 0.16
            return
        zombie.state = "dead"
        zombie.purify_at = None
        if self.random.random() < 0.35:
            item = self.random.choice(("axe", "knife", "canned_food"))
            self.pickups[f"zombie:{zombie.entity_id}"] = (
                item, zombie.x, zombie.y, self.building_at(zombie.x, zombie.y),
            )

    def ally_at(self, player, x, y):
        candidates = [z for z in self.zombies if hypot(z.x - x, z.y - y) <= 23
                      and self.can_command_ally(player, z)]
        return min(candidates, key=lambda z: hypot(z.x - x, z.y - y), default=None)

    def drop_item(self, player, item):
        # Try in front first, then nearby directions when a wall or pickup blocks the spot.
        building = self.building_at(player.x, player.y)
        for offset in (0, pi / 4, -pi / 4, pi / 2, -pi / 2, pi):
            angle = player.target_angle + offset
            for distance in (44, 30):
                x = round(player.x - sin(angle) * distance)
                y = round(player.y + cos(angle) * distance)
                if self.building_at(x, y) != building:
                    continue
                if self.move(player.x, player.y, x - player.x, y - player.y, 8) != (x, y):
                    continue
                if not self.pickup_path_clear(player.x, player.y, x, y):
                    continue
                if any(hypot(x - px, y - py) < 24 for _, px, py, _ in self.pickups.values()):
                    continue
                pickup_id = f"drop:{next(self.drop_ids)}"
                self.pickups[pickup_id] = (item, x, y, building)
                if item in player.inventory.durability:
                    self.dropped_durability[pickup_id] = player.inventory.durability[item][0]
                return True
        return False

    def hit_tree(self, position, weapon, inventory=None):
        damage = TREE_DAMAGE.get(weapon)
        if damage is None or position not in self.trees:
            return False
        self.sound("tree", *position)
        remaining = self.trees[position] - damage
        if remaining > 0:
            self.trees[position] = remaining
            return False
        del self.trees[position]
        self.walls.remove(self.tree_walls[position])
        self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
        if inventory is None:
            x, y = position
            self.pickups[f"drop:{next(self.drop_ids)}"] = ("wood", x, y, self.building_at(x, y))
        else:
            inventory.add("wood")
        return True

    def find_route(self, start, goal, radius, obstacles=None):
        walls = self.walls if obstacles is None else obstacles
        if self.pickup_path_clear(*start, *goal, radius, walls):
            return [goal]

        # Wall corners make waypoints without snapping actors to a grid at narrow doors.
        margin = radius + 1
        min_x, max_x = sorted((start[0], goal[0]))
        min_y, max_y = sorted((start[1], goal[1]))
        corners = set()
        for left, bottom, right, top in walls:
            if right < min_x - 240 or left > max_x + 240 or top < min_y - 240 or bottom > max_y + 240:
                continue
            for x in (left - margin, right + margin):
                for y in (bottom - margin, top + margin):
                    if (radius <= x <= MAP_WIDTH - radius and radius <= y <= MAP_HEIGHT - radius
                            and self.pickup_path_clear(x, y, x, y, radius, walls)):
                        corners.add((x, y))
        candidates = sorted(corners | {goal})
        estimate = {point: hypot(goal[0] - point[0], goal[1] - point[1]) for point in candidates}
        frontier = [(hypot(goal[0] - start[0], goal[1] - start[1]), 0.0, start)]
        distances = {start: 0.0}
        parents = {}
        visited = set()
        while frontier:
            _, distance, point = heappop(frontier)
            if point in visited:
                continue
            if point == goal:
                route = []
                while point != start:
                    route.append(point)
                    point = parents[point]
                return route[::-1]
            visited.add(point)
            for candidate in candidates:
                if candidate in visited:
                    continue
                cost = distance + hypot(candidate[0] - point[0], candidate[1] - point[1])
                if (cost >= distances.get(candidate, float("inf"))
                        or not self.pickup_path_clear(*point, *candidate, radius, walls)):
                    continue
                distances[candidate] = cost
                parents[candidate] = point
                heappush(frontier, (cost + estimate[candidate], cost, candidate))
        return []

    def actor_by_id(self, entity_id):
        return next((actor for actor in self.zombies if actor.entity_id == entity_id), None)

    def take_pickup(self, pickup_id):
        pickup = self.pickups.pop(pickup_id, None)
        if pickup is None:
            return None
        if pickup_id.startswith("stone:"):
            self.stone_respawns[pickup_id] = (self.resource_time + STONE_RESPAWN_SECONDS, pickup)
        return pickup[0]

    def can_command_ally(self, player, ally):
        return (ally.state == "ally"
                and hypot(ally.x - player.x, ally.y - player.y) <= 90
                and self.building_at(ally.x, ally.y) in (None, self.building_at(player.x, player.y))
                and self.pickup_path_clear(player.x, player.y, ally.x, ally.y))

    def nearby_allies(self, player):
        return tuple(actor for actor in self.zombies if actor.state == "ally"
                     and hypot(actor.x - player.x, actor.y - player.y) <= 260)

    def collision_obstacles(self, actor=None):
        if actor is None:
            return self.walls
        bodies = (self.player, *self.zombies)
        return self.walls + [
            (body.x - body.RADIUS, body.y - body.RADIUS,
             body.x + body.RADIUS, body.y + body.RADIUS)
            for body in bodies
            if body is not None and body is not actor
            and getattr(body, "state", None) not in ("dead", "escaped")
            and body.health > 0
        ]
