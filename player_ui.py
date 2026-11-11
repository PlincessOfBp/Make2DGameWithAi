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
        pass
