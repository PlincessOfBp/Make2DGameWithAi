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


skeleton("player_ui.py", """from os import environ
from pathlib import Path

import pico2d as p

from item_data import ITEM_ICON_CELLS, ITEM_NAMES, RECIPES


HOTBAR_X, HOTBAR_TOP = 259, 68
INVENTORY_X, INVENTORY_TOP = 225, 439
CRAFT_X, CRAFT_TOP = 180, 450
UI_ASSETS = (
    "quickbar", "slot_selected", "inventory", "crafting", "panel", "health", "infection",
)
""", "PlayerUI")
first_method("player_ui.py", "    def __init__(self):", """
        self.page = None
        self.recipe = next(iter(RECIPES))
        self.font = None
        self.result = None
""", "인벤토리 페이지와 제작 선택 및 결과 상태 초기화",
"from player_ui import PlayerUI; assert PlayerUI().page is None")
method("player_ui.py", "    def load_font(self):", """
        windows = Path(environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for path in (windows / "malgun.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                     windows / "arial.ttf"):
            if Path(path).is_file():
                try:
                    self.font = p.load_font(str(path), 15)
                    return
                except (OSError, ValueError):
                    continue
""", "수량과 한글 메뉴 표시를 위한 시스템 글꼴 로드",
"from unittest.mock import patch; from player_ui import PlayerUI; u=PlayerUI(); q=patch('player_ui.p.load_font').start(); u.load_font(); assert u.font is not None")
method("player_ui.py", "    def click(self, player, x, y, button):", """
        inventory = player.inventory
        if self.result is not None:
            return True
        left_click = button == p.SDL_BUTTON_LEFT
        if HOTBAR_X <= x < HOTBAR_X + 282 and HOTBAR_TOP - 64 < y <= HOTBAR_TOP:
            if left_click:
                dx, dy = x - HOTBAR_X - 9, HOTBAR_TOP - y - 8
                if 0 <= dx < 5 * 54 and dx % 54 < 48 and 0 <= dy < 48:
                    inventory.selected = dx // 54
            return True
        if self.page is None:
            return False
        if not left_click:
            return True
        if 450 <= y <= 477:
            if 250 <= x < 395:
                self.page = "inventory"
            elif 405 <= x < 550:
                self.page = "craft"
        elif self.page == "inventory":
            dx, dy = x - INVENTORY_X - 16, INVENTORY_TOP - y - 49
            if 0 <= dx < 6 * 54 and 0 <= dy < 3 * 54 and dx % 54 < 48 and dy % 54 < 48:
                index = dy // 54 * 6 + dx // 54
                items = [item for item in ITEM_NAMES if item in inventory.items]
                if index < len(items):
                    inventory.assign(items[index])
        else:
            dx, dy = x - CRAFT_X, CRAFT_TOP - y
            if 20 <= dx < 154 and 56 <= dy < 56 + 3 * 63 and (dy - 56) % 63 < 56:
                self.recipe = tuple(RECIPES)[(dy - 56) // 63]
            elif 293 <= dx <= 414 and 222 <= dy <= 251:
                inventory.craft(self.recipe)
        return True
""", "핫바·인벤토리·제작 UI 클릭을 소비하고 슬롯 및 레시피 조작",
"from player import Player; from player_ui import PlayerUI,p; u=PlayerUI(); a=Player(); assert not u.click(a,400,300,p.SDL_BUTTON_LEFT); assert u.click(a,335,35,p.SDL_BUTTON_LEFT) and a.inventory.selected==1; u.page='inventory'; assert u.click(a,475,463,p.SDL_BUTTON_LEFT) and u.page=='craft'")
method("player_ui.py", "    def text(self, x, y, value, color=(248, 239, 218)):", """
        if self.font is not None:
            self.font.draw(x, y, value, color)
""", "UI 글자와 수량 렌더링", "from unittest.mock import Mock; from player_ui import PlayerUI; u=PlayerUI(); u.font=Mock(); u.text(3,4,'42'); u.font.draw.assert_called_once()")
method("player_ui.py", "    def panel(self, images, name, x, top, width, height):", """
        image = images[f"ui/{name}.png"]
        if image is None:
            p.draw_rectangle(x, top - height, x + width, top, 44, 49, 52, filled=True)
        else:
            image.draw(x + width // 2, top - height // 2)
""", "UI 에셋을 클릭 좌표와 일치하는 위치에 그리기",
"from unittest.mock import Mock; from player_ui import PlayerUI; u=PlayerUI(); m=Mock(); u.panel({'ui/panel.png':m},'panel',240,412,320,224); m.draw.assert_called_once_with(400,300)")
method("player_ui.py", "    def icon(self, images, item, x, y, count=None):", """
        image = images["items/items.png"]
        if image is not None:
            sx, sy = ITEM_ICON_CELLS[item]
            image.clip_draw(sx, sy, 32, 32, x, y)
        else:
            self.text(x - 15, y, ITEM_NAMES[item])
        if count is not None:
            self.text(x + 8, y - 12, str(count))
""", "아이템 아이콘과 보유 수량 그리기",
"from unittest.mock import Mock; from player_ui import PlayerUI; u=PlayerUI(); m=Mock(); u.icon({'items/items.png':m},'axe',40,50); m.clip_draw.assert_called_once_with(64,32,32,32,40,50)")
method("player_ui.py", "    def draw_hud(self, images, player, remaining):", """
        inventory = player.inventory
        for index, (name, value, color) in enumerate((
            ("health", player.health, (177, 56, 54)),
            ("infection", player.infection, (88, 152, 95)),
        )):
            y = 574 - index * 28
            image = images[f"ui/{name}.png"]
            if image is not None:
                image.draw(22, y)
            p.draw_rectangle(38, y - 8, 138, y + 8, 43, 44, 46, filled=True)
            if value > 0:
                p.draw_rectangle(38, y - 8, 38 + value, y + 8, *color, filled=True)
            self.text(145, y, str(int(value)))
        self.text(662, 574, f"남은 좀비 {remaining}")
        self.panel(images, "quickbar", HOTBAR_X, HOTBAR_TOP, 282, 64)
        for index, item in enumerate(inventory.slots):
            x = HOTBAR_X + 33 + index * 54
            y = HOTBAR_TOP - 32
            if index == inventory.selected:
                self.panel(images, "slot_selected", x - 24, y + 24, 48, 48)
            if item is not None:
                self.icon(images, item, x, y, inventory.items[item])
            self.text(x - 20, y + 16, str(index + 1))
""", "체력·감염·남은 좀비와 선택 핫바를 화면에 표시",
"from unittest.mock import Mock,patch; from player_ui import PlayerUI,UI_ASSETS; from player import Player; u=PlayerUI(); images={f'ui/{key}.png':Mock() for key in UI_ASSETS}; p=Player(); patch('player_ui.p.draw_rectangle').start(); u.draw_hud(images,p,20); images['ui/slot_selected.png'].draw.assert_called_once()")
method("player_ui.py", "    def draw_window(self, images, player):", """
        if self.result is not None:
            self.panel(images, "panel", 240, 412, 320, 224)
            self.text(320, 320, self.result)
            self.text(340, 270, "Esc로 종료")
            return
        if self.page is None:
            return
        inventory = player.inventory
        for left, name, page in ((250, "인벤토리", "inventory"), (405, "제작", "craft")):
            color = (111, 90, 53) if self.page == page else (58, 62, 64)
            p.draw_rectangle(left, 450, left + 145, 477, *color, filled=True)
            self.text(left + 28, 463, name)
        if self.page == "inventory":
            self.panel(images, "inventory", INVENTORY_X, INVENTORY_TOP, 350, 258)
            self.text(241, 414, "인벤토리")
            for index, item in enumerate(item for item in ITEM_NAMES if item in inventory.items):
                x = INVENTORY_X + 40 + index % 6 * 54
                y = INVENTORY_TOP - 73 - index // 6 * 54
                self.icon(images, item, x, y, inventory.items[item])
            self.text(241, 211, "아이템 클릭  /  선택한 핫바에 배정")
        else:
            self.panel(images, "crafting", CRAFT_X, CRAFT_TOP, 440, 280)
            self.text(202, 421, "제작")
            for index, item in enumerate(RECIPES):
                y = CRAFT_TOP - 56 - index * 63
                if item == self.recipe:
                    p.draw_rectangle(CRAFT_X + 20, y - 56, CRAFT_X + 154, y, 205, 168, 96)
                self.text(CRAFT_X + 27, y - 28, ITEM_NAMES[item])
            self.icon(images, self.recipe, CRAFT_X + 207, CRAFT_TOP - 83)
            for index, (item, count) in enumerate(RECIPES[self.recipe].items()):
                owned = inventory.items.get(item, 0)
                color = (248, 239, 218) if owned >= count else (255, 140, 130)
                self.text(CRAFT_X + 193, CRAFT_TOP - 132 - index * 29,
                          f"{ITEM_NAMES[item]}  {owned}/{count}", color)
            enabled = inventory.can_craft(self.recipe)
            p.draw_rectangle(CRAFT_X + 293, CRAFT_TOP - 251, CRAFT_X + 414, CRAFT_TOP - 222,
                             *((111, 90, 53) if enabled else (60, 63, 65)), filled=True)
            self.text(CRAFT_X + 326, CRAFT_TOP - 237, "제작" if enabled else "재료 부족")
""", "인벤토리와 제작 패널에 재료·결과·버튼 상태 표시",
"from unittest.mock import Mock,patch; from player_ui import PlayerUI,UI_ASSETS; from player import Player; u=PlayerUI(); p=Player(); u.page='craft'; images={f'ui/{key}.png':Mock() for key in UI_ASSETS}; images['items/items.png']=Mock(); patch('player_ui.p.draw_rectangle').start(); u.draw_window(images,p); images['ui/crafting.png'].draw.assert_called_once()")
edit("play_mode.py", "from item_data import ITEM_ICON_CELLS", """from item_data import ITEM_ICON_CELLS, WEAPON_COLUMNS
from player_ui import PlayerUI, UI_ASSETS""", "플레이 모드에서 플레이어 UI와 무기 시트 설정 참조")
edit("play_mode.py", '        for kind, x, y, *_ in self.world.buildings:', """        paths.update(f"ui/{name}.png" for name in UI_ASSETS)
        paths.update(("items/weapons.png", "world/props/barricade.png", "ui/purifying.png"))
        for zombie in self.world.zombies:
            paths.add(f"characters/zombie_{zombie.variant:02}.png")
            paths.add(f"characters/human_{zombie.variant:02}.png")
        for kind, x, y, *_ in self.world.buildings:""", "UI와 무기·바리케이트·NPC 이미지를 월드 에셋과 함께 로딩")
