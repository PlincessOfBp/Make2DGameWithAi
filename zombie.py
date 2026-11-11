from math import atan2, hypot, pi

from item_data import TREE_DAMAGE


SIGHT_RANGE = 280
SIGHT_MEMORY = 5.0
CHASE_RADIUS = 8
ROUTE_RETRY = 0.4


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
        self.next_chop = 0.0
        self.purify_at = None
        self.command = "wait"
        self.command_target = None
        self.attack_until = 0.0
        self.hurt_until = 0.0
        self.human = False
        self.last_seen = None
        self.seen_until = 0.0
        self.route = []
        self.route_goal = None
        self.next_route_at = 0.0

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
            self.human = True
            self.next_hit = world.resource_time
        if self.state == "fleeing":
            edge = 8 if self.x < 1200 else 2392
            self.move_toward(world, edge, self.y, dt, 190, 0)
            if self.x == edge:
                self.state = "escaped"
        elif self.state == "ally":
            self.update_ally(world, player, dt)
        else:
            targets = [player, *(z for z in world.zombies if z.state in ("ally", "fleeing"))]
            target = min(targets, key=lambda actor: hypot(actor.x - self.x, actor.y - self.y))
            distance = hypot(target.x - self.x, target.y - self.y)
            if distance <= 31 and world.pickup_path_clear(self.x, self.y, target.x, target.y):
                self.walk_time = 0.0
                self.angle = atan2(target.y - self.y, target.x - self.x) - pi / 2
                if world.resource_time >= self.next_hit:
                    if target is player:
                        player.take_damage(5, world.resource_time)
                    else:
                        target.health = max(0, target.health - 5)
                    if target is not player:
                        if target.health == 0:
                            target.state = "dead"
                        else:
                            target.hurt_until = world.resource_time + 0.16
                    self.next_hit = world.resource_time + 2
                    self.attack_until = world.resource_time + 0.24
            elif distance <= 280:
                self.move_toward(world, target.x, target.y, dt, self.speed, 27)
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
        if self.command == "wood":
            tool = max((item for item in TREE_DAMAGE if player.items.get(item, 0)),
                       key=TREE_DAMAGE.get, default=None)
            targets = world.trees if tool is not None else ()
            if self.command_target is not None and self.command_target not in targets:
                self.set_command(world, "wait")
                self.walk_time = 0.0
                return
        else:
            targets = [(x, y) for _, item, x, y in world.visible_pickups(self.x, self.y)
                       if item == "stone"]
        if self.command_target not in targets:
            self.command_target = min(targets, key=lambda t: hypot(t[0] - self.x, t[1] - self.y),
                                      default=None)
        if self.command_target is None:
            self.set_command(world, "wait")
            return
        x, y = self.command_target
        distance = hypot(x - self.x, y - self.y)
        if distance > 250:
            self.set_command(world, "wait")
        elif distance > 35:
            self.move_toward(world, x, y, dt, 200, 32)
            if not self.walk_time:
                self.set_command(world, "wait")
            return
        elif self.command == "wood":
            if distance and not world.pickup_path_clear(
                self.x, self.y, x - (x - self.x) * 15 / distance, y - (y - self.y) * 15 / distance
            ):
                self.set_command(world, "wait")
            elif world.resource_time >= self.next_chop:
                self.next_chop = world.resource_time + 0.65
                if world.hit_tree((x, y), tool):
                    self.set_command(world, "wait")
        else:
            item = world.collect_pickup(self.x, self.y, x, y)
            if item is not None:
                player.inventory.add(item)
            self.set_command(world, "wait")
        self.walk_time = 0.0

    def follow_route(self, world, goal, dt, stop):
        start = (self.x, self.y)
        if world.pickup_path_clear(*start, *goal, CHASE_RADIUS):
            self.route.clear()
            self.route_goal = None
            self.move_toward(world, *goal, dt, self.speed, stop)
            return

        if self.route and not world.pickup_path_clear(*start, *self.route[0], CHASE_RADIUS):
            self.route.clear()
        goal_changed = self.route_goal is None or hypot(
            goal[0] - self.route_goal[0], goal[1] - self.route_goal[1]
        ) > 24
        if (not self.route or goal_changed) and world.resource_time >= self.next_route_at:
            self.route = world.find_route(start, goal, CHASE_RADIUS)
            self.route_goal = goal
            self.next_route_at = world.resource_time + ROUTE_RETRY
        if not self.route:
            self.walk_time = 0.0
            return
        waypoint = self.route[0]
        self.move_toward(world, *waypoint, dt, self.speed, 0)
        if hypot(self.x - waypoint[0], self.y - waypoint[1]) < 0.01:
            self.route.pop(0)

    def see_target(self, world, player):
        humans = (actor for actor in world.zombies if actor.state in ("ally", "fleeing"))
        nearest = None
        distance = SIGHT_RANGE
        for actor in (player, *humans):
            if actor.health <= 0:
                continue
            candidate_distance = hypot(actor.x - self.x, actor.y - self.y)
            if candidate_distance <= distance and world.pickup_path_clear(self.x, self.y, actor.x, actor.y):
                nearest, distance = actor, candidate_distance
        return nearest

    def hunt(self, world, player, dt):
        pass
