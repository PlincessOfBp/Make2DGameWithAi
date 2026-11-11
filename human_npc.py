from math import atan2, cos, hypot, pi, sin, tau

from inventory import Inventory
from town import MAP_HEIGHT, MAP_WIDTH


GATHER_FRAME_TIME = 0.15
GATHER_REACH = 35
GATHER_LIMIT = 20
WOOD_GATHER_TOOL = "stone_axe"
GATHER_ROUTE_TIMEOUT = 1.0
ASSIST_RANGE = 220
ASSIST_MEMORY = 5.0
WAIT_RETREAT_LIMIT = 120
MELEE_STAND_DISTANCE = 26
MELEE_REPLAN_SECONDS = 0.35


class HumanNPC:
    def __init__(self, actor):
        self.actor = actor
        self.command = "wait"
        self.target = None
        self.destination = None
        self.escape_retry_at = 0.0
        self.gather_until = 0.0
        self.gather_pending = False
        self.tool = None
        self.inventory = Inventory()
        self.following = False
        self.gather_remaining = 0
        self.gather_origin = None
        self.gather_shortfall = 0
        self.gather_blocked_at = None
        self.skipped_resources = set()
        self.wait_origin = (actor.x, actor.y)
        self.returning_to_wait = False
        self.melee_route = []
        self.melee_target = None
        self.melee_target_position = None
        self.melee_retry_at = 0.0

    def set_command(self, world, command, amount=1):
        self.command = command
        if command == "wait":
            self.wait_origin = (self.actor.x, self.actor.y)
        self.returning_to_wait = False
        self.melee_route.clear()
        self.melee_target = None
        self.melee_retry_at = 0.0
        if command != "attack":
            self.following = command == "follow"
        gathering = command in ("wood", "stone")
        self.gather_remaining = max(1, min(amount, GATHER_LIMIT)) if gathering else 0
        self.gather_origin = (self.actor.x, self.actor.y) if gathering else None
        self.gather_shortfall = 0
        self.gather_blocked_at = None
        self.skipped_resources.clear()
        target = world.attack_target
        self.target = target.entity_id if command == "attack" and target is not None else None
        self.destination = None
        self.gather_pending = False
        self.gather_until = 0.0
        self.tool = None
        self.actor.route.clear()
        self.actor.route_goal = None
        self.actor.next_route_at = 0.0
        self.actor.walk_time = 0.0
        self.actor.attack_target = None
        self.actor.attack_until = 0.0

    def flee(self, world, dt):
        actor = self.actor
        if self.destination is None:
            if world.resource_time < self.escape_retry_at:
                actor.walk_time = 0.0
                return
            self.escape_retry_at = world.resource_time + 0.4
            x, y = actor.x, actor.y
            edges = ((8, y), (MAP_WIDTH - 8, y), (x, 8), (x, MAP_HEIGHT - 8))
            for goal in sorted(edges, key=lambda point: hypot(point[0] - x, point[1] - y)):
                route = world.find_route((x, y), goal, 8)
                if route:
                    self.destination = goal
                    actor.route, actor.route_goal = route, goal
                    break
        if self.destination is None:
            actor.walk_time = 0.0
            return
        actor.follow_route(world, self.destination, dt, 0, speed=190)
        if hypot(actor.x - self.destination[0], actor.y - self.destination[1]) < 0.01:
            actor.state = "escaped"
        elif dt > 0 and not actor.route and not actor.walk_time:
            self.destination = None
            self.escape_retry_at = world.resource_time + 0.4

    def protect(self, world, dt):
        actor = self.actor
        low_health = actor.health <= 15
        detection_range = 160 if low_health else 31
        visible_threats = (
            (distance, npc.entity_id, npc)
            for npc in world.zombies
            if npc.state == "zombie"
            and (distance := hypot(npc.x - actor.x, npc.y - actor.y)) <= detection_range
            and world.pickup_path_clear(actor.x, actor.y, npc.x, npc.y)
        )
        nearest = min(visible_threats, default=None)
        if nearest is None:
            return False
        distance, _, threat = nearest
        if low_health:
            heading = atan2(actor.y - threat.y, actor.x - threat.x)
            candidates = [
                world.move(actor.x, actor.y, cos(heading + turn * tau / 8) * 30,
                           sin(heading + turn * tau / 8) * 30, actor.RADIUS, actor=actor)
                for turn in range(8)
            ]
            x, y = max(candidates, key=lambda point: hypot(point[0] - threat.x, point[1] - threat.y))
            if hypot(x - threat.x, y - threat.y) > distance + 0.01:
                actor.move_toward(world, x, y, dt, 215, 0, steer=False)
                return True
        if distance <= 31:
            actor.start_attack(threat, world.resource_time)
            return True
        actor.walk_time = 0.0
        return True

    def choose_resource(self, world):
        actor = self.actor
        start = (actor.x, actor.y)
        if self.command == "wood":
            self.tool = WOOD_GATHER_TOOL
            points = [(position, *position) for position in world.trees]
        else:
            points = [(pickup_id, x, y) for pickup_id, item, x, y in world.visible_pickups(*start)
                      if item == "stone"]
        for target, x, y in sorted(points, key=lambda entry: hypot(entry[1] - actor.x, entry[2] - actor.y)):
            if target in self.skipped_resources:
                continue
            angle = atan2(actor.y - y, actor.x - x)
            goals = [(x, y)] if self.command == "stone" else [
                (x + cos(angle + turn * pi / 2) * 30, y + sin(angle + turn * pi / 2) * 30)
                for turn in range(4)
            ]
            for goal in goals:
                if self.command == "wood" and not world.pickup_path_clear(
                    *goal, (goal[0] + x) / 2, (goal[1] + y) / 2
                ):
                    continue
                route = world.find_route(start, goal, 8)
                if route and world.pickup_path_clear(*goal, *goal, 8):
                    self.target, self.destination = target, goal
                    self.gather_blocked_at = None
                    actor.route, actor.route_goal = route, goal
                    return True
        return False

    def gather(self, world, dt):
        actor = self.actor
        now = world.resource_time
        wood = self.command == "wood"
        if not self.gather_pending and now < self.gather_until:
            actor.walk_time = 0.0
            return

        if self.target is not None and (
            (wood and self.target not in world.trees)
            or (not wood and self.target not in world.pickups)
        ):
            self.target = None
            self.gather_pending = False
        if self.target is None and not self.choose_resource(world):
            self.gather_shortfall = self.gather_remaining
            self.begin_return()
            return
        if wood:
            x, y = self.target
            end_x, end_y = (self.destination[0] + x) / 2, (self.destination[1] + y) / 2
        else:
            _, x, y, _ = world.pickups[self.target]
            end_x, end_y = x, y

        close = hypot(x - actor.x, y - actor.y) <= GATHER_REACH
        clear = close and world.pickup_path_clear(actor.x, actor.y, end_x, end_y)
        if self.gather_pending and now >= self.gather_until - GATHER_FRAME_TIME - 1e-9:
            self.gather_pending = False
            collected = False
            if clear and wood:
                collected = world.hit_tree(self.target, self.tool, self.inventory)
            elif clear:
                item = world.take_pickup(self.target)
                if item is not None:
                    self.inventory.add(item)
                    collected = True
            if collected:
                self.gather_remaining -= 1
                self.target = None
                if self.gather_remaining == 0:
                    self.begin_return()
                return

        if now < self.gather_until:
            actor.walk_time = 0.0
        elif not clear:
            actor.follow_route(world, self.destination, dt, 0, speed=200)
            if actor.walk_time:
                self.gather_blocked_at = None
            elif dt > 0:
                if self.gather_blocked_at is None:
                    self.gather_blocked_at = now
                elif now - self.gather_blocked_at >= GATHER_ROUTE_TIMEOUT:
                    self.skipped_resources.add(self.target)
                    self.target = None
        elif now >= actor.next_chop:
            actor.walk_time = 0.0
            actor.angle = atan2(y - actor.y, x - actor.x) - pi / 2
            self.gather_pending = True
            self.gather_until = now + GATHER_FRAME_TIME * 2
            actor.next_chop = now + 0.65
        else:
            actor.walk_time = 0.0

    def update(self, world, player, dt):
        actor = self.actor
        if actor.state == "fleeing":
            self.flee(world, dt)
        elif actor.advance_attack(world, player):
            return
        elif self.protect(world, dt):
            self.gather_pending = False
            self.gather_until = 0.0
        elif self.command == "follow":
            target = world.attack_target
            if (target is not None and target.state == "zombie"
                    and world.resource_time - world.attack_target_at <= ASSIST_MEMORY
                    and hypot(actor.x - player.x, actor.y - player.y) <= ASSIST_RANGE
                    and hypot(target.x - player.x, target.y - player.y) <= ASSIST_RANGE):
                self.fight(world, target, dt)
            else:
                actor.follow_route(world, (player.x, player.y), dt, 55, speed=215)
        elif self.command == "attack":
            target = world.actor_by_id(self.target)
            if target is None or target.state != "zombie":
                self.set_command(world, "follow" if self.following else "wait")
            else:
                self.fight(world, target, dt)
        elif self.command in ("wood", "stone"):
            self.gather(world, dt)
        elif self.command == "return":
            self.return_to_origin(world, dt)
        elif world.resource_time >= self.gather_until:
            self.tool = None
            actor.walk_time = 0.0

    def take_gathered(self, player):
        if not self.can_take_gathered():
            return False
        for item, count in tuple(self.inventory.items.items()):
            player.inventory.add(item, count)
            self.inventory.remove(item, count)
        return True

    def begin_return(self):
        self.command = "return"
        self.target = None
        self.destination = self.gather_origin
        self.gather_pending = False
        self.actor.route.clear()
        self.actor.route_goal = None
        self.actor.next_route_at = 0.0

    def return_to_origin(self, world, dt):
        if world.resource_time < self.gather_until:
            return
        actor = self.actor
        actor.follow_route(world, self.destination, dt, 0, speed=215)
        if hypot(actor.x - self.destination[0], actor.y - self.destination[1]) < 0.01:
            shortfall = self.gather_shortfall
            self.set_command(world, "wait")
            self.gather_shortfall = shortfall

    def fight(self, world, target, dt):
        actor = self.actor
        if (hypot(target.x - actor.x, target.y - actor.y) <= 31
                and world.pickup_path_clear(actor.x, actor.y, target.x, target.y)):
            actor.start_attack(target, world.resource_time)
        else:
            actor.follow_route(world, (target.x, target.y), dt, 27, speed=215)

    def can_take_gathered(self):
        return self.command not in ("wood", "stone", "return") and bool(self.inventory.items)
