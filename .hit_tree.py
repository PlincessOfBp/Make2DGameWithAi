from pathlib import Path
import difflib
import subprocess
import sys


def git(*args, input=None, capture_output=False):
    return subprocess.run(["git", *args], input=input, capture_output=capture_output, check=True)


def change(name, replacements, title, check=""):
    def update(source):
        for old, new in replacements:
            assert old in source, (name, old)
            source = source.replace(old, new, 1)
        return source

    path = Path(name)
    head = git("show", f"HEAD:{name}", capture_output=True).stdout.decode("utf-8")
    staged = update(head)
    working = update(path.read_text(encoding="utf-8"))
    if name.endswith(".py"):
        compile(working, name, "exec")
        compile(staged, name, "exec")
    path.write_text(working, encoding="utf-8")
    if check:
        subprocess.run([sys.executable, "-B", "-c", check], check=True)
    patch = "".join(difflib.unified_diff(
        head.splitlines(keepends=True), staged.splitlines(keepends=True),
        fromfile=f"a/{name}", tofile=f"b/{name}",
    )).encode("utf-8")
    git("apply", "--cached", input=patch)
    git("diff", "--cached", "--check")
    git("--no-pager", "diff", "--cached", "--", name)
    git("commit", "-m", title)
    git("log", "-1", "--oneline")


def append_method(name, signature, body, title, check):
    working = Path(name).read_text(encoding="utf-8")
    anchor = "".join(working.splitlines(keepends=True)[-3:])
    stub = signature + "\n        pass\n"
    change(name, [(anchor, anchor + "\n" + stub)],
           signature.split("(")[0].strip()[4:] + " 메서드 선언")
    change(name, [(stub, signature + "\n" + body.strip("\n") + "\n")], title, check)


change("player.py", [('        self.health = 100\n', '        self.health = 100\n        self.hurt_until = 0.0\n')],
       "플레이어 피격 표시 만료 시각 초기화")
append_method("player.py", "    def take_damage(self, damage, now):", """
        self.health = max(0, self.health - damage)
        self.hurt_until = now + 0.16 if self.health else 0.0
""", "플레이어가 피해를 받으면 잠깐 피격 상태로 표시",
"from player import Player; p=Player(); p.take_damage(5,3); assert (p.health,p.hurt_until)==(95,3.16); p.take_damage(95,3); assert p.health==p.hurt_until==0")
change("zombie.py", [('                    target.health = max(0, target.health - 5)\n', """                    if target is player:
                        player.take_damage(5, world.resource_time)
                    else:
                        target.health = max(0, target.health - 5)
""")], "좀비의 플레이어 공격을 피격 상태 갱신에 연결",
"from world import World; from player import Player; w=World(); p=Player(); z=w.zombies[0]; z.x,z.y=p.x+25,p.y; z.update(w,p,0); assert (p.health,p.hurt_until)==(95,.16)")
change("play_mode.py", [('            if player.action is None:\n', """            if player.health == 0:
                frame, source_y = 0, 1024
            elif self.world.resource_time < player.hurt_until:
                frame, source_y = 0, 1088
            elif player.action is None:
"""), ('        if player.action == "bite":\n', '        if player.health == 0 or player.action == "bite":\n')],
"플레이어 시트의 피격과 사망 프레임을 동작보다 우선 표시",
"from unittest.mock import Mock; from play_mode import PlayMode; from player import Player; from world import World; m=PlayMode(); m.player=Player(); m.world=World(); m.camera=(0,0); img=Mock(); m.images={'characters/player.png':img}; m.player.take_damage(5,0); m.draw_player(); assert img.clip_composite_draw.call_args.args[1]==1088; m.player.take_damage(95,0); m.draw_player(); assert img.clip_composite_draw.call_args.args[1]==1024")

