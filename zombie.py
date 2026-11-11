from math import atan2, hypot, pi


class Zombie:
    def __init__(self, entity_id, x, y):
        self.entity_id = entity_id
        self.x, self.y = x, y
        self.health = 50
        self.state = "zombie"
        self.speed = (185, 220, 245)[entity_id % 3]
        self.variant = entity_id % 3 + 1
        self.angle = 0.0
        self.walk_time = 0.0
        self.next_hit = 0.0
        self.purify_at = None
        self.command = "wait"

    def move_toward(self, world, x, y, dt, speed, stop):
        pass
