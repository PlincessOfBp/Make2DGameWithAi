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


save("item_data.py", """ITEM_NAMES = {
    "wood": "나무", "stone": "돌멩이", "axe": "도끼", "nails": "못", "tape": "테이프",
    "canned_food": "통조림", "knife": "나이프", "stone_axe": "돌도끼",
    "nailed_bat": "못 박힌 방망이", "barricade": "바리케이트",
}
ITEM_ICON_CELLS = {
    item: (index % 5 * 32, 32 - index // 5 * 32)
    for index, item in enumerate(ITEM_NAMES)
}
RECIPES = {
    "stone_axe": {"wood": 1, "stone": 1, "tape": 1},
    "nailed_bat": {"wood": 2, "nails": 2},
    "barricade": {"wood": 3, "nails": 2},
}
WEAPON_DAMAGE = {None: 5, "knife": 10, "stone_axe": 13, "nailed_bat": 17, "axe": 25}
WEAPON_COLUMNS = {"knife": 0, "stone_axe": 1, "nailed_bat": 2, "axe": 3}
WOOD_TOOLS = {"axe", "stone_axe"}
HOTBAR_ITEMS = {*WEAPON_COLUMNS, "canned_food", "barricade"}
""", "아이템 아이콘과 제작 재료 및 무기 피해량 정의",
"from item_data import ITEM_ICON_CELLS; assert ITEM_ICON_CELLS['barricade']==(128,0)")
skeleton("inventory.py", "from item_data import HOTBAR_ITEMS, RECIPES\n", "Inventory")
first_method("inventory.py", "    def __init__(self):", """
        self.items = {}
        self.slots = [None] * 5
        self.selected = 0
""", "보유 수량과 다섯 개 핫바 슬롯 초기화", "from inventory import Inventory; assert Inventory().slots==[None]*5")
method("inventory.py", "    def add(self, item):", """
        self.items[item] = self.items.get(item, 0) + 1
        if item in HOTBAR_ITEMS and item not in self.slots and None in self.slots:
            self.slots[self.slots.index(None)] = item
""", "획득 아이템 수량을 누적하고 사용 가능한 아이템 자동 등록",
"from inventory import Inventory; i=Inventory(); i.add('axe'); i.add('axe'); assert i.items=={'axe':2} and i.slots[0]=='axe'")
method("inventory.py", "    def remove(self, item, count=1):", """
        remaining = self.items[item] - count
        if remaining:
            self.items[item] = remaining
        else:
            del self.items[item]
            if item in self.slots:
                self.slots[self.slots.index(item)] = None
""", "소비한 수량을 차감하고 소진된 핫바 아이템 제거",
"from inventory import Inventory; i=Inventory(); i.add('axe'); i.remove('axe'); assert not i.items and i.slots[0] is None")
method("inventory.py", "    def assign(self, item):", """
        if item not in self.items or item not in HOTBAR_ITEMS:
            return
        if item in self.slots:
            previous = self.slots.index(item)
            self.slots[previous] = self.slots[self.selected]
        self.slots[self.selected] = item
""", "인벤토리 아이템을 선택 슬롯에 배정",
"from inventory import Inventory; i=Inventory(); i.add('axe'); i.add('canned_food'); i.selected=1; i.assign('axe'); assert i.slots[:2]==['canned_food','axe']")
method("inventory.py", "    def can_craft(self, item):", """
        return item in RECIPES and all(self.items.get(material, 0) >= count
                                       for material, count in RECIPES[item].items())
""", "레시피에 필요한 재료와 수량 확인",
"from inventory import Inventory; assert not Inventory().can_craft('barricade')")
method("inventory.py", "    def craft(self, item):", """
        if not self.can_craft(item):
            return False
        for material, count in RECIPES[item].items():
            self.remove(material, count)
        self.add(item)
        return True
""", "제작 성공 시 모든 재료를 차감하고 결과 지급",
"from inventory import Inventory; i=Inventory(); i.add('wood'); assert not i.craft('stone_axe') and i.items=={'wood':1}; i.add('stone'); i.add('tape'); assert i.craft('stone_axe') and i.items=={'stone_axe':1}")
edit("player.py", "from math import atan2, expm1, hypot, pi, tau", "from math import atan2, cos, expm1, hypot, pi, sin, tau\n\nfrom inventory import Inventory\nfrom item_data import WEAPON_COLUMNS", "플레이어에서 인벤토리와 무기 설정 참조")
edit("player.py", "        self.items = {}", """        self.inventory = Inventory()
        self.items = self.inventory.items
        self.health = 100
        self.infection = 0.0
        self.action = None
        self.action_elapsed = 0.0
        self.action_angle = 0.0
        self.action_weapon = None""", "플레이어 체력과 감염 및 행동 상태 초기화",
"from player import Player; p=Player(); assert p.health==100 and p.infection==0 and p.action is None")
method("player.py", "    def start_action(self, action, target_x, target_y):", """
        if self.action is not None:
            return False
        dx, dy = target_x - self.x, target_y - self.y
        self.action_angle = atan2(dy, dx) - pi / 2 if dx or dy else self.target_angle
        selected = self.inventory.slots[self.inventory.selected]
        self.action_weapon = selected if action == "attack" and selected in WEAPON_COLUMNS else None
        self.action = action
        self.action_elapsed = 0.0
        return True
""", "공격과 물기 시작 시 방향과 장비 기록",
"from player import Player; p=Player(); p.inventory.add('axe'); assert p.start_action('attack',350,1360); assert p.action_weapon=='axe' and not p.start_action('bite',0,0)")
method("player.py", "    def update_action(self, world, dt):", """
        self.infection = max(0.0, self.infection - dt * (2 / 60))
        if self.action is None:
            return
        previous = self.action_elapsed
        self.action_elapsed += dt
        if previous < 0.12 <= self.action_elapsed:
            world.resolve_player_action(self, self.action, self.action_angle, self.action_weapon)
        if self.action_elapsed >= 0.36:
            self.action = None
""", "접촉 시점을 넘는 프레임에만 행동 판정하고 감염 자연 감소",
"from unittest.mock import Mock; from player import Player; p=Player(); w=Mock(); p.start_action('bite',0,0); p.update_action(w,.2); p.update_action(w,.2); assert w.resolve_player_action.call_count==1 and p.action is None")
method("player.py", "    def use_selected(self, world):", """
        item = self.inventory.slots[self.inventory.selected]
        if item == "canned_food" and (self.health < 100 or self.infection > 0):
            self.health = min(100, self.health + 30)
            self.infection = max(0, self.infection - 20)
        elif item == "barricade":
            x = round(self.x - sin(self.target_angle) * 64)
            y = round(self.y + cos(self.target_angle) * 64)
            if not world.place_barricade(self, x, y):
                return False
        else:
            return False
        self.inventory.remove(item)
        return True
""", "통조림 회복과 유효한 바리케이트 설치를 E 사용 동작에 연결",
"from unittest.mock import Mock; from player import Player; p=Player(); w=Mock(); p.inventory.add('canned_food'); assert not p.use_selected(w); p.health=81; p.infection=25; assert p.use_selected(w) and (p.health,p.infection)==(100,5)")
skeleton("zombie.py", "from math import atan2, hypot, pi\n", "Zombie")
first_method("zombie.py", "    def __init__(self, entity_id, x, y):", """
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
""", "좀비 체력과 세 가지 이동 속도 초기화",
"from zombie import Zombie; assert [Zombie(i,0,0).speed for i in range(3)]==[185,220,245]")
method("zombie.py", "    def move_toward(self, world, x, y, dt, speed, stop):", """
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
""", "좀비와 회복된 인간에 월드 충돌 이동 적용",
"from zombie import Zombie; from world import World; z=Zombie(0,250,1360); z.move_toward(World(),350,1360,1,220,25); assert z.x==325")
method("zombie.py", "    def update(self, world, player, dt):", """
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
""", "좀비 추적과 피격 간격 및 물린 좀비의 정화 전환 구현",
"from random import Random; from zombie import Zombie; from world import World; from player import Player; w=World(); w.random=Random(1); p=Player(); z=Zombie(1,250,1389); z.update(w,p,0); z.update(w,p,0); assert p.health==95; z.purify_at=10; w.resource_time=10; z.update(w,p,0); assert z.state=='ally'")

