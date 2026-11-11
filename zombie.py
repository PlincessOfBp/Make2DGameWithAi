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
        self.command_target = None
        self.attack_until = 0.0
        self.human = False

    def move_toward(self, world, x, y, dt, speed, stop):
        dx, dy = x - self.x, y - self.y
        distance = hypot(dx, dy)
        if distance <= stop:
            self.walk_time = 0.0
            return
        self.angle = atan2(dy, dx) - pi / 2
        step = min(speed * dt, distance - stop) / distance
        position = world.move(self.x, self.y, dx * step, dy * step, 8)
        self.walk_time = self.walk_time + dt if position != (self.x, self.y) else 0.0
        self.x, self.y = position

    def update(self, world, player, dt):
        if self.state in ("dead", "escaped"):
            return
        if self.purify_at is not None and world.resource_time >= self.purify_at:
            self.purify_at = None
            self.state = "ally" if world.random.random() < 0.5 else "fleeing"
            self.health = 50
        if self.state == "fleeing":
            edge = 8 if self.x < 1200 else 2392
            self.move_toward(world, edge, self.y, dt, 190, 0)
            if self.x == edge:
                self.state = "escaped"
        elif self.state == "ally":
            if self.command == "follow":
                self.move_toward(world, player.x, player.y, dt, 215, 55)
            else:
                self.walk_time = 0.0
        else:
            distance = hypot(player.x - self.x, player.y - self.y)
            if distance <= 31 and world.pickup_path_clear(self.x, self.y, player.x, player.y):
                self.walk_time = 0.0
                if world.resource_time >= self.next_hit:
                    player.health = max(0, player.health - 5)
                    self.next_hit = world.resource_time + 2
            elif distance <= 280:
                self.move_toward(world, player.x, player.y, dt, self.speed, 27)
            else:
                self.walk_time = 0.0
