from pathlib import Path
import subprocess
import sys


def git(*args):
    subprocess.run(["git", *args], check=True)


def edit(name, old, new, title, check=""):
    path = Path(name)
    source = path.read_text(encoding="utf-8")
    assert old in source, (name, old)
    source = source.replace(old, new, 1)
    if name.endswith(".py"):
        compile(source, name, "exec")
    path.write_text(source, encoding="utf-8")
    if check:
        subprocess.run([sys.executable, "-B", "-c", check], check=True)
    git("add", "--", name)
    git("diff", "--cached", "--check")
    git("--no-pager", "diff", "--cached", "--", name)
    git("commit", "-m", title)
    git("log", "-1", "--oneline")


def method(name, signature, body, title, check):
    anchor = "".join(Path(name).read_text(encoding="utf-8").splitlines(keepends=True)[-2:])
    stub = signature + "\n        pass\n"
    edit(name, anchor, anchor + "\n" + stub, signature.split("(")[0].strip()[4:] + " 메서드 선언")
    edit(name, stub, signature + "\n" + body.strip("\n") + "\n", title, check)


git("add", "--", "zombie.py")
git("diff", "--cached", "--check")
git("--no-pager", "diff", "--cached", "--", "zombie.py")
git("commit", "-m", "좀비가 직접 갈 수 없을 때 우회 지점을 순서대로 따라가도록 구현")
git("log", "-1", "--oneline")
method("zombie.py", "    def see_target(self, world, player):", """
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
""", "시야 범위와 벽을 검사해 보이는 인간만 추적 대상으로 선택",
"from world import World; from player import Player; from zombie import Zombie; w=World(); p=Player(); z=Zombie(0,100,110); p.x,p.y=160,110; w.walls=[(120,95,140,125)]; assert z.see_target(w,p) is None; p.y=210; assert z.see_target(w,p) is p")
method("zombie.py", "    def hunt(self, world, player, dt):", """
        target = self.see_target(world, player)
        if target is not None:
            self.last_seen = (target.x, target.y)
            self.seen_until = world.resource_time + SIGHT_MEMORY
            if hypot(target.x - self.x, target.y - self.y) <= 31:
                self.walk_time = 0.0
                self.angle = atan2(target.y - self.y, target.x - self.x) - pi / 2
                if world.resource_time >= self.next_hit:
                    if target is player:
                        player.take_damage(5, world.resource_time)
                    else:
                        target.health = max(0, target.health - 5)
                        if target.health == 0:
                            target.state = "dead"
                        else:
                            target.hurt_until = world.resource_time + 0.16
                    self.next_hit = world.resource_time + 2
                    self.attack_until = world.resource_time + 0.24
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
""", "시야를 잃으면 마지막 목격 지점까지만 추적하고 재발견 시 추적 재개",
"from world import World; from player import Player; from zombie import Zombie; w=World(); p=Player(); z=Zombie(0,100,110); p.x,p.y=160,110; w.walls=[(120,95,140,125)]; z.hunt(w,p,.1); assert (z.x,z.y)==(100,110); p.y=210; z.hunt(w,p,.01); assert z.last_seen==(160,210); p.y=110; z.hunt(w,p,.1); assert z.last_seen==(160,210) and p.health==100; w.resource_time=6; z.hunt(w,p,.1); assert z.last_seen is None")

source = Path("zombie.py").read_text(encoding="utf-8")
start = source.index('        else:\n            targets = [player')
end = source.index('\n    def set_command', start)
edit("zombie.py", source[start:end], """        else:
            self.hunt(world, player, dt)
""", "좀비 월드 갱신에 시야 제한과 장애물 우회 연결",
"from world import World; from player import Player; from zombie import Zombie; w=World(); p=Player(); p.x,p.y=160,110; z=Zombie(0,100,110); w.walls=[(120,95,140,125)]; z.update(w,p,.1); assert (z.x,z.y)==(100,110); w.walls=[]; z.update(w,p,.1); assert z.x>100 and z.last_seen==(160,110)")
