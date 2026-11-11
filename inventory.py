from item_data import HOTBAR_ITEMS, RECIPES


class Inventory:
    def __init__(self):
        self.items = {}
        self.slots = [None] * 5
        self.selected = 0
