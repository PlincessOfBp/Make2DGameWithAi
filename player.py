from math import atan2, cos, expm1, hypot, pi, sin, tau

from inventory import Inventory
from item_data import WEAPON_COLUMNS


class Player:
    SPEED = 220
    RADIUS = 8
    TURN_RESPONSE = 14
    WALK_FPS = 10

    def __init__(self):
        self.x, self.y = 250, 1360
        self.angle = self.target_angle = 0.0
        self.walk_time = 0.0
        self.inventory = Inventory()
        self.items = self.inventory.items
        self.health = 100
        self.infection = 0.0
        self.action = None
        self.action_elapsed = 0.0
        self.action_angle = 0.0
        self.action_weapon = None

    def move(self, world, horizontal, vertical, dt):
        length = hypot(horizontal, vertical)
        if not length:
            self.walk_time = 0.0
            return
        distance = self.SPEED * dt / length
        x, y = world.move(self.x, self.y, horizontal * distance, vertical * distance, self.RADIUS)
        self.walk_time = self.walk_time + dt if (x, y) != (self.x, self.y) else 0.0
        self.x, self.y = x, y

    def aim(self, world_x, world_y, dt):
        dx, dy = world_x - self.x, world_y - self.y
        if dx or dy:
            self.target_angle = atan2(dy, dx) - pi / 2
        difference = (self.target_angle - self.angle + pi) % tau - pi
        self.angle = (self.angle + difference * -expm1(-self.TURN_RESPONSE * dt)) % tau
