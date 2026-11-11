from math import cos, sin
from pathlib import Path

import pico2d as p

from player import Player
from item_data import ITEM_ICON_CELLS, WEAPON_COLUMNS
from player_ui import PlayerUI, UI_ASSETS
from town import PICKUP_ICON_HALF_SIZE, SCREEN_HEIGHT, SCREEN_WIDTH, TREE_DRAW_OFFSET
from world import World


ASSETS = Path(__file__).resolve().parent / "assets"


class PlayMode:
    def enter(self):
        self.world = World()
        self.player = Player()
        self.keys = set()
        self.mouse = None
        self.camera = self.world.camera(self.player.x, self.player.y)
        self.images = {}
        paths = {
            "world/ground.png", "characters/player.png",
            "world/props/tree.png", "items/items.png",
        }
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

    def handle_events(self, events):
        for event in events:
            if event.type == p.SDL_KEYDOWN:
                self.keys.add(event.key)
            elif event.type == p.SDL_KEYUP:
                self.keys.discard(event.key)
            elif event.type == p.SDL_MOUSEMOTION:
                self.mouse = (event.x, SCREEN_HEIGHT - 1 - event.y)
            elif event.type == p.SDL_MOUSEBUTTONDOWN and event.button == p.SDL_BUTTON_RIGHT:
                cam_x, cam_y = self.camera
                mouse_x, mouse_y = event.x + cam_x, SCREEN_HEIGHT - 1 - event.y + cam_y
                item = self.world.collect_pickup(self.player.x, self.player.y, mouse_x, mouse_y)
                if item is not None:
                    self.player.items[item] = self.player.items.get(item, 0) + 1

    def update(self, dt):
        horizontal = (p.SDLK_d in self.keys) - (p.SDLK_a in self.keys)
        vertical = (p.SDLK_w in self.keys) - (p.SDLK_s in self.keys)
        self.player.move(self.world, horizontal, vertical, dt)
        self.world.update_resources(dt, self.player.x, self.player.y)
        self.camera = self.world.camera(self.player.x, self.player.y)
        if self.mouse is not None:
            mouse_x, mouse_y = self.mouse
            cam_x, cam_y = self.camera
            self.player.aim(mouse_x + cam_x, mouse_y + cam_y, dt)

    def draw(self):
        cam_x, cam_y = self.camera
        ground = self.images["world/ground.png"]
        if ground is not None:
            ground.clip_draw(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT,
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        else:
            p.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 91, 112, 75, filled=True)
        self.draw_buildings(interiors=True)
        self.draw_pickups()
        self.draw_trees(foreground=False)
        self.draw_player()
        self.draw_trees(foreground=True)
        self.draw_buildings(interiors=False)

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
            walking = player.walk_time > 0
            frame = int(player.walk_time * player.WALK_FPS) % 4
            source_y = 1280 if walking else 1344
            image.clip_composite_draw(frame * 64, source_y, 64, 64,
                                      player.angle, "", x, y, 64, 64)
        else:
            radius = player.RADIUS
            p.draw_rectangle(x-radius, y-radius, x+radius, y+radius, 60, 140, 220, filled=True)
            p.draw_line(x, y, x-sin(player.angle)*radius, y+cos(player.angle)*radius,
                        255, 255, 255)

    def draw_trees(self, foreground):

        cam_x, cam_y = self.camera
        image = self.images["world/props/tree.png"]
        for x, y in self.world.trees:
            if (y < self.player.y) != foreground:
                continue
            sx, sy = x - cam_x, y - cam_y
            if image is not None:
                image.draw(sx, sy + TREE_DRAW_OFFSET)
            else:
                p.draw_rectangle(sx - 9, sy - 8, sx + 9, sy + 16, 105, 73, 40, filled=True)
                p.draw_rectangle(sx - 40, sy + 16, sx + 40, sy + 80, 66, 105, 46, filled=True)

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
