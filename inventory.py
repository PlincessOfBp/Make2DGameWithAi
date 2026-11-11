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
        if item not in self.items or item not in HOTBAR_ITEMS:
            return
        if item in self.slots:
            previous = self.slots.index(item)
            self.slots[previous] = self.slots[self.selected]
        self.slots[self.selected] = item

    def can_craft(self, item):
        return item in RECIPES and all(self.items.get(material, 0) >= count
                                       for material, count in RECIPES[item].items())

    def craft(self, item):
        pass