edit("town.py", "PICKUP_REACH = 64", """ZOMBIE_POINTS = (
    (580, 1320), (990, 1350), (960, 1655), (72, 1730), (420, 1755),
    (1350, 1650), (1850, 1690), (2310, 1580), (1700, 1285), (2230, 1265),
    (1080, 880), (565, 720), (152, 725), (210, 405), (850, 275),
    (1400, 705), (1740, 790), (1830, 505), (2180, 320), (2240, 835),
)
TREE_RESPAWN_SECONDS = 30
PICKUP_REACH = 64""", "초기 좀비 20마리 위치와 가로수 재생성 설정 정의")
edit("play_mode.py", "from town import ITEM_ICON_CELLS, PICKUP_ICON_HALF_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH, TREE_DRAW_OFFSET",
"from item_data import ITEM_ICON_CELLS\nfrom town import PICKUP_ICON_HALF_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH, TREE_DRAW_OFFSET",
"월드 아이템과 UI가 공통 아이콘 설정을 사용하도록 연결")
edit("town.py", 'ITEM_ICON_CELLS = {\n    "stone": (32, 32),\n    "axe": (64, 32),\n    "nails": (96, 32),\n    "tape": (128, 32),\n    "canned_food": (0, 0),\n}\n', "", "중복된 맵 아이템 아이콘 설정 정리")
edit("world.py", "from math import hypot", """from math import cos, hypot, sin
from random import Random

from item_data import WEAPON_DAMAGE, WOOD_TOOLS
from zombie import Zombie""", "월드에서 전투 수치와 좀비 클래스를 참조")
edit("world.py", "    TREE_TRUNKS, TREE_TRUNK_HALF_HEIGHT, TREE_TRUNK_HALF_WIDTH,",
"    TREE_RESPAWN_SECONDS, TREE_TRUNKS, TREE_TRUNK_HALF_HEIGHT, TREE_TRUNK_HALF_WIDTH, ZOMBIE_POINTS,",
"월드에서 좀비 배치와 가로수 재생성 설정 참조")
edit("world.py", """        self.trees = TREE_TRUNKS
        self.walls = [
            (x - TREE_TRUNK_HALF_WIDTH, y - TREE_TRUNK_HALF_HEIGHT,
             x + TREE_TRUNK_HALF_WIDTH, y + TREE_TRUNK_HALF_HEIGHT)
            for x, y in self.trees
        ]""", """        self.trees = list(TREE_TRUNKS)
        self.tree_walls = {
            (x, y): (x - TREE_TRUNK_HALF_WIDTH, y - TREE_TRUNK_HALF_HEIGHT,
                     x + TREE_TRUNK_HALF_WIDTH, y + TREE_TRUNK_HALF_HEIGHT)
            for x, y in self.trees
        }
        self.walls = list(self.tree_walls.values())
        self.tree_respawns = {}
        self.barricades = []
        self.random = Random()
        self.zombies = [Zombie(index, x, y) for index, (x, y) in enumerate(ZOMBIE_POINTS)]""",
"월드에 좀비와 채집 및 설치 상태 초기화",
"from world import World; assert len(World().zombies)==20")
method("world.py", "    def place_barricade(self, player, x, y):", """
        left, bottom, right, top = x - 29, y - 14, x + 29, y + 14
        if left < 0 or bottom < 0 or right > MAP_WIDTH or top > MAP_HEIGHT:
            return False
        if any(left < r and right > l and bottom < t and top > b for l, b, r, t in self.walls):
            return False
        actors = [player, *(z for z in self.zombies if z.state not in ("dead", "escaped"))]
        if any(left - 8 < actor.x < right + 8 and bottom - 8 < actor.y < top + 8 for actor in actors):
            return False
        if any(left <= px <= right and bottom <= py <= top for _, px, py, _ in self.pickups.values()):
            return False
        self.walls.append((left, bottom, right, top))
        self.barricades.append((x, y))
        return True
""", "바리케이트 설치 시 경계·장애물·개체·픽업 겹침 확인",
"from world import World; from player import Player; w=World(); p=Player(); assert not w.place_barricade(p,p.x,p.y) and w.place_barricade(p,1000,400) and not w.place_barricade(p,1000,400)")
method("world.py", "    def resolve_player_action(self, player, action, angle, weapon):", """
        forward_x, forward_y = -sin(angle), cos(angle)
        reach = 46 if action == "bite" else 78
        targets = [(z.x, z.y, z) for z in self.zombies if z.state == "zombie"
                   and (action != "bite" or z.purify_at is None)]
        if action == "attack" and weapon in WOOD_TOOLS:
            targets.extend((x, y, None) for x, y in self.trees)
        hits = []
        for x, y, zombie in targets:
            dx, dy = x - player.x, y - player.y
            distance = hypot(dx, dy)
            if distance > reach or dx * forward_x + dy * forward_y < distance * 0.65:
                continue
            if zombie is None and distance:
                # Stop the ray just before the target tree's own trunk.
                x -= dx * min(1, 15 / distance)
                y -= dy * min(1, 15 / distance)
            if self.pickup_path_clear(player.x, player.y, x, y):
                hits.append((distance, zombie, (player.x + dx, player.y + dy)))
        if not hits:
            return
        _, zombie, position = min(hits, key=lambda hit: hit[0])
        if zombie is None:
            self.trees.remove(position)
            self.walls.remove(self.tree_walls[position])
            self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
            player.inventory.add("wood")
        elif action == "bite":
            zombie.purify_at = self.resource_time + 10
            player.infection = min(100, player.infection + 10)
        else:
            zombie.health = max(0, zombie.health - WEAPON_DAMAGE[weapon])
            if zombie.health == 0:
                zombie.state = "dead"
                zombie.purify_at = None
                if self.random.random() < 0.35:
                    item = self.random.choice(("axe", "knife", "canned_food"))
                    self.pickups[f"zombie:{zombie.entity_id}"] = (
                        item, zombie.x, zombie.y, self.building_at(zombie.x, zombie.y),
                    )
""", "조준 범위에서 공격·나무 채집·물기·사망 드롭 처리",
"from math import pi; from world import World; from player import Player; w=World(); p=Player(); p.x,p.y=440,1280; w.resolve_player_action(p,'attack',0,'axe'); assert p.items=={'wood':1}; z=w.zombies[0]; p.x,p.y=z.x-35,z.y; w.resolve_player_action(p,'bite',-pi/2,None); assert p.infection==10 and z.purify_at==10; w.resolve_player_action(p,'attack',-pi/2,'axe'); assert z.health==25")
edit("world.py", "                del self.stone_respawns[pickup_id]",
"""                del self.stone_respawns[pickup_id]
        for (x, y), ready_at in tuple(self.tree_respawns.items()):
            wall = self.tree_walls[x, y]
            left, bottom, right, top = wall
            occupied = hypot(player_x - x, player_y - y) < 32 or any(
                hypot(z.x - x, z.y - y) < 24 for z in self.zombies if z.state not in ("dead", "escaped")
            )
            overlaps_wall = any(left < r and right > l and bottom < t and top > b
                                for l, b, r, t in self.walls)
            if self.resource_time >= ready_at and not occupied and not overlaps_wall:
                self.trees.append((x, y))
                self.walls.append(wall)
                del self.tree_respawns[x, y]""", "채집 후 나무가 빈 지점에서 다시 자라도록 갱신",
"from world import World; from player import Player; w=World(); p=Player(); p.x,p.y=440,1280; w.resolve_player_action(p,'attack',0,'axe'); w.update_resources(30,440,1280); assert (440,1320) in w.trees")