edit("play_mode.py", "        self.player = Player()", """        self.player = Player()
        self.ui = PlayerUI()
        self.ui.load_font()""", "플레이 화면 진입 시 인벤토리·제작 UI 준비")
edit("play_mode.py", "        self.images.clear()", "        self.images.clear()\n        self.ui.font = None", "캔버스를 닫기 전에 UI 글꼴 참조 해제")
method("play_mode.py", "    def draw_actors(self):", """
        cam_x, cam_y = self.camera
        current_building = self.world.building_at(self.player.x, self.player.y)
        for zombie in self.world.zombies:
            if zombie.state == "escaped":
                continue
            building = self.world.building_at(zombie.x, zombie.y)
            if building is not None and building != current_building:
                continue
            x, y = round(zombie.x) - cam_x, round(zombie.y) - cam_y
            human = zombie.state in ("ally", "fleeing")
            kind = "human" if human else "zombie"
            image = self.images[f"characters/{kind}_{zombie.variant:02}.png"]
            if image is not None:
                row = 3 if zombie.state == "dead" else int(zombie.walk_time > 0)
                frame = int(zombie.walk_time * 9) % 4 if row == 1 else 0
                image.clip_composite_draw(frame * 64, (4 if human else 3) * 64 - row * 64,
                                          64, 64, zombie.angle, "", x, y, 64, 64)
            else:
                p.draw_rectangle(x-8, y-8, x+8, y+8, 82, 154, 84, filled=True)
            if zombie.purify_at is not None:
                icon = self.images["ui/purifying.png"]
                if icon is not None:
                    icon.draw(x, y + 36)
                self.ui.text(x + 13, y + 36, f"{max(0, zombie.purify_at - self.world.resource_time):.1f}")
        barricade = self.images["world/props/barricade.png"]
        for x, y in self.world.barricades:
            x, y = x - cam_x, y - cam_y
            if barricade is not None:
                barricade.draw(x, y + 10)
            else:
                p.draw_rectangle(x-29, y-14, x+29, y+14, 118, 77, 46, filled=True)
""", "좀비와 회복된 인간·정화 타이머 및 바리케이트 렌더링",
"from unittest.mock import Mock; from play_mode import PlayMode; from world import World; from player import Player; m=PlayMode(); m.world=World(); m.player=Player(); m.camera=(0,0); image=Mock(); m.images={f'characters/zombie_{i:02}.png':image for i in range(1,4)}; m.images['world/props/barricade.png']=None; m.draw_actors(); assert image.clip_composite_draw.call_count==20")

