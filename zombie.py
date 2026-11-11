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

    def set_command(self, world, command):
        self.command_target = world.attack_target if command == "attack" else None
        self.command = command

    def update_ally(self, world, player, dt):
        if self.command == "follow":
            self.move_toward(world, player.x, player.y, dt, 215, 55)
        elif self.command == "attack":
            target = self.command_target
            if target is None or target.state != "zombie":
                self.set_command(world, "wait")
            elif hypot(target.x - self.x, target.y - self.y) > 31:
                self.move_toward(world, target.x, target.y, dt, 215, 27)
                return
            elif world.pickup_path_clear(self.x, self.y, target.x, target.y):
                if world.resource_time >= self.next_hit:
                    world.hit_zombie(target, 5)
                    self.next_hit = world.resource_time + 2
                    self.attack_until = world.resource_time + 0.24
            self.walk_time = 0.0
        elif self.command in ("wood", "stone"):
            self.gather(world, player, dt)
        else:
            self.walk_time = 0.0
            if self.health > 15:
                return
            threat = min((z for z in world.zombies if z.state == "zombie"),
                         key=lambda z: hypot(z.x - self.x, z.y - self.y), default=None)
            if threat is not None and hypot(threat.x - self.x, threat.y - self.y) < 160:
                self.move_toward(world, self.x * 2 - threat.x, self.y * 2 - threat.y, dt, 215, 0)

    def gather(self, world, player, dt):
        pass
