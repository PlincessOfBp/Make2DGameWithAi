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
        pass
