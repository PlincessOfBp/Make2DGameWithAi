from math import atan2, cos, hypot, pi, sin

from human_npc import HumanNPC


SIGHT_RANGE = 280
SIGHT_MEMORY = 5.0
CHASE_RADIUS = 8
ROUTE_RETRY = 0.4
ATTACK_FRAME_TIME = 0.12
ATTACK_REACH = 31
ZOMBIE_ATTACK_DAMAGE = 10
ALLY_ATTACK_DAMAGE = 5
NPC_ATTACK_INTERVAL = 2


class Zombie:
    RADIUS = CHASE_RADIUS

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
        self.avoid_side = -1 if entity_id % 2 else 1
        self.wander_goal = None
        self.wander_at = 2.0 + entity_id % 7

    def move_toward(self, world, x, y, dt, speed, stop, steer=True):
        dx, dy = x - self.x, y - self.y
        distance = hypot(dx, dy)
        if distance <= stop:
            self.walk_time = 0.0
            return
        heading = atan2(dy, dx)
        travel = min(speed * dt, distance - stop)
        step = travel / distance
        position = world.move(self.x, self.y, dx * step, dy * step, self.RADIUS, actor=self)
        forward = ((position[0] - self.x) * dx + (position[1] - self.y) * dy) / distance
        if steer and travel and forward < travel * 0.25:
            wall_only = world.move(self.x, self.y, dx * step, dy * step, self.RADIUS)
            if wall_only != position:
                # Keep one side while passing the body instead of changing sides every frame.
                for side in (self.avoid_side, -self.avoid_side):
                    angle = heading + side * pi / 2
                    candidate = world.move(self.x, self.y, cos(angle) * travel, sin(angle) * travel,
                                           self.RADIUS, actor=self)
                    lateral = ((candidate[1] - self.y) * dx - (candidate[0] - self.x) * dy) / distance
                    if lateral * side > travel * 0.25:
                        position = candidate
                        self.avoid_side = side
                        break
        moved = position != (self.x, self.y)
        self.angle = (atan2(position[1] - self.y, position[0] - self.x) if moved else heading) - pi / 2
        self.walk_time = self.walk_time + dt if moved else 0.0
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

    def set_command(self, world, command, amount=1):
        if self.state == "ally":
            self.human.set_command(world, command, amount)

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
            self.wander_goal = None
            self.wander_at = world.resource_time + 3
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
            if self.last_seen is not None:
                self.last_seen = None
                self.route.clear()
                self.route_goal = None
            self.wander(world, dt)

    def wander(self, world, dt):
        now = world.resource_time
        if self.wander_goal is None:
            self.walk_time = 0.0
            if now < self.wander_at:
                return
            self.wander_at = now + world.random.uniform(3, 7)
            start = (self.x, self.y)
            room = world.building_at(*start)
            for _ in range(8):
                angle = world.random.uniform(0, 2 * pi)
                distance = world.random.uniform(30, 85)
                goal = world.move(*start, cos(angle) * distance, sin(angle) * distance, self.RADIUS)
                if (hypot(goal[0] - self.x, goal[1] - self.y) >= 24
                        and world.building_at(*goal) == room
                        and world.pickup_path_clear(*start, *goal, self.RADIUS)):
                    self.wander_goal = goal
                    break
        if self.wander_goal is not None:
            self.move_toward(world, *self.wander_goal, dt, 48, 0, steer=False)
            if dt > 0 and (not self.walk_time or hypot(
                self.x - self.wander_goal[0], self.y - self.wander_goal[1]
            ) < 0.01):
                self.wander_goal = None

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
                    player.take_damage(ZOMBIE_ATTACK_DAMAGE, now)
                elif target.state == "zombie":
                    world.hit_zombie(target, ALLY_ATTACK_DAMAGE)
                else:
                    target.health = max(0, target.health - ZOMBIE_ATTACK_DAMAGE)
                    if target.health == 0:
                        target.state = "dead"
                    else:
                        target.hurt_until = now + 0.16
        return now < self.attack_until
