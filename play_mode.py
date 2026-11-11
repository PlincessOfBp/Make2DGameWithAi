from pathlib import Path

import pico2d as p

from town import SCREEN_HEIGHT, SCREEN_WIDTH
from world import World


ASSETS = Path(__file__).resolve().parent / "assets"


class PlayMode:
    def enter(self):
        pass
