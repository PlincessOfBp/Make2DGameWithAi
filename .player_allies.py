from pathlib import Path
import ast
import subprocess
import sys


def git(*args):
    subprocess.run(["git", *args], check=True)


def save(name, source, title, check=""):
    git("status", "--short", "--", name)
    if name.endswith(".py"):
        compile(source, name, "exec")
    Path(name).write_text(source, encoding="utf-8")
    if check:
        subprocess.run([sys.executable, "-B", "-c", check], check=True)
    git("add", "--", name)
    git("diff", "--cached", "--check")
    git("--no-pager", "diff", "--cached", "--", name)
    git("commit", "-m", title)
    git("log", "-1", "--oneline")


def edit(name, old, new, title, check=""):
    source = Path(name).read_text(encoding="utf-8")
    assert old in source, old
    save(name, source.replace(old, new, 1), title, check)


def method(name, signature, body, title, check=""):
    source = Path(name).read_text(encoding="utf-8")
    stub = signature + "\n        pass\n"
    save(name, source.rstrip() + "\n\n" + stub, signature.split("(")[0].strip()[4:] + " 메서드 선언")
    edit(name, stub, signature + "\n" + body.strip("\n") + "\n", title, check)


def skeleton(name, imports, cls):
    save(name, imports + f"\n\nclass {cls}:\n    pass\n", cls + " 클래스 뼈대 추가")


def first_method(name, signature, body, title, check=""):
    source = Path(name).read_text(encoding="utf-8")
    save(name, source.rsplit("    pass", 1)[0] + signature + "\n        pass\n", signature.strip()[4:].split("(")[0] + " 메서드 선언")
    edit(name, signature + "\n        pass", signature + "\n" + body.strip("\n"), title, check)


edit("world.py", "        self.barricades = []", """        self.barricades = []
        self.attack_target = None""", "조력자 공동 공격용 플레이어의 적중 대상 기록 준비")
method("world.py", "    def hit_zombie(self, zombie, damage):", """
        if zombie.state != "zombie":
            return
        zombie.health = max(0, zombie.health - damage)
        if zombie.health:
            return
        zombie.state = "dead"
        zombie.purify_at = None
        if self.random.random() < 0.35:
            item = self.random.choice(("axe", "knife", "canned_food"))
            self.pickups[f"zombie:{zombie.entity_id}"] = (
                item, zombie.x, zombie.y, self.building_at(zombie.x, zombie.y),
            )
""", "플레이어와 조력자가 공유하는 좀비 피해 및 단일 드롭 처리",
"from world import World; w=World(); z=w.zombies[0]; w.random.seed(1); w.hit_zombie(z,50); before=w.pickups.copy(); w.hit_zombie(z,50); assert z.state=='dead' and w.pickups==before and 'zombie:0' in before")
edit("world.py", """            zombie.health = max(0, zombie.health - WEAPON_DAMAGE[weapon])
            if zombie.health == 0:
                zombie.state = "dead"
                zombie.purify_at = None
                if self.random.random() < 0.35:
                    item = self.random.choice(("axe", "knife", "canned_food"))
                    self.pickups[f"zombie:{zombie.entity_id}"] = (
                        item, zombie.x, zombie.y, self.building_at(zombie.x, zombie.y),
                    )""", """            self.attack_target = zombie
            self.hit_zombie(zombie, WEAPON_DAMAGE[weapon])""", "플레이어 공격을 공통 피해 판정에 연결하고 대상 저장")

method("world.py", "    def harvest_tree(self, player, position):", """
        if position not in self.trees:
            return False
        self.trees.remove(position)
        self.walls.remove(self.tree_walls[position])
        self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
        player.inventory.add("wood")
        return True
""", "채집한 가로수를 제거하고 재생성 예약 및 나무 지급",
"from world import World; from player import Player; w=World(); p=Player(); t=w.trees[0]; assert w.harvest_tree(p,t) and not w.harvest_tree(p,t) and p.items=={'wood':1}")
edit("world.py", """            self.trees.remove(position)
            self.walls.remove(self.tree_walls[position])
            self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
            player.inventory.add("wood")""", """            self.harvest_tree(player, position)""", "플레이어 도끼 공격을 공통 채집 처리에 연결")
