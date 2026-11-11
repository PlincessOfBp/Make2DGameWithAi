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
        self.hurt_until = 0.0
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

    def start_action(self, action, target_x, target_y):
        if self.action is not None:
            return False
        dx, dy = target_x - self.x, target_y - self.y
        self.action_angle = atan2(dy, dx) - pi / 2 if dx or dy else self.target_angle
        selected = self.inventory.slots[self.inventory.selected]
        self.action_weapon = selected if action == "attack" and selected in WEAPON_COLUMNS else None
        self.action = action
        self.action_elapsed = 0.0
        return True

    def update_action(self, world, dt):
        self.infection = max(0.0, self.infection - dt * (2 / 60))
        if self.action is None:
            return
        previous = self.action_elapsed
        self.action_elapsed += dt
        if previous < 0.12 <= self.action_elapsed:
            world.resolve_player_action(self, self.action, self.action_angle, self.action_weapon)
        if self.action_elapsed >= 0.36:
            self.action = None

    def use_selected(self, world):
        item = self.inventory.slots[self.inventory.selected]
        if item == "canned_food" and (self.health < 100 or self.infection > 0):
            self.health = min(100, self.health + 30)
            self.infection = max(0, self.infection - 20)
        elif item == "barricade":
            x = round(self.x - sin(self.target_angle) * 64)
            y = round(self.y + cos(self.target_angle) * 64)
            if not world.place_barricade(self, x, y):
                return False
        else:
            return False
        self.inventory.remove(item)
        return True

    def take_damage(self, damage, now):
        self.health = max(0, self.health - damage)
        self.hurt_until = now + 0.16 if self.health else 0.0

    def drop_selected(self, world):
        item = self.inventory.slots[self.inventory.selected]
        if item is None or not world.drop_item(self, item):
            return False
        self.inventory.remove(item)
        return True
