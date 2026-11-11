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
        pass