edit("play_mode.py", """            walking = player.walk_time > 0
            frame = int(player.walk_time * player.WALK_FPS) % 4
            source_y = 1280 if walking else 1344
            image.clip_composite_draw(frame * 64, source_y, 64, 64,
                                      player.angle, "", x, y, 64, 64)""", """            if player.action is None:
                walking = player.walk_time > 0
                frame = int(player.walk_time * player.WALK_FPS) % 4
                source_y = 1280 if walking else 1344
            else:
                frame = min(int(player.action_elapsed / 0.12), 2)
                source_y = 1216 if player.action == "attack" else 1152
            image.clip_composite_draw(frame * 64, source_y, 64, 64,
                                      player.angle, "", x, y, 64, 64)""", "플레이어 대기·이동에 공격과 물기 애니메이션 연결")
method("play_mode.py", "    def draw_weapon(self):", """
        player = self.player
        if player.action == "bite":
            return
        inventory = player.inventory
        attacking = player.action == "attack"
        item = player.action_weapon if attacking else inventory.slots[inventory.selected]
        image = self.images["items/weapons.png"]
        if item not in WEAPON_COLUMNS or image is None:
            return
        frame = min(int(player.action_elapsed / 0.12), 2)
        hand_y = (4, 16, 7)[frame] if attacking else 0
        angle = player.angle
        cam_x, cam_y = self.camera
        x = round(player.x - cam_x + 12 * cos(angle) - hand_y * sin(angle))
        y = round(player.y - cam_y + 12 * sin(angle) + hand_y * cos(angle))
        swing = (player.action_elapsed / 0.36 * 2 - 1) * 1.134 if attacking else 0
        image.clip_composite_draw(WEAPON_COLUMNS[item] * 64, 0 if attacking else 64,
                                  64, 64, angle + swing, "", x, y, 64, 64)
""", "손 위치와 회전에 맞춰 장착 무기와 휘두르기 레이어 표시",
"from unittest.mock import Mock; from play_mode import PlayMode; from player import Player; m=PlayMode(); m.player=Player(); m.player.inventory.add('axe'); m.camera=(0,0); img=Mock(); m.images={'items/weapons.png':img}; m.draw_weapon(); img.clip_composite_draw.assert_called_once_with(192,64,64,64,0,'',262,1360,64,64)")
edit("play_mode.py", """        self.draw_player()
        self.draw_trees(foreground=True)
        self.draw_buildings(interiors=False)""", """        self.draw_actors()
        self.draw_player()
        self.draw_weapon()
        self.draw_trees(foreground=True)
        self.draw_buildings(interiors=False)
        remaining = sum(z.state == "zombie" for z in self.world.zombies)
        self.ui.draw_hud(self.images, self.player, remaining)
        self.ui.draw_window(self.images, self.player)""", "마을 화면에 무기·좀비·핫바와 플레이어 UI 연결")

