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
        pass
