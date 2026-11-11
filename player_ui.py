from os import environ
from pathlib import Path

import pico2d as p

from human_npc import GATHER_LIMIT
from item_data import ITEM_ICON_CELLS, ITEM_NAMES, RECIPES


HOTBAR_X, HOTBAR_TOP = 259, 68
INVENTORY_X, INVENTORY_TOP = 225, 439
CRAFT_X, CRAFT_TOP = 180, 450
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
        self.gather_resource = "wood"
        self.gather_amount = 1
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
                slot = self.hotbar_slot_at(x, y)
                if slot is not None:
                    if self.page == "inventory" and inventory.slots[slot] is not None:
                        self.dragged_item = inventory.slots[slot]
                    else:
                        inventory.select(slot)
            return True
        if self.page is None:
            return False
        if not left_click:
            return True
        if 450 <= y <= 477:
            if 250 <= x < 395:
                self.page = "inventory"
            elif 405 <= x < 550:
                self.dragged_item = None
                self.page = "craft"
        elif self.page == "inventory":
            dx, dy = x - INVENTORY_X - 16, INVENTORY_TOP - y - 49
            if 0 <= dx < 6 * 54 and 0 <= dy < 3 * 54 and dx % 54 < 48 and dy % 54 < 48:
                index = dy // 54 * 6 + dx // 54
                items = inventory.unassigned_items()
                if index < len(items):
                    self.dragged_item = items[index]
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
            if item is not None and item != self.dragged_item:
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
            for index, item in enumerate(inventory.unassigned_items()):
                x = INVENTORY_X + 40 + index % 6 * 54
                y = INVENTORY_TOP - 73 - index // 6 * 54
                if item != self.dragged_item:
                    self.icon(images, item, x, y, inventory.items[item])
            self.text(241, 211, "아이템을 드래그해 핫바 배정 또는 해제")
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

    def click_ally(self, world, x, y, button, player):
        if self.ally is None:
            return False
        if not world.can_command_ally(player, self.ally):
            self.ally = None
            return True
        if button != p.SDL_BUTTON_LEFT:
            self.ally = None
            return True
        for action, _, left, bottom, right, top, enabled in self.ally_buttons():
            if not (left <= x < right and bottom <= y < top):
                continue
            if not enabled:
                return True
            if action == "gather":
                self.gather_menu = True
                self.gather_resource, self.gather_amount = "wood", 1
            elif action in ("wood", "stone"):
                self.gather_resource = action
            elif action == "more":
                self.gather_amount += 1
            elif action == "less":
                self.gather_amount -= 1
            elif action == "back":
                self.gather_menu = False
            elif action == "start":
                self.ally.set_command(world, self.gather_resource, self.gather_amount)
                self.ally = None
            elif action == "take":
                self.ally.human.take_gathered(player)
            else:
                self.ally.set_command(world, action)
                self.ally = None
            return True
        if not (ALLY_LEFT <= x < ALLY_LEFT + 320 and ALLY_TOP - 224 < y <= ALLY_TOP):
            self.ally = None
        return True

    def draw_ally(self, images):
        if self.ally is None:
            return
        self.panel(images, "panel", ALLY_LEFT, ALLY_TOP, 320, 224)
        self.text(ALLY_LEFT + 27, ALLY_TOP - 25, "채집 설정" if self.gather_menu else "조력자 명령")
        human = self.ally.human
        for action, label, left, bottom, right, top, enabled in self.ally_buttons():
            selected = (action == self.gather_resource if self.gather_menu else action == human.command)
            color = (112, 89, 50) if selected else (64, 66, 65)
            if not enabled:
                color = (43, 45, 46)
            p.draw_rectangle(left, bottom, right, top, *color, filled=True)
            self.text(left + 14, (bottom + top) // 2, label,
                      (248, 239, 218) if enabled else (155, 153, 149))
        if self.gather_menu:
            self.text(366, 308, f"수량  {self.gather_amount}")
        else:
            if human.command in ("wood", "stone"):
                status = f"채집 중  ·  남은 수량 {human.gather_remaining}"
            elif human.gather_shortfall and human.command in ("return", "wait"):
                suffix = "복귀 중" if human.command == "return" else "복귀 완료"
                status = f"채집 {human.gather_shortfall}개 미달  ·  {suffix}"
            else:
                status = {"return": "명령 지점으로 복귀 중", "follow": "따라가기 · 전투 지원",
                          "attack": "공동 공격 중", "wait": "대기 중"}[human.command]
            self.text(264, 275, status)
            counts = "  ".join(f"{ITEM_NAMES[item]} {count}" for item, count in human.inventory.items.items())
            self.text(264, 250, f"보관 물품  {counts or '없음'}")

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
            if inventory.slots[slot] == item:
                inventory.select(slot)
            else:
                inventory.assign(item, slot)
        elif INVENTORY_X <= x < INVENTORY_X + 350 and INVENTORY_TOP - 258 < y <= INVENTORY_TOP:
            inventory.unassign(item)

    def draw_drag(self, images, player, pointer):
        if self.dragged_item is None or pointer is None:
            return
        x, y = pointer
        slot = self.hotbar_slot_at(x, y)
        if slot is not None:
            left = HOTBAR_X + 9 + slot * 54
            top = HOTBAR_TOP - 8
            p.draw_rectangle(left, top - 48, left + 48, top, 247, 210, 127)
        self.icon(images, self.dragged_item, x, y, player.inventory.items[self.dragged_item])

    def ally_buttons(self):
        if self.gather_menu:
            return (
                ("wood", "나무", 262, 333, 392, 361, True),
                ("stone", "돌멩이", 408, 333, 538, 361, True),
                ("less", "−", 262, 294, 315, 322, self.gather_amount > 1),
                ("more", "+", 485, 294, 538, 322, self.gather_amount < GATHER_LIMIT),
                ("back", "뒤로", 262, 211, 392, 241, True),
                ("start", "채집 시작", 408, 211, 538, 241, True),
            )
        return (
            ("wait", "대기", 262, 333, 392, 361, True),
            ("follow", "따라가기", 408, 333, 538, 361, True),
            ("attack", "공동 공격", 262, 296, 392, 324, True),
            ("gather", "채집", 408, 296, 538, 324, True),
            ("take", "물품 받기", 262, 202, 538, 230, self.ally.human.can_take_gathered()),
        )