change("item_data.py", [('WOOD_TOOLS = {"axe", "stone_axe"}\n',
'WOOD_TOOLS = {"axe", "stone_axe"}\nTREE_MAX_HP = 60\nTREE_DAMAGE = {"axe": 30, "stone_axe": 20}\n')],
"나무 최대 체력과 일반 도끼·돌도끼 피해 정의",
"from item_data import TREE_MAX_HP,TREE_DAMAGE; assert TREE_MAX_HP==60 and set(TREE_DAMAGE.values())=={20,30}")
change("world.py", [
    ("from item_data import WEAPON_DAMAGE, WOOD_TOOLS\n", "from item_data import TREE_DAMAGE, TREE_MAX_HP, WEAPON_DAMAGE, WOOD_TOOLS\n"),
    ("        self.trees = list(TREE_TRUNKS)\n", "        self.trees = dict.fromkeys(TREE_TRUNKS, TREE_MAX_HP)\n"),
    ("                self.trees.append((x, y))\n", "                self.trees[x, y] = TREE_MAX_HP\n"),
    ("        self.trees.remove(position)\n", "        del self.trees[position]\n"),
], "가로수마다 체력을 보관하고 재생성 시 최대 체력으로 복구",
"from world import World; from player import Player; w=World(); pos=next(iter(w.trees)); assert w.trees[pos]==60; w.harvest_tree(Player(),pos); assert pos not in w.trees; w.update_resources(30,250,1360); assert w.trees[pos]==60")
append_method("world.py", "    def hit_tree(self, position, weapon):", """
        damage = TREE_DAMAGE.get(weapon)
        if damage is None or position not in self.trees:
            return False
        remaining = self.trees[position] - damage
        if remaining > 0:
            self.trees[position] = remaining
            return False
        del self.trees[position]
        self.walls.remove(self.tree_walls[position])
        self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
        x, y = position
        self.pickups[f"drop:{next(self.drop_ids)}"] = ("wood", x, y, self.building_at(x, y))
        return True
""", "나무가 쓰러지는 마지막 타격에만 월드에 나무 아이템 생성",
"from world import World; w=World(); a,b=list(w.trees)[:2]; assert not w.hit_tree(a,'axe') and w.trees[a]==30 and w.trees[b]==60; assert w.hit_tree(a,'axe') and not w.hit_tree(a,'axe') and len(w.pickups)==29; assert not w.hit_tree(b,'stone_axe') and not w.hit_tree(b,'stone_axe') and w.hit_tree(b,'stone_axe') and len(w.pickups)==30")
change("world.py", [
    ("from item_data import TREE_DAMAGE, TREE_MAX_HP, WEAPON_DAMAGE, WOOD_TOOLS\n", "from item_data import TREE_DAMAGE, TREE_MAX_HP, WEAPON_DAMAGE\n"),
    ("weapon in WOOD_TOOLS:", "weapon in TREE_DAMAGE:"),
    ("            self.harvest_tree(player, position)\n", "            self.hit_tree(position, weapon)\n"),
], "플레이어 도끼 공격에 나무 체력과 드롭 연결",
"from world import World; from player import Player; w=World(); p=Player(); p.x,p.y=440,1280; w.resolve_player_action(p,'attack',0,'axe'); assert w.trees[440,1320]==30; w.resolve_player_action(p,'attack',0,'axe'); assert not p.items and w.collect_pickup(p.x,p.y,440,1320)=='wood'")
change("zombie.py", [
    ("from math import atan2, hypot, pi\n", "from math import atan2, hypot, pi\n\nfrom item_data import TREE_DAMAGE\n"),
    ("        self.next_hit = 0.0\n", "        self.next_hit = 0.0\n        self.next_chop = 0.0\n"),
    ("""            has_axe = any(player.items.get(item, 0) for item in ("axe", "stone_axe"))
            targets = world.trees if has_axe else ()""", """            tool = max((item for item in TREE_DAMAGE if player.items.get(item, 0)),
                       key=TREE_DAMAGE.get, default=None)
            targets = world.trees if tool is not None else ()
            if self.command_target is not None and self.command_target not in targets:
                self.set_command(world, "wait")
                self.walk_time = 0.0
                return"""),
    ("""            if distance == 0 or world.pickup_path_clear(
                self.x, self.y, x - (x - self.x) * 15 / distance, y - (y - self.y) * 15 / distance
            ):
                world.harvest_tree(player, (x, y))
            self.set_command(world, "wait")""", """            if distance and not world.pickup_path_clear(
                self.x, self.y, x - (x - self.x) * 15 / distance, y - (y - self.y) * 15 / distance
            ):
                self.set_command(world, "wait")
            elif world.resource_time >= self.next_chop:
                self.next_chop = world.resource_time + 0.65
                if world.hit_tree((x, y), tool):
                    self.set_command(world, "wait")"""),
], "조력자도 보유 도끼에 따라 여러 번 나무를 공격하고 현장에 드롭",
"from world import World; from player import Player; w=World(); p=Player(); p.inventory.add('stone_axe'); a=w.zombies[0]; a.x,a.y=440,1290; a.set_command(w,'wood'); a.gather(w,p,.1); a.gather(w,p,.1); assert w.trees[440,1320]==40; w.resource_time=1; a.gather(w,p,.1); w.resource_time=2; a.gather(w,p,.1); assert (440,1320) not in w.trees and a.command=='wait' and p.items=={'stone_axe':1} and w.pickups['drop:0'][0]=='wood'")
change("world.py", [
    ("""    def harvest_tree(self, player, position):
        if position not in self.trees:
            return False
        del self.trees[position]
        self.walls.remove(self.tree_walls[position])
        self.tree_respawns[position] = self.resource_time + TREE_RESPAWN_SECONDS
        player.inventory.add("wood")
        return True

""", ""),
    ("""            if self.resource_time >= ready_at and not occupied and not overlaps_wall:
                self.trees[x, y] = TREE_MAX_HP""", """            pickup_in_trunk = any(left <= px <= right and bottom <= py <= top
                                  for _, px, py, _ in self.pickups.values())
            if self.resource_time >= ready_at and not occupied and not overlaps_wall and not pickup_in_trunk:
                self.trees[x, y] = TREE_MAX_HP"""),
], "드롭을 주운 뒤에 나무가 재생성되도록 하고 즉시 지급 경로 제거",
"from world import World; w=World(); pos=(440,1320); w.hit_tree(pos,'axe'); w.hit_tree(pos,'axe'); w.update_resources(30,250,1360); assert pos not in w.trees; assert w.collect_pickup(440,1280,*pos)=='wood'; w.update_resources(0,250,1360); assert w.trees[pos]==60")
change("item_data.py", [('WOOD_TOOLS = {"axe", "stone_axe"}\n', '')],
"도끼 적합 여부를 나무 피해 표에 통합")
change("play_mode.py", [
    ("from item_data import ITEM_ICON_CELLS, WEAPON_COLUMNS\n", "from item_data import ITEM_ICON_CELLS, TREE_MAX_HP, WEAPON_COLUMNS\n"),
    ("        for x, y in self.world.trees:\n", "        for (x, y), hp in self.world.trees.items():\n"),
    ('                p.draw_rectangle(sx - 40, sy + 16, sx + 40, sy + 80, 66, 105, 46, filled=True)\n', """                p.draw_rectangle(sx - 40, sy + 16, sx + 40, sy + 80, 66, 105, 46, filled=True)
            if hp < TREE_MAX_HP:
                p.draw_rectangle(sx - 16, sy + 19, sx + 16, sy + 23, 55, 48, 42, filled=True)
                width = round(32 * hp / TREE_MAX_HP)
                p.draw_rectangle(sx - 16, sy + 19, sx - 16 + width, sy + 23, 222, 174, 79, filled=True)
"""),
], "피해를 입은 가로수의 줄기 위에 남은 체력 표시")
change("play_mode.py", [
    ("        self.draw_pickups()\n        self.draw_trees(foreground=False)\n", "        self.draw_trees(foreground=False)\n"),
    ("        self.draw_trees(foreground=True)\n        self.draw_buildings(interiors=False)\n",
     "        self.draw_trees(foreground=True)\n        self.draw_pickups()\n        self.draw_buildings(interiors=False)\n"),
], "픽업을 시체와 캐릭터 위의 월드 레이어에 표시",
"from unittest.mock import Mock; from play_mode import PlayMode; from world import World; from player import Player; m=PlayMode(); m.world=World(); m.player=Player(); m.images={'world/ground.png':Mock()}; m.camera=(0,0); m.ui=Mock(); calls=[]; m.draw_actors=lambda:calls.append('actors'); m.draw_pickups=lambda:calls.append('loot'); m.draw_player=m.draw_weapon=Mock(); m.draw_trees=m.draw_buildings=Mock(); m.mouse=None; m.draw(); assert calls==['actors','loot']")
