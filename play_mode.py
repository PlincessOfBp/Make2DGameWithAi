from math import cos, sin
from pathlib import Path

import pico2d as p

from player import Player
from item_data import ITEM_ICON_CELLS, TREE_MAX_HP, WEAPON_COLUMNS
from player_ui import PlayerUI, UI_ASSETS
from town import PICKUP_ICON_HALF_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH, TREE_DRAW_OFFSET
from world import World
from human_npc import GATHER_FRAME_TIME
from zombie import ATTACK_FRAME_TIME


ASSETS = Path(__file__).resolve().parent / "assets"


class PlayMode:
    def enter(self):
        self.world = World()
        self.player = Player()
        self.ui = PlayerUI()
        self.ui.load_font()
        self.keys = set()
        self.mouse = None
        self.camera = self.world.camera(self.player.x, self.player.y)
        self.images = {}
        paths = {
            "world/ground.png", "characters/player.png",
            "world/props/tree.png", "items/items.png",
        }
        paths.update(f"ui/{name}.png" for name in UI_ASSETS)
        paths.update(("items/weapons.png", "world/props/barricade.png", "ui/purifying.png"))
        for zombie in self.world.zombies:
            paths.add(f"characters/zombie_{zombie.variant:02}.png")
            paths.add(f"characters/human_{zombie.variant:02}.png")
        for kind, x, y, *_ in self.world.buildings:
            paths.update(f"world/props/{name}.png" for name, _, _ in self.world.furniture[x, y])
            for layer in ("interior", "roof"):
                paths.add(f"world/buildings/{kind}_{layer}.png")
        for path in sorted(paths):
            try:
                self.images[path] = p.load_image(str(ASSETS / path))
            except OSError:
                self.images[path] = None

    def exit(self):
        self.images.clear()
        self.ui.font = None

    def handle_events(self, events):
        for event in events:
            if event.type == p.SDL_KEYDOWN and event.key == p.SDLK_ESCAPE:
                if self.ui.page is None:
                    return True
                self.ui.page = None
                self.ui.dragged_item = None
            elif event.type == p.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p.SDL_MOUSEMOTION:
                self.mouse = (event.x, SCREEN_HEIGHT - 1 - event.y)
            elif self.ui.result is not None:
                continue
            elif event.type == p.SDL_KEYDOWN:
                self.keys.add(event.key)
                if p.SDLK_1 <= event.key <= p.SDLK_5:
                    self.player.inventory.select(event.key - p.SDLK_1)
                elif event.key == p.SDLK_i:
                    self.ui.ally = None
                    self.ui.dragged_item = None
                    self.ui.page = "inventory" if self.ui.page is None else None
                elif (self.ui.page is None and self.ui.ally is None
                      and event.key in (p.SDLK_e, p.SDLK_b, p.SDLK_q)):
                    cam_x, cam_y = self.camera
                    target = ((self.player.x, self.player.y) if self.mouse is None
                              else (self.mouse[0] + cam_x, self.mouse[1] + cam_y))
                    if event.key == p.SDLK_e:
                        self.player.aim(*target, dt=0)
                        self.player.use_selected(self.world)
                    elif event.key == p.SDLK_q:
                        self.player.aim(*target, dt=0)
                        self.player.drop_selected(self.world)
                    else:
                        self.player.start_action("bite", *target)
            elif event.type == p.SDL_MOUSEBUTTONUP:
                x, y = event.x, SCREEN_HEIGHT - 1 - event.y
                self.ui.release(self.player, x, y, event.button)
            elif event.type == p.SDL_MOUSEBUTTONDOWN:
                x, y = event.x, SCREEN_HEIGHT - 1 - event.y
                self.mouse = (x, y)
                if self.ui.click_ally(self.world, x, y, event.button):
                    continue
                if self.ui.click(self.player, x, y, event.button):
                    continue
                cam_x, cam_y = self.camera
                target = (x + cam_x, y + cam_y)
                if event.button == p.SDL_BUTTON_LEFT:
                    self.player.start_action("attack", *target)
                elif event.button == p.SDL_BUTTON_RIGHT:
                    ally = self.world.ally_at(self.player, *target)
                    if ally is not None:
                        self.ui.ally = ally
                        self.ui.gather_menu = False
                        continue
                    item = self.world.collect_pickup(self.player.x, self.player.y, *target)
                    if item is not None:
                        self.player.inventory.add(item)
        return False

    def update(self, dt):
        if self.ui.page is not None or self.ui.result is not None:
            return
        horizontal = (p.SDLK_d in self.keys) - (p.SDLK_a in self.keys)
        vertical = (p.SDLK_w in self.keys) - (p.SDLK_s in self.keys)
        self.player.move(self.world, horizontal, vertical, dt)
        self.world.update_resources(dt, self.player.x, self.player.y)
        self.camera = self.world.camera(self.player.x, self.player.y)
        if self.mouse is not None:
            mouse_x, mouse_y = self.mouse
            cam_x, cam_y = self.camera
            self.player.aim(mouse_x + cam_x, mouse_y + cam_y, dt)
        self.player.update_action(self.world, dt)
        for actor in self.world.zombies:
            if actor.state in ("zombie", "ally"):
                actor.advance_attack(self.world, self.player)
        for zombie in self.world.zombies:
            zombie.update(self.world, self.player, dt)
        if self.ui.ally is not None and self.ui.ally.state != "ally":
            self.ui.ally = None
        if self.player.health == 0:
            self.ui.result = "게임 오버 · 사망"
        elif self.player.infection >= 100:
            self.ui.result = "게임 오버 · 좀비화"
        elif all(z.state != "zombie" for z in self.world.zombies):
            survivors = sum(z.state in ("ally", "fleeing", "escaped") for z in self.world.zombies)
            self.ui.result = "해피 엔딩" if survivors * 2 > len(self.world.zombies) else "새드 엔딩"

    def draw(self):
        cam_x, cam_y = self.camera
        ground = self.images["world/ground.png"]
        if ground is not None:
            ground.clip_draw(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT,
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        else:
            p.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 91, 112, 75, filled=True)
        self.draw_buildings(interiors=True)
        self.draw_world_objects()
        self.draw_buildings(interiors=False)
        remaining = sum(z.state == "zombie" for z in self.world.zombies)
        self.ui.draw_hud(self.images, self.player, remaining)
        self.ui.draw_ally(self.images)
        self.ui.draw_window(self.images, self.player)
        self.ui.draw_drag(self.images, self.player, self.mouse)

    def draw_buildings(self, interiors):
        cam_x, cam_y = self.camera
        current_building = self.world.building_at(self.player.x, self.player.y)
        for index, (kind, x, y, width, height, footprint) in enumerate(self.world.buildings):
            indoors = index == current_building
            if indoors != interiors:
                continue
            layer = "interior" if indoors else "roof"
            image = self.images[f"world/buildings/{kind}_{layer}.png"]
            if image is not None:
                image.draw(x - cam_x, y - cam_y, width, height)
            else:
                for left, bottom, right, top in footprint:
                    p.draw_rectangle(left - cam_x, bottom - cam_y, right - cam_x, top - cam_y,
                                     100, 80, 68, filled=True)
            if indoors:
                for name, px, py in self.world.furniture[x, y]:
                    prop = self.images[f"world/props/{name}.png"]
                    if prop is not None:
                        prop.draw(px - cam_x, py - cam_y)

    def draw_player(self):
        cam_x, cam_y = self.camera
        player = self.player
        x, y = round(player.x) - cam_x, round(player.y) - cam_y
        image = self.images["characters/player.png"]
        if image is not None:
            if player.health == 0:
                frame, source_y = 0, 1024
            elif self.world.resource_time < player.hurt_until:
                frame, source_y = 0, 1088
            elif player.action is None:
                walking = player.walk_time > 0
                frame = int(player.walk_time * player.WALK_FPS) % 4
                source_y = 1280 if walking else 1344
            else:
                frame = min(int(player.action_elapsed / 0.12), 2)
                source_y = 1216 if player.action == "attack" else 1152
            image.clip_composite_draw(frame * 64, source_y, 64, 64,
                                      player.angle, "", x, y, 64, 64)
        else:
            radius = player.RADIUS
            p.draw_rectangle(x-radius, y-radius, x+radius, y+radius, 60, 140, 220, filled=True)
            p.draw_line(x, y, x-sin(player.angle)*radius, y+cos(player.angle)*radius,
                        255, 255, 255)

    def draw_pickups(self):
        cam_x, cam_y = self.camera
        image = self.images["items/items.png"]
        size = PICKUP_ICON_HALF_SIZE * 2
        for _, item, x, y in self.world.visible_pickups(self.player.x, self.player.y):
            sx, sy = x - cam_x, y - cam_y
            if image is not None:
                source_x, source_y = ITEM_ICON_CELLS[item]
                image.clip_draw(source_x, source_y, size, size, sx, sy)
            else:
                color = (145, 145, 150) if item == "stone" else (220, 173, 72)
                p.draw_rectangle(sx - 7, sy - 7, sx + 7, sy + 7, *color, filled=True)

    def draw_weapon(self):
        player = self.player
        if player.health == 0 or player.action == "bite":
            return
        attacking = player.action == "attack"
        item = player.action_weapon if attacking else player.inventory.selected_item()
        image = self.images["items/weapons.png"]
        if item not in WEAPON_COLUMNS or image is None:
            return
        frame = min(int(player.action_elapsed / 0.12), 2)
        hand_y = (4, 16, 7)[frame] if attacking else 0
        angle = player.angle
        cam_x, cam_y = self.camera
        x = round(player.x - cam_x + 12 * cos(angle) - hand_y * sin(angle))
        y = round(player.y - cam_y + 12 * sin(angle) + hand_y * cos(angle))
        swing = (player.action_elapsed / 0.36 * 2 - 1) * 1.134 if attacking else 0
        image.clip_composite_draw(WEAPON_COLUMNS[item] * 64, 0 if attacking else 64,
                                  64, 64, angle + swing, "", x, y, 64, 64)

    def draw_tree(self, x, y, hp):
        cam_x, cam_y = self.camera
        image = self.images["world/props/tree.png"]
        sx, sy = x - cam_x, y - cam_y
        if image is not None:
            image.draw(sx, sy + TREE_DRAW_OFFSET)
        else:
            p.draw_rectangle(sx - 9, sy - 8, sx + 9, sy + 16, 105, 73, 40, filled=True)
            p.draw_rectangle(sx - 40, sy + 16, sx + 40, sy + 80, 66, 105, 46, filled=True)
        if hp < TREE_MAX_HP:
            p.draw_rectangle(sx - 16, sy + 19, sx + 16, sy + 23, 55, 48, 42, filled=True)
            width = round(32 * hp / TREE_MAX_HP)
            p.draw_rectangle(sx - 16, sy + 19, sx - 16 + width, sy + 23, 222, 174, 79, filled=True)

    def draw_npc(self, zombie):
        cam_x, cam_y = self.camera
        x, y = round(zombie.x) - cam_x, round(zombie.y) - cam_y
        human = zombie.human
        kind = "human" if human else "zombie"
        image = self.images[f"characters/{kind}_{zombie.variant:02}.png"]
        if image is not None:
            if zombie.state == "dead":
                row, frame = (4 if human else 3), 0
            elif self.world.resource_time < zombie.hurt_until:
                row, frame = (5 if human else 4), 0
            elif self.world.resource_time < zombie.attack_until:
                elapsed = self.world.resource_time - (zombie.attack_until - ATTACK_FRAME_TIME * 3)
                row, frame = 2, min(2, max(0, int((elapsed + 1e-9) / ATTACK_FRAME_TIME)))
            elif human and self.world.resource_time < human.gather_until:
                elapsed = self.world.resource_time - (human.gather_until - GATHER_FRAME_TIME * 2)
                row, frame = 3, int(elapsed + 1e-9 >= GATHER_FRAME_TIME)
            else:
                row = int(zombie.walk_time > 0)
                frame = int(zombie.walk_time * 9) % 4 if row == 1 else 0
            image.clip_composite_draw(frame * 64, image.h - (row + 1) * 64,
                                      64, 64, 0 if zombie.state == "dead" else zombie.angle,
                                      "", x, y, 64, 64)
        else:
            p.draw_rectangle(x-8, y-8, x+8, y+8, 82, 154, 84, filled=True)
        if zombie.purify_at is not None:
            icon = self.images["ui/purifying.png"]
            if icon is not None:
                icon.draw(x, y + 36)
            self.ui.text(x + 13, y + 36, f"{max(0, zombie.purify_at - self.world.resource_time):.1f}")

    def draw_barricades(self):
        cam_x, cam_y = self.camera
        barricade = self.images["world/props/barricade.png"]
        for x, y in self.world.barricades:
            x, y = x - cam_x, y - cam_y
            if barricade is not None:
                barricade.draw(x, y + 10)
            else:
                p.draw_rectangle(x-29, y-14, x+29, y+14, 118, 77, 46, filled=True)

    def draw_world_objects(self):
        player = self.player
        current_building = self.world.building_at(player.x, player.y)
        draw_order = []
        for zombie in self.world.zombies:
            if zombie.state == "escaped":
                continue
            building = self.world.building_at(zombie.x, zombie.y)
            if building is not None and building != current_building:
                continue
            if zombie.state == "dead":
                self.draw_npc(zombie)
            else:
                draw_order.append((zombie.y, self.draw_npc, (zombie,)))

        self.draw_barricades()
        self.draw_pickups()
        draw_order.extend(((player.y, self.draw_player, ()), (player.y, self.draw_weapon, ())))
        draw_order.extend((y, self.draw_tree, (x, y, hp)) for (x, y), hp in self.world.trees.items())
        # World Y increases away from the viewer; the trunk anchors each tree's depth.
        for _, draw, args in sorted(draw_order, key=lambda entry: entry[0], reverse=True):
            draw(*args)

    def draw_held_weapon(self, item, angle, x, y, hand_y, swing=None):
        image = self.images["items/weapons.png"]
        if item not in WEAPON_COLUMNS or image is None:
            return
        hand_x = round(x + 12 * cos(angle) - hand_y * sin(angle))
        hand_y = round(y + 12 * sin(angle) + hand_y * cos(angle))
        rotation = angle if swing is None else angle + swing
        image.clip_composite_draw(WEAPON_COLUMNS[item] * 64, 64 if swing is None else 0,
                                  64, 64, rotation, "", hand_x, hand_y, 64, 64)
