from time import perf_counter

import pico2d as p
from pico2d import pico2d as backend

from town import SCREEN_HEIGHT, SCREEN_WIDTH


class GameFramework:
    def run(self, mode):
        p.SDL_SetHint(b"SDL_RENDER_SCALE_QUALITY", b"0")
        p.open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT, sync=True)
        try:
            p.SDL_SetWindowResizable(backend.window, p.SDL_TRUE)
            p.SDL_SetWindowMinimumSize(backend.window, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            # SDL scales the viewport and converts mouse events to the same logical coordinates.
            p.SDL_SetHint(b"SDL_RENDER_LOGICAL_SIZE_MODE", b"letterbox")
            if p.SDL_RenderSetLogicalSize(backend.renderer, SCREEN_WIDTH, SCREEN_HEIGHT) != 0:
                raise RuntimeError(p.SDL_GetError().decode("utf-8", errors="replace"))
            mode.enter()
            previous = perf_counter()
            while True:
                now = perf_counter()
                dt = now - previous
                previous = now
                events = p.get_events()
                for event in events:
                    if event.type == p.SDL_KEYDOWN and event.key == p.SDLK_F11:
                        fullscreen = p.SDL_GetWindowFlags(backend.window) & p.SDL_WINDOW_FULLSCREEN
                        p.SDL_SetWindowFullscreen(backend.window, 0 if fullscreen else p.SDL_WINDOW_FULLSCREEN_DESKTOP)
                events = [event for event in events
                          if not (event.type in (p.SDL_KEYDOWN, p.SDL_KEYUP) and event.key == p.SDLK_F11)]
                if any(event.type == p.SDL_QUIT for event in events) or mode.handle_events(events):
                    break
                mode.update(dt)
                p.SDL_SetRenderDrawColor(backend.renderer, 0, 0, 0, 255)
                p.SDL_RenderClear(backend.renderer)
                p.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 200, 200, 210, filled=True)
                mode.draw()
                p.update_canvas()
        finally:
            try:
                mode.exit()
            finally:
                p.close_canvas()
