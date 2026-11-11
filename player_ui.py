from os import environ
from pathlib import Path

import pico2d as p

from item_data import ITEM_ICON_CELLS, ITEM_NAMES, RECIPES


HOTBAR_X, HOTBAR_TOP = 259, 68
INVENTORY_X, INVENTORY_TOP = 225, 439
CRAFT_X, CRAFT_TOP = 180, 450
ALLY_COMMANDS = (
    ("wait", "대기"), ("follow", "따라가기"), ("attack", "공동 공격"), ("gather", "채집"),
)
GATHER_COMMANDS = (("wood", "나무"), ("stone", "돌멩이"), ("back", "뒤로"))
ALLY_LEFT, ALLY_TOP = 240, 412

UI_ASSETS = (
    "quickbar", "slot_selected", "inventory", "crafting", "panel", "health", "infection",
)


class PlayerUI:
    def __init__(self):
        self.page = None
        self.recipe = next(iter(RECIPES))
        self.font = None
        self.result = None
        self.ally = None
        self.gather_menu = False
        self.dragged_item = None

    def load_font(self):
        windows = Path(environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for path in (windows / "malgun.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                     windows / "arial.ttf"):
            if Path(path).is_file():
                try:
                    self.font = p.load_font(str(path), 15)
                    return
                except (OSError, ValueError):
                    continue

    def click(self, player, x, y, button):
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

    def text(self, x, y, value, color=(248, 239, 218)):
        if self.font is not None:
            self.font.draw(x, y, value, color)

    def panel(self, images, name, x, top, width, height):
        image = images[f"ui/{name}.png"]
        if image is None:
            p.draw_rectangle(x, top - height, x + width, top, 44, 49, 52, filled=True)
        else:
            image.draw(x + width // 2, top - height // 2)

    def icon(self, images, item, x, y, count=None):
        image = images["items/items.png"]
        if image is not None:
            sx, sy = ITEM_ICON_CELLS[item]
            image.clip_draw(sx, sy, 32, 32, x, y)
        else:
            self.text(x - 15, y, ITEM_NAMES[item])
        if count is not None:
            self.text(x + 8, y - 12, str(count))

    def draw_hud(self, images, player, remaining):
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

    def draw_window(self, images, player):
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

    def click_ally(self, world, x, y, button):
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

    def draw_ally(self, images):
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

    def hotbar_slot_at(self, x, y):
        dx, dy = x - HOTBAR_X - 9, HOTBAR_TOP - y - 8
        if 0 <= dx < 5 * 54 and dx % 54 < 48 and 0 <= dy < 48:
            return dx // 54
        return None

    def release(self, player, x, y, button):
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
