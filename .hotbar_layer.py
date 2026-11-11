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
    compile(working, name, "exec")
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


def method(name, signature, body, title, check):
    anchor = "".join(Path(name).read_text(encoding="utf-8").splitlines(keepends=True)[-2:])
    stub = signature + "\n        pass\n"
    change(name, [(anchor, anchor + "\n" + stub)],
           signature.split("(")[0].strip()[4:] + " 메서드 선언")
    change(name, [(stub, signature + "\n" + body.strip("\n") + "\n")], title, check)


change("play_mode.py", [
    ("        self.draw_actors()\n        self.draw_player()\n", "        self.draw_actors()\n        self.draw_pickups()\n        self.draw_player()\n"),
    ("        self.draw_trees(foreground=True)\n        self.draw_pickups()\n", "        self.draw_trees(foreground=True)\n"),
], "픽업을 시체 위와 플레이어 아래에 그리기",
"from unittest.mock import Mock; from play_mode import PlayMode; from world import World; m=PlayMode(); m.world=World(); m.player=None; m.camera=(0,0); m.images={'world/ground.png':Mock()}; m.mouse=None; m.ui=Mock(); calls=[]; m.draw_actors=lambda:calls.append('actors'); m.draw_pickups=lambda:calls.append('loot'); m.draw_player=lambda:calls.append('player'); m.draw_weapon=lambda:calls.append('weapon'); m.draw_trees=m.draw_buildings=Mock(); m.draw(); assert calls==['actors','loot','player','weapon']")
method("inventory.py", "    def selected_item(self):", """
        return None if self.selected is None else self.slots[self.selected]
""", "핫바 미선택 상태에서 맨손 판정을 반환",
"from inventory import Inventory; i=Inventory(); i.add('axe'); assert i.selected_item()=='axe'; i.selected=None; assert i.selected_item() is None")
change("inventory.py", [
    ("        if slot is None:\n            slot = self.selected\n", "        if slot is None:\n            slot = self.selected\n        if slot is None:\n            return\n"),
], "맨손 상태에서 슬롯을 지정하지 않은 배정은 건너뛰기")
change("player.py", [
    ("        selected = self.inventory.slots[self.inventory.selected]\n", "        selected = self.inventory.selected_item()\n"),
    ("        item = self.inventory.slots[self.inventory.selected]\n", "        item = self.inventory.selected_item()\n"),
    ("        item = self.inventory.slots[self.inventory.selected]\n", "        item = self.inventory.selected_item()\n"),
], "맨손일 때 맨손 공격을 사용하고 아이템 사용·드롭 생략",
"from player import Player; from world import World; p=Player(); w=World(); p.inventory.add('axe'); p.inventory.selected=None; assert p.start_action('attack',p.x+40,p.y) and p.action_weapon is None; assert not p.use_selected(w) and not p.drop_selected(w) and p.items=={'axe':1}")
change("play_mode.py", [
    ("        inventory = player.inventory\n        attacking", "        attacking"),
    ("inventory.slots[inventory.selected]", "player.inventory.selected_item()"),
], "선택이 해제되면 장착 무기 레이어 숨기기")
method("inventory.py", "    def select(self, slot):", """
        self.selected = None if self.selected == slot else slot
""", "현재 핫바 슬롯을 다시 선택하면 선택 해제",
"from inventory import Inventory; i=Inventory(); i.add('axe'); i.select(0); assert i.selected is None and i.slots[0]=='axe'; i.select(0); assert i.selected_item()=='axe'")
change("play_mode.py", [
    ("                    self.player.inventory.selected = event.key - p.SDLK_1\n",
     "                    self.player.inventory.select(event.key - p.SDLK_1)\n"),
], "숫자키에 핫바 재선택 토글 연결")
change("player_ui.py", [
    ("""                    inventory.selected = slot
                    if self.page == "inventory":
                        self.dragged_item = inventory.slots[slot]""", """                    if self.page == "inventory" and inventory.slots[slot] is not None:
                        self.dragged_item = inventory.slots[slot]
                    else:
                        inventory.select(slot)"""),
    ("""        if slot is not None:
            inventory.assign(item, slot)""", """        if slot is not None:
            if inventory.slots[slot] == item:
                inventory.select(slot)
            else:
                inventory.assign(item, slot)"""),
], "핫바 클릭에 선택 해제 연결하고 드래그 교환 유지",
"from play_mode import p; from player import Player; from player_ui import PlayerUI; a=Player(); u=PlayerUI(); a.inventory.add('axe'); a.inventory.add('knife'); u.click(a,292,36,p.SDL_BUTTON_LEFT); assert a.inventory.selected is None; u.page='inventory'; u.click(a,292,36,p.SDL_BUTTON_LEFT); u.release(a,292,36,p.SDL_BUTTON_LEFT); assert a.inventory.selected==0; u.click(a,292,36,p.SDL_BUTTON_LEFT); u.release(a,346,36,p.SDL_BUTTON_LEFT); assert a.inventory.slots[:2]==['knife','axe'] and a.inventory.selected==0")
