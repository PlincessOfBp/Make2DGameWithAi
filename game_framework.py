from time import perf_counter

import pico2d as p

from town import SCREEN_HEIGHT, SCREEN_WIDTH


class GameFramework:
    def run(self, mode):
        p.SDL_SetHint(b"SDL_RENDER_SCALE_QUALITY", b"0")
        p.open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT, sync=True)
        try:
            mode.enter()
            previous = perf_counter()
            while True:
                now = perf_counter()
                dt = now - previous
                previous = now
                events = p.get_events()
                if any(event.type == p.SDL_QUIT for event in events) or mode.handle_events(events):
                    break
                mode.update(dt)
                p.clear_canvas()
                mode.draw()
                p.update_canvas()
        finally:
            try:
                mode.exit()
            finally:
                p.close_canvas()