method("world.py", "    def ally_at(self, player, x, y):", """
        candidates = [z for z in self.zombies if z.state == "ally"
                      and hypot(z.x - x, z.y - y) <= 23
                      and hypot(z.x - player.x, z.y - player.y) <= 90
                      and self.pickup_path_clear(player.x, player.y, z.x, z.y)]
        return min(candidates, key=lambda z: hypot(z.x - x, z.y - y), default=None)
""", "우클릭 위치와 상호작용 범위에 맞는 조력자 조회",
"from world import World; from player import Player; w=World(); p=Player(); z=w.zombies[0]; z.state='ally'; z.x,z.y=285,1360; assert w.ally_at(p,285,1360) is z and w.ally_at(p,600,1200) is None")

edit("zombie.py", '        self.command = "wait"', """        self.command = "wait"
        self.command_target = None
        self.attack_until = 0.0
        self.human = False""", "회복된 조력자 명령 대상과 공격 표시 상태 초기화")
method("zombie.py", "    def set_command(self, world, command):", """
        self.command_target = world.attack_target if command == "attack" else None
        self.command = command
""", "조력자 명령에 현재 플레이어 공격 대상 저장",
"from world import World; from zombie import Zombie; w=World(); z=Zombie(1,0,0); w.attack_target=w.zombies[0]; z.set_command(w,'attack'); assert z.command_target is w.attack_target")
method("zombie.py", "    def update_ally(self, world, player, dt):", """
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
""", "조력자의 따라가기·공동 공격·저체력 자기보호 동작 구현",
"from world import World; from player import Player; w=World(); p=Player(); a,z=w.zombies[:2]; a.state='ally'; a.x,a.y=250,1360; z.x,z.y=279,1360; w.attack_target=z; a.set_command(w,'attack'); a.update_ally(w,p,0); a.update_ally(w,p,0); assert z.health==45")
method("zombie.py", "    def gather(self, world, player, dt):", """
        if self.command == "wood":
            has_axe = any(player.items.get(item, 0) for item in ("axe", "stone_axe"))
            targets = world.trees if has_axe else ()
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
            if distance == 0 or world.pickup_path_clear(
                self.x, self.y, x - (x - self.x) * 15 / distance, y - (y - self.y) * 15 / distance
            ):
                world.harvest_tree(player, (x, y))
            self.set_command(world, "wait")
        else:
            item = world.collect_pickup(self.x, self.y, x, y)
            if item is not None:
                player.inventory.add(item)
            self.set_command(world, "wait")
        self.walk_time = 0.0
""", "조력자가 지정 자원을 찾아 채집하고 보상을 플레이어에게 지급",
"from world import World; from player import Player; w=World(); p=Player(); a=w.zombies[0]; a.state='ally'; a.x,a.y=280,1350; a.set_command(w,'stone'); a.gather(w,p,.1); assert p.items=={'stone':1} and a.command=='wait'")
edit("zombie.py", """            self.health = 50
        if self.state == "fleeing":""", """            self.health = 50
            self.human = True
            self.next_hit = world.resource_time
        if self.state == "fleeing":""", "정화 전환 시 인간 외형과 공격 시각 초기화")
edit("zombie.py", """            if self.command == "follow":
                self.move_toward(world, player.x, player.y, dt, 215, 55)
            else:
                self.walk_time = 0.0""", """            self.update_ally(world, player, dt)""", "회복 조력자의 명령 행동을 NPC 갱신에 연결")
