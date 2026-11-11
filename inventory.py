from item_data import HOTBAR_ITEMS, RECIPES


class Inventory:
    def __init__(self):
        self.items = {}
        self.slots = [None] * 5
        self.selected = 0

    def add(self, item):
        self.items[item] = self.items.get(item, 0) + 1
        if item in HOTBAR_ITEMS and item not in self.slots and None in self.slots:
            self.slots[self.slots.index(None)] = item

    def remove(self, item, count=1):
        remaining = self.items[item] - count
        if remaining:
            self.items[item] = remaining
        else:
            del self.items[item]
            if item in self.slots:
                self.slots[self.slots.index(item)] = None

    def assign(self, item):
        pass
