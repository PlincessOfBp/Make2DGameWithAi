from pathlib import Path

import pico2d as p

from town import SCREEN_HEIGHT, SCREEN_WIDTH
from world import World


ASSETS = Path(__file__).resolve().parent / "assets"


class PlayMode:
    def enter(self):
        self.world = World()
        self.camera = self.world.camera(250, 1360)
        self.images = {}
        paths = {"world/ground.png"}
        for kind, *_ in self.world.buildings:
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
        pass


    def update(self, dt):
        pass


    def draw(self):
        cam_x, cam_y = self.camera
        ground = self.images["world/ground.png"]
        if ground is not None:
            ground.clip_draw(cam_x, cam_y, SCREEN_WIDTH, SCREEN_HEIGHT,
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        else:
            p.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 91, 112, 75, filled=True)
        self.draw_buildings()


    def draw_buildings(self):
        cam_x, cam_y = self.camera
        for kind, x, y, width, height, footprint in self.world.buildings:
            image = self.images[f"world/buildings/{kind}_roof.png"]
            if image is not None:
                image.draw(x - cam_x, y - cam_y)
            else:
                for left, bottom, right, top in footprint:
                    p.draw_rectangle(left - cam_x, bottom - cam_y, right - cam_x, top - cam_y,
                                     100, 80, 68, filled=True)
