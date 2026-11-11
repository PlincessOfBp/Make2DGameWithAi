from pathlib import Path
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


def method(name, signature, body, title, check):
    source = Path(name).read_text(encoding="utf-8")
    stub = signature + "\n        pass\n"
    save(name, source.rstrip() + "\n\n" + stub, signature.split("(")[0].strip()[4:] + " 메서드 선언")
    edit(name, stub, signature + "\n" + body.strip("\n") + "\n", title, check)


source = Path("world.py").read_text(encoding="utf-8")
source = source.replace(
    "        # Try in front first, then nearby directions when a wall or pickup blocks the spot.",
    """        # Try in front first, then nearby directions when a wall or pickup blocks the spot.
        building = self.building_at(player.x, player.y)""")
source = source.replace(
    "                if self.move(player.x, player.y, x - player.x, y - player.y, 8) != (x, y):",
    """                if self.building_at(x, y) != building:
                    continue
                if self.move(player.x, player.y, x - player.x, y - player.y, 8) != (x, y):""")
source = source.replace("(item, x, y, self.building_at(x, y))", "(item, x, y, building)")
save("world.py", source, "벽과 기존 픽업을 피해 같은 공간에 회수 가능한 월드 드롭 생성",
"from world import World; from player import Player; w=World(); p=Player(); assert w.drop_item(p,'axe') and w.drop_item(p,'axe'); assert w.pickups['drop:0'][1:3]!=w.pickups['drop:1'][1:3]; item,x,y,_=w.pickups['drop:0']; assert w.collect_pickup(p.x,p.y,x,y)==item")
method("player.py", "    def drop_selected(self, world):", """
        item = self.inventory.slots[self.inventory.selected]
        if item is None or not world.drop_item(self, item):
            return False
        self.inventory.remove(item)
        return True
""", "월드 드롭에 성공했을 때만 선택 슬롯 수량 한 개 차감",
"from unittest.mock import Mock; from player import Player; p=Player(); w=Mock(); assert not p.drop_selected(w); p.inventory.add('axe'); p.inventory.add('axe'); w.drop_item.return_value=False; assert not p.drop_selected(w) and p.items['axe']==2; w.drop_item.return_value=True; assert p.drop_selected(w) and p.items['axe']==1 and p.drop_selected(w) and p.inventory.slots[0] is None")
edit("player_ui.py", "        self.gather_menu = False", "        self.gather_menu = False\n        self.dragged_item = None",
"인벤토리에서 드래그 중인 아이템 상태 초기화")
method("player_ui.py", "    def hotbar_slot_at(self, x, y):", """
        dx, dy = x - HOTBAR_X - 9, HOTBAR_TOP - y - 8
        if 0 <= dx < 5 * 54 and dx % 54 < 48 and 0 <= dy < 48:
            return dx // 54
        return None
""", "핫바 슬롯 좌표를 클릭과 드롭에 공통 적용",
"from player_ui import PlayerUI; u=PlayerUI(); assert u.hotbar_slot_at(292,36)==0 and u.hotbar_slot_at(346,36)==1 and u.hotbar_slot_at(317,36) is None")
method("player_ui.py", "    def release(self, player, x, y, button):", """
        if button != p.SDL_BUTTON_LEFT:
            return
        item, self.dragged_item = self.dragged_item, None
        if item is None or self.page != "inventory":
            return
        inventory = player.inventory
        slot = self.hotbar_slot_at(x, y)
        if slot is not None:
            inventory.assign(item, slot)
        elif INVENTORY_X <= x < INVENTORY_X + 350 and INVENTORY_TOP - 258 < y <= INVENTORY_TOP:
            inventory.unassign(item)
""", "드래그를 슬롯에서 놓으면 배정하고 인벤토리에 놓으면 해제",
"from player import Player; from player_ui import PlayerUI,p; u=PlayerUI(); a=Player(); a.inventory.add('axe'); u.page='inventory'; u.dragged_item='axe'; u.release(a,300,300,p.SDL_BUTTON_LEFT); assert a.inventory.unassigned_items()==['axe']; u.dragged_item='axe'; u.release(a,346,36,p.SDL_BUTTON_LEFT); assert a.inventory.slots[1]=='axe'; u.dragged_item='axe'; u.release(a,100,100,p.SDL_BUTTON_LEFT); assert a.inventory.slots[1]=='axe' and u.dragged_item is None")
method("player_ui.py", "    def draw_drag(self, images, player, pointer):", """
        if self.dragged_item is None or pointer is None:
            return
        x, y = pointer
        slot = self.hotbar_slot_at(x, y)
        if slot is not None:
            left = HOTBAR_X + 9 + slot * 54
            top = HOTBAR_TOP - 8
            p.draw_rectangle(left, top - 48, left + 48, top, 247, 210, 127)
        self.icon(images, self.dragged_item, x, y, player.inventory.items[self.dragged_item])
""", "드래그 아이콘을 커서 위치에 표시하고 대상 핫바 슬롯 강조",
"from unittest.mock import Mock,patch; from player import Player; from player_ui import PlayerUI; u=PlayerUI(); a=Player(); a.inventory.add('axe'); u.dragged_item='axe'; u.icon=Mock(); q=patch('player_ui.p.draw_rectangle').start(); u.draw_drag({},a,(346,36)); u.icon.assert_called_once_with({},'axe',346,36,1); assert q.call_count==1")
edit("player_ui.py", """                dx, dy = x - HOTBAR_X - 9, HOTBAR_TOP - y - 8
                if 0 <= dx < 5 * 54 and dx % 54 < 48 and 0 <= dy < 48:
                    inventory.selected = dx // 54""", """                slot = self.hotbar_slot_at(x, y)
                if slot is not None:
                    inventory.selected = slot
                    if self.page == "inventory":
                        self.dragged_item = inventory.slots[slot]""",
"인벤토리가 열렸을 때 핫바에서 드래그 시작")
edit("player_ui.py", """            elif 405 <= x < 550:
                self.page = "craft" """.rstrip(), """            elif 405 <= x < 550:
                self.dragged_item = None
                self.page = "craft" """.rstrip(), "제작 탭을 열 때 인벤토리 드래그 취소")
