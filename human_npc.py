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