edit("zombie.py", """            distance = hypot(player.x - self.x, player.y - self.y)
            if distance <= 31 and world.pickup_path_clear(self.x, self.y, player.x, player.y):
                self.walk_time = 0.0
                if world.resource_time >= self.next_hit:
                    player.health = max(0, player.health - 5)
                    self.next_hit = world.resource_time + 2
            elif distance <= 280:
                self.move_toward(world, player.x, player.y, dt, self.speed, 27)""", """            targets = [player, *(z for z in world.zombies if z.state in ("ally", "fleeing"))]
            target = min(targets, key=lambda actor: hypot(actor.x - self.x, actor.y - self.y))
            distance = hypot(target.x - self.x, target.y - self.y)
            if distance <= 31 and world.pickup_path_clear(self.x, self.y, target.x, target.y):
                self.walk_time = 0.0
                self.angle = atan2(target.y - self.y, target.x - self.x) - pi / 2
                if world.resource_time >= self.next_hit:
                    target.health = max(0, target.health - 5)
                    if target is not player and target.health == 0:
                        target.state = "dead"
                    self.next_hit = world.resource_time + 2
                    self.attack_until = world.resource_time + 0.24
            elif distance <= 280:
                self.move_toward(world, target.x, target.y, dt, self.speed, 27)""", "좀비가 가까운 인간을 공격하도록 연결하고 공격 상태 표시",
"from world import World; from player import Player; w=World(); p=Player(); z,a=w.zombies[:2]; z.x,z.y=420,1350; a.x,a.y=440,1350; a.state='ally'; a.health=5; z.update(w,p,0); assert a.state=='dead' and p.health==100")
edit("player_ui.py", "UI_ASSETS = (", """ALLY_COMMANDS = (
    ("wait", "대기"), ("follow", "따라가기"), ("attack", "공동 공격"), ("gather", "채집"),
)
GATHER_COMMANDS = (("wood", "나무"), ("stone", "돌멩이"), ("back", "뒤로"))
ALLY_LEFT, ALLY_TOP = 240, 412

UI_ASSETS = (""", "조력자 명령과 자원 선택 버튼 정의")
edit("player_ui.py", "        self.result = None", """        self.result = None
        self.ally = None
        self.gather_menu = False""", "조력자 명령 창 선택 상태 초기화")
method("player_ui.py", "    def click_ally(self, world, x, y, button):", """
        if self.ally is None:
            return False
        if self.ally.state != "ally":
            self.ally = None
            return True
        if button != p.SDL_BUTTON_LEFT:
            self.ally = None
            return True
        options = GATHER_COMMANDS if self.gather_menu else ALLY_COMMANDS
        offset = ALLY_TOP - 52 - y
        if ALLY_LEFT + 26 <= x < ALLY_LEFT + 294 and 0 <= offset < len(options) * 34 and offset % 34 < 28:
            command, _ = options[offset // 34]
            if command in ("gather", "back"):
                self.gather_menu = command == "gather"
            else:
                self.ally.set_command(world, command)
                self.ally = None
        elif not (ALLY_LEFT <= x < ALLY_LEFT + 320 and ALLY_TOP - 224 < y <= ALLY_TOP):
            self.ally = None
        return True
""", "조력자 패널 입력을 소비하고 네 가지 명령과 채집 자원 지정",
"from world import World; from player_ui import PlayerUI,p; w=World(); u=PlayerUI(); a=w.zombies[0]; a.state='ally'; u.ally=a; assert u.click_ally(w,350,252,p.SDL_BUTTON_LEFT) and u.gather_menu; assert u.click_ally(w,350,311,p.SDL_BUTTON_LEFT) and a.command=='stone' and u.ally is None")
method("player_ui.py", "    def draw_ally(self, images):", """
        if self.ally is None:
            return
        self.panel(images, "panel", ALLY_LEFT, ALLY_TOP, 320, 224)
        title = "채집 자원 선택" if self.gather_menu else "조력자 명령"
        self.text(ALLY_LEFT + 27, ALLY_TOP - 25, title)
        options = GATHER_COMMANDS if self.gather_menu else ALLY_COMMANDS
        for index, (_, label) in enumerate(options):
            top = ALLY_TOP - 52 - index * 34
            p.draw_rectangle(ALLY_LEFT + 26, top - 28, ALLY_LEFT + 294, top,
                             64, 66, 65, filled=True)
            self.text(ALLY_LEFT + 40, top - 14, label)
""", "조력자 명령 창과 채집 자원 하위 메뉴 그리기",
"from unittest.mock import Mock,patch; from world import World; from player_ui import PlayerUI; u=PlayerUI(); u.ally=World().zombies[0]; q=patch('player_ui.p.draw_rectangle').start(); u.draw_ally({'ui/panel.png':Mock()}); assert q.call_count==4")
edit("play_mode.py", "                    self.ui.page = \"inventory\" if self.ui.page is None else None", """                    self.ui.ally = None
                    self.ui.page = "inventory" if self.ui.page is None else None""", "인벤토리 열기 전 조력자 명령 창 닫기")