edit("player_ui.py", """                items = [item for item in ITEM_NAMES if item in inventory.items]
                if index < len(items):
                    inventory.assign(items[index])""", """                items = inventory.unassigned_items()
                if index < len(items):
                    self.dragged_item = items[index]""",
"인벤토리 아이템을 누르면 즉시 배정하는 대신 드래그 시작",
"from player_ui import PlayerUI,p; from player import Player; u=PlayerUI(); a=Player(); a.inventory.add('axe'); a.inventory.add('stone'); u.page='inventory'; u.click(a,265,366,p.SDL_BUTTON_LEFT); assert u.dragged_item=='stone' and a.inventory.slots[0]=='axe'; u.release(a,292,36,p.SDL_BUTTON_LEFT); assert a.inventory.slots[0]=='stone' and a.inventory.unassigned_items()==['axe']")
edit("player_ui.py", """            if item is not None:
                self.icon(images, item, x, y, inventory.items[item])""", """            if item is not None and item != self.dragged_item:
                self.icon(images, item, x, y, inventory.items[item])""",
"드래그하는 동안 핫바 원래 위치의 아이콘 숨기기")
edit("player_ui.py", """            for index, item in enumerate(item for item in ITEM_NAMES if item in inventory.items):
                x = INVENTORY_X + 40 + index % 6 * 54
                y = INVENTORY_TOP - 73 - index // 6 * 54
                self.icon(images, item, x, y, inventory.items[item])
            self.text(241, 211, "아이템 클릭  /  선택한 핫바에 배정")""", """            for index, item in enumerate(inventory.unassigned_items()):
                x = INVENTORY_X + 40 + index % 6 * 54
                y = INVENTORY_TOP - 73 - index // 6 * 54
                if item != self.dragged_item:
                    self.icon(images, item, x, y, inventory.items[item])
            self.text(241, 211, "아이템을 드래그해 핫바 배정 또는 해제")""",
"인벤토리에 미배정 아이템과 드래그 안내 표시")

edit("play_mode.py", """                    self.ui.ally = None
                    self.ui.page = "inventory" if self.ui.page is None else None""", """                    self.ui.ally = None
                    self.ui.dragged_item = None
                    self.ui.page = "inventory" if self.ui.page is None else None""",
"인벤토리 닫기와 재열기에서 진행 중인 드래그 취소")
edit("play_mode.py", """            elif event.type == p.SDL_MOUSEBUTTONDOWN:
                x, y = event.x, SCREEN_HEIGHT - 1 - event.y""", """            elif event.type == p.SDL_MOUSEBUTTONUP:
                x, y = event.x, SCREEN_HEIGHT - 1 - event.y
                self.ui.release(self.player, x, y, event.button)
            elif event.type == p.SDL_MOUSEBUTTONDOWN:
                x, y = event.x, SCREEN_HEIGHT - 1 - event.y
                self.mouse = (x, y)""",
"마우스 버튼을 놓는 이벤트를 인벤토리 드롭에 연결")
edit("play_mode.py", """                self.mouse = (x, y)
                cam_x, cam_y = self.camera
                target = (x + cam_x, y + cam_y)""", """                cam_x, cam_y = self.camera
                target = (x + cam_x, y + cam_y)""",
"버튼 입력의 커서 위치 갱신을 한 곳에서 처리")
edit("play_mode.py", "        self.ui.draw_window(self.images, self.player)", """        self.ui.draw_window(self.images, self.player)
        self.ui.draw_drag(self.images, self.player, self.mouse)""", "UI 맨 위에 드래그 아이콘 표시")
source = Path("play_mode.py").read_text(encoding="utf-8")
source = source.replace("(p.SDLK_e, p.SDLK_b)", "(p.SDLK_e, p.SDLK_b, p.SDLK_q)").replace(
    '                    else:\n                        self.player.start_action("bite", *target)',
    """                    elif event.key == p.SDLK_q:
                        self.player.aim(*target, dt=0)
                        self.player.drop_selected(self.world)
                    else:
                        self.player.start_action("bite", *target)""")
save("play_mode.py", source, "Q 키로 커서 방향에 선택 아이템 한 개 떨어뜨리기",
"from types import SimpleNamespace as E; from play_mode import PlayMode,p; from player_ui import PlayerUI; from player import Player; from world import World; m=PlayMode(); m.ui=PlayerUI(); m.player=Player(); m.world=World(); m.mouse=None; m.camera=(0,1060); m.keys=set(); m.player.inventory.add('axe'); m.handle_events([E(type=p.SDL_KEYDOWN,key=p.SDLK_q)]); assert m.player.items=={} and m.world.pickups['drop:0'][0]=='axe'")
