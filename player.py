from math import atan2, expm1, hypot, pi, tau


class Player:
    SPEED = 220
    RADIUS = 8
    TURN_RESPONSE = 14
    WALK_FPS = 10

    def __init__(self):
        self.x, self.y = 250, 1360
        self.angle = self.target_angle = 0.0
        self.walk_time = 0.0

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
        pass
