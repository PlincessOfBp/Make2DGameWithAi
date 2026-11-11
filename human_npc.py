from math import atan2, cos, hypot, pi, sin, tau

from inventory import Inventory
from item_data import TREE_DAMAGE
from town import MAP_HEIGHT, MAP_WIDTH


GATHER_FRAME_TIME = 0.15
GATHER_REACH = 35
GATHER_LIMIT = 20
ASSIST_RANGE = 220
ASSIST_MEMORY = 5.0


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

    def set_command(self, world, command):
        self.command = command
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
        if actor.health > 15:
            actor.walk_time = 0.0
            return
        threat = min((npc for npc in world.zombies if npc.state == "zombie"),
                     key=lambda npc: hypot(npc.x - actor.x, npc.y - actor.y), default=None)
        if threat is None or hypot(threat.x - actor.x, threat.y - actor.y) >= 160:
            actor.walk_time = 0.0
            return
        heading = atan2(actor.y - threat.y, actor.x - threat.x)
        candidates = [
            world.move(actor.x, actor.y, cos(heading + turn * tau / 8) * 30,
                       sin(heading + turn * tau / 8) * 30, 8)
            for turn in range(8)
        ]
        x, y = max(candidates, key=lambda point: hypot(point[0] - threat.x, point[1] - threat.y))
        if hypot(x - threat.x, y - threat.y) > hypot(actor.x - threat.x, actor.y - threat.y):
            actor.move_toward(world, x, y, dt, 215, 0)
        else:
            actor.walk_time = 0.0

    def choose_resource(self, world, player):
        actor = self.actor
        start = (actor.x, actor.y)
        if self.command == "wood":
            self.tool = max((item for item in TREE_DAMAGE if player.items.get(item, 0)),
                            key=TREE_DAMAGE.get, default=None)
            points = [(position, *position) for position in world.trees] if self.tool else []
        else:
            points = [(pickup_id, x, y) for pickup_id, item, x, y in world.visible_pickups(*start)
                      if item == "stone"]
        for target, x, y in sorted(points, key=lambda entry: hypot(entry[1] - actor.x, entry[2] - actor.y)):
            if hypot(x - actor.x, y - actor.y) > GATHER_RANGE:
                break
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
                    actor.route, actor.route_goal = route, goal
                    return True
        return False

    def gather(self, world, player, dt):
        actor = self.actor
        if self.target is None and not self.choose_resource(world, player):
            self.set_command(world, "wait")
            return
        wood = self.command == "wood"
        if wood:
            if self.target not in world.trees or self.tool not in player.items:
                self.set_command(world, "wait")
                return
            x, y = self.target
            end_x, end_y = (self.destination[0] + x) / 2, (self.destination[1] + y) / 2
        else:
            pickup = world.pickups.get(self.target)
            if pickup is None:
                self.set_command(world, "wait")
                return
            _, x, y, _ = pickup
            end_x, end_y = x, y
        close = hypot(x - actor.x, y - actor.y) <= GATHER_REACH
        clear = close and world.pickup_path_clear(actor.x, actor.y, end_x, end_y)
        now = world.resource_time
        if self.gather_pending and now >= self.gather_until - GATHER_FRAME_TIME - 1e-9:
            self.gather_pending = False
            if clear:
                if wood:
                    if world.hit_tree(self.target, self.tool):
                        self.target = None
                        self.command = "wait"
                else:
                    item = world.take_pickup(self.target)
                    if item is not None:
                        player.inventory.add(item)
                    self.target = None
                    self.command = "wait"
        if now < self.gather_until:
            actor.walk_time = 0.0
        elif not clear:
            actor.follow_route(world, self.destination, dt, 0, speed=200)
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
        elif self.command == "follow":
            actor.follow_route(world, (player.x, player.y), dt, 55, speed=215)
        elif self.command == "attack":
            target = world.actor_by_id(self.target)
            if target is None or target.state != "zombie":
                self.set_command(world, "wait")
            elif (hypot(target.x - actor.x, target.y - actor.y) <= 31
                  and world.pickup_path_clear(actor.x, actor.y, target.x, target.y)):
                actor.start_attack(target, world.resource_time)
            else:
                actor.follow_route(world, (target.x, target.y), dt, 27, speed=215)
        elif self.command in ("wood", "stone"):
            self.gather(world, player, dt)
        elif world.resource_time >= self.gather_until:
            self.tool = None
            self.protect(world, dt)
