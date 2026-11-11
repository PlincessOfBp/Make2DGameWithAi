from os import environ
from pathlib import Path

import pico2d as p

from item_data import ITEM_ICON_CELLS, ITEM_NAMES, RECIPES


HOTBAR_X, HOTBAR_TOP = 259, 68
INVENTORY_X, INVENTORY_TOP = 225, 439
CRAFT_X, CRAFT_TOP = 180, 450
UI_ASSETS = (
    "quickbar", "slot_selected", "inventory", "crafting", "panel", "health", "infection",
)


class PlayerUI:
    def __init__(self):
        self.page = None
        self.recipe = next(iter(RECIPES))
        self.font = None
        self.result = None

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
        pass