edit("play_mode.py", """    def handle_events(self, events):
        for event in events:
            if event.type == p.SDL_KEYDOWN:
                self.keys.add(event.key)
            elif event.type == p.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p.SDL_MOUSEMOTION:
                self.mouse = (event.x, SCREEN_HEIGHT - 1 - event.y)
            elif event.type == p.SDL_MOUSEBUTTONDOWN and event.button == p.SDL_BUTTON_RIGHT:
                cam_x, cam_y = self.camera
                mouse_x, mouse_y = event.x + cam_x, SCREEN_HEIGHT - 1 - event.y + cam_y
                item = self.world.collect_pickup(self.player.x, self.player.y, mouse_x, mouse_y)
                if item is not None:
                    self.player.items[item] = self.player.items.get(item, 0) + 1""", """    def handle_events(self, events):
        for event in events:
            if event.type == p.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p.SDL_MOUSEMOTION:
                self.mouse = (event.x, SCREEN_HEIGHT - 1 - event.y)
            elif self.ui.result is not None:
                continue
            elif event.type == p.SDL_KEYDOWN:
                self.keys.add(event.key)
                if p.SDLK_1 <= event.key <= p.SDLK_5:
                    self.player.inventory.selected = event.key - p.SDLK_1
                elif event.key == p.SDLK_i:
                    self.ui.page = "inventory" if self.ui.page is None else None
                elif self.ui.page is None and event.key == p.SDLK_e:
                    self.player.use_selected(self.world)
                elif self.ui.page is None and event.key == p.SDLK_b:
                    cam_x, cam_y = self.camera
                    target = ((self.player.x, self.player.y) if self.mouse is None
                              else (self.mouse[0] + cam_x, self.mouse[1] + cam_y))
                    self.player.start_action("bite", *target)
            elif event.type == p.SDL_MOUSEBUTTONDOWN:
                x, y = event.x, SCREEN_HEIGHT - 1 - event.y
                if self.ui.click(self.player, x, y, event.button):
                    continue
                self.mouse = (x, y)
                cam_x, cam_y = self.camera
                target = (x + cam_x, y + cam_y)
                if event.button == p.SDL_BUTTON_LEFT:
                    self.player.start_action("attack", *target)
                elif event.button == p.SDL_BUTTON_RIGHT:
                    item = self.world.collect_pickup(self.player.x, self.player.y, *target)
                    if item is not None:
                        self.player.inventory.add(item)""", "숫자키·I·E·B와 마우스 클릭에 플레이어 조작 연결",
"from unittest.mock import Mock; from types import SimpleNamespace as E; from play_mode import PlayMode,p; from player_ui import PlayerUI; from player import Player; m=PlayMode(); m.ui=PlayerUI(); m.player=Player(); m.keys=set(); m.camera=(0,0); m.handle_events([E(type=p.SDL_KEYDOWN,key=p.SDLK_i),E(type=p.SDL_MOUSEBUTTONDOWN,button=p.SDL_BUTTON_LEFT,x=150,y=150)]); assert m.ui.page=='inventory' and m.player.action is None")
edit("play_mode.py", "    def update(self, dt):\n        horizontal", """    def update(self, dt):
        if self.ui.page is not None or self.ui.result is not None:
            return
        horizontal""", "인벤토리와 제작 창 및 게임 종료 상태에서 월드 정지")
