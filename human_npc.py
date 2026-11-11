from math import atan2, cos, hypot, pi, sin, tau

from item_data import TREE_DAMAGE
from town import MAP_HEIGHT, MAP_WIDTH


GATHER_FRAME_TIME = 0.15
GATHER_REACH = 35
GATHER_RANGE = 250


class HumanNPC:
    def __init__(self, actor):
        self.actor = actor
        self.command = "wait"
        self.target = None
        self.destination = None
        self.gather_until = 0.0
        self.gather_pending = False
        self.tool = None

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
        elif not actor.route and not actor.walk_time and world.resource_time >= actor.next_route_at:
            self.destination = None

    def protect(self, world, dt):
        actor = self.actor
        actor.walk_time = 0.0
        if actor.health > 15:
            return
        threat = min((npc for npc in world.zombies if npc.state == "zombie"),
                     key=lambda npc: hypot(npc.x - actor.x, npc.y - actor.y), default=None)
        if threat is None or hypot(threat.x - actor.x, threat.y - actor.y) >= 160:
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

    def choose_resource(self, world, player):
        pass
