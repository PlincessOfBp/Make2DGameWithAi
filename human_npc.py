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
        pass