edit("play_mode.py", """                elif self.ui.page is None and event.key == p.SDLK_e:""", """                elif self.ui.page is None and self.ui.ally is None and event.key == p.SDLK_e:""", "조력자 명령 중 아이템 사용 입력 차단")
edit("play_mode.py", """                elif self.ui.page is None and event.key == p.SDLK_b:""", """                elif self.ui.page is None and self.ui.ally is None and event.key == p.SDLK_b:""", "조력자 명령 중 물기 입력 차단")
edit("play_mode.py", """                if self.ui.click(self.player, x, y, event.button):""", """                if self.ui.click_ally(self.world, x, y, event.button):
                    continue
                if self.ui.click(self.player, x, y, event.button):""", "조력자 명령 창 클릭을 월드 공격과 획득보다 먼저 처리")
edit("play_mode.py", """                elif event.button == p.SDL_BUTTON_RIGHT:
                    item = self.world.collect_pickup""", """                elif event.button == p.SDL_BUTTON_RIGHT:
                    ally = self.world.ally_at(self.player, *target)
                    if ally is not None:
                        self.ui.ally = ally
                        self.ui.gather_menu = False
                        continue
                    item = self.world.collect_pickup""", "가까운 조력자 우클릭을 명령 창에 연결",
"from types import SimpleNamespace as E; from play_mode import PlayMode,p; from player_ui import PlayerUI; from world import World; from player import Player; m=PlayMode(); m.ui=PlayerUI(); m.world=World(); m.player=Player(); m.camera=(0,1060); z=m.world.zombies[0]; z.state='ally'; z.x,z.y=285,1360; m.handle_events([E(type=p.SDL_MOUSEBUTTONDOWN,button=p.SDL_BUTTON_RIGHT,x=285,y=299)]); assert m.ui.ally is z")
edit("play_mode.py", """        if self.player.health == 0:""", """        if self.ui.ally is not None and self.ui.ally.state != "ally":
            self.ui.ally = None
        if self.player.health == 0:""", "조력자가 사망하면 열린 명령 창 정리")
edit("play_mode.py", """        self.ui.draw_window(self.images, self.player)""", """        self.ui.draw_ally(self.images)
        self.ui.draw_window(self.images, self.player)""", "플레이 화면에 조력자 명령 창 렌더링 연결")
edit("play_mode.py", """            human = zombie.state in ("ally", "fleeing")""", """            human = zombie.human""", "회복된 인간의 사망 시에도 인간 시트 선택")
edit("play_mode.py", """                row = 3 if zombie.state == "dead" else int(zombie.walk_time > 0)
                frame = int(zombie.walk_time * 9) % 4 if row == 1 else 0""", """                if zombie.state == "dead":
                    row, frame = (4 if human else 3), 0
                elif self.world.resource_time < zombie.attack_until:
                    row, frame = 2, 1
                else:
                    row = int(zombie.walk_time > 0)
                    frame = int(zombie.walk_time * 9) % 4 if row == 1 else 0""", "좀비와 조력자의 공격 접촉 및 인간 사망 프레임 표시")