edit("play_mode.py", "            self.player.aim(mouse_x + cam_x, mouse_y + cam_y, dt)", """            self.player.aim(mouse_x + cam_x, mouse_y + cam_y, dt)
        self.player.update_action(self.world, dt)
        for zombie in self.world.zombies:
            zombie.update(self.world, self.player, dt)
        if self.player.health == 0:
            self.ui.result = "게임 오버 · 사망"
        elif self.player.infection >= 100:
            self.ui.result = "게임 오버 · 좀비화"
        elif all(z.state != "zombie" for z in self.world.zombies):
            survivors = sum(z.state in ("ally", "fleeing", "escaped") for z in self.world.zombies)
            self.ui.result = "해피 엔딩" if survivors * 2 > len(self.world.zombies) else "새드 엔딩" """.rstrip(),
"행동 접촉·좀비 갱신과 사망·좀비화·클리어 판정을 실행 루프에 연결",
"from play_mode import PlayMode; from player_ui import PlayerUI; from player import Player; from world import World; m=PlayMode(); m.ui=PlayerUI(); m.player=Player(); m.world=World(); m.keys=set(); m.mouse=None; m.player.health=0; m.update(.1); assert '사망' in m.ui.result; t=m.world.resource_time; m.update(1); assert m.world.resource_time==t")
