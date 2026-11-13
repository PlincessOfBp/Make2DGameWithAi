from item_data import HOTBAR_ITEMS, RECIPES, TOOL_DURABILITY


class Inventory:
    def __init__(self):
        self.items = {}
        self.durability = {}
        self.slots = [None] * 5
        self.selected = 0

    def add(self, item, count=1, *, durability=None):
        previous = self.items.get(item, 0)
        self.items[item] = previous + count
        if item in TOOL_DURABILITY:
            uses = TOOL_DURABILITY[item] if durability is None else durability
            self.durability.setdefault(item, []).extend([uses] * count)
        if not previous and item in HOTBAR_ITEMS and None in self.slots:
            self.slots[self.slots.index(None)] = item

    def remove(self, item, count=1):
        if item in self.durability:
            del self.durability[item][:count]
            if not self.durability[item]:
                del self.durability[item]
        remaining = self.items[item] - count
        if remaining:
            self.items[item] = remaining
        else:
            del self.items[item]
            if item in self.slots:
                self.slots[self.slots.index(item)] = None

    def assign(self, item, slot=None):
        if item not in self.items:
            return
        if slot is None:
            slot = self.selected
        if slot is None:
            return
        if item in self.slots:
            previous = self.slots.index(item)
            self.slots[previous] = self.slots[slot]
        self.slots[slot] = item

    def can_craft(self, item):
        return item in RECIPES and all(self.items.get(material, 0) >= count
                                       for material, count in RECIPES[item].items())

    def craft(self, item):
        if not self.can_craft(item):
            return False
        for material, count in RECIPES[item].items():
            self.remove(material, count)
        self.add(item)
        return True

    def unassigned_items(self):
        return [item for item in self.items if item not in self.slots]

    def unassign(self, item):
        if item in self.slots:
            self.slots[self.slots.index(item)] = None

    def selected_item(self):
        return None if self.selected is None else self.slots[self.selected]

    def select(self, slot):
        self.selected = None if self.selected == slot else slot

    def wear_tool(self, item):
        if item in self.durability:
            self.durability[item][0] -= 1
            if self.durability[item][0] == 0:
                self.remove(item)
