from math import atan2, hypot, pi

from human_npc import HumanNPC


SIGHT_RANGE = 280
SIGHT_MEMORY = 5.0
CHASE_RADIUS = 8
ROUTE_RETRY = 0.4
ATTACK_FRAME_TIME = 0.12
ATTACK_REACH = 31
NPC_ATTACK_DAMAGE = 5
NPC_ATTACK_INTERVAL = 2


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
        self.attack_until = 0.0
        self.attack_target = None
        self.hurt_until = 0.0
        self.human = None
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
            self.human = HumanNPC(self)
            self.next_hit = world.resource_time
            self.hurt_until = 0.0
            self.human.set_command(world, "wait")
        if self.human is not None:
            self.human.update(world, player, dt)
        else:
            self.hunt(world, player, dt)

    def set_command(self, world, command):
        if self.state == "ally":
            self.human.set_command(world, command)

    def follow_route(self, world, goal, dt, stop, speed=None):
        speed = self.speed if speed is None else speed
        start = (self.x, self.y)
        if world.pickup_path_clear(*start, *goal, CHASE_RADIUS):
            self.route.clear()
            self.route_goal = None
            self.move_toward(world, *goal, dt, speed, stop)
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
        self.move_toward(world, *waypoint, dt, speed, 0)
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
        if self.advance_attack(world, player):
            return
        target = self.see_target(world, player)
        if target is not None:
            self.last_seen = (target.x, target.y)
            self.seen_until = world.resource_time + SIGHT_MEMORY
            if hypot(target.x - self.x, target.y - self.y) <= ATTACK_REACH:
                self.start_attack(target, world.resource_time)
                return
            self.follow_route(world, self.last_seen, dt, 27)
        elif (self.last_seen is not None and world.resource_time < self.seen_until
              and hypot(self.last_seen[0] - self.x, self.last_seen[1] - self.y) > 3):
            self.follow_route(world, self.last_seen, dt, 0)
        else:
            self.last_seen = None
            self.route.clear()
            self.route_goal = None
            self.walk_time = 0.0

    def start_attack(self, target, now):
        self.walk_time = 0.0
        self.angle = atan2(target.y - self.y, target.x - self.x) - pi / 2
        if now >= self.next_hit:
            self.attack_target = target
            self.attack_until = now + ATTACK_FRAME_TIME * 3
            self.next_hit = now + NPC_ATTACK_INTERVAL

    def advance_attack(self, world, player):
        now = world.resource_time
        target = self.attack_target
        if target is not None and now >= self.attack_until - ATTACK_FRAME_TIME * 2 - 1e-9:
            self.attack_target = None
            valid = (target.state == "zombie" if self.state == "ally"
                     else target is player or target.state in ("ally", "fleeing"))
            if (valid and target.health > 0
                    and hypot(target.x - self.x, target.y - self.y) <= ATTACK_REACH
                    and world.pickup_path_clear(self.x, self.y, target.x, target.y)):
                self.next_hit = now + NPC_ATTACK_INTERVAL
                if target is player:
                    player.take_damage(NPC_ATTACK_DAMAGE, now)
                elif target.state == "zombie":
                    world.hit_zombie(target, NPC_ATTACK_DAMAGE)
                else:
                    target.health = max(0, target.health - NPC_ATTACK_DAMAGE)
                    if target.health == 0:
                        target.state = "dead"
                    else:
                        target.hurt_until = now + 0.16
        return now < self.attack_until
