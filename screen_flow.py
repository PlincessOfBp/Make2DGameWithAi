from ctypes import byref, c_int

import pico2d as p
from pico2d import pico2d as renderer_backend

from play_mode import ASSETS, PlayMode
from player_ui import PlayerUI
from town import SCREEN_HEIGHT, SCREEN_WIDTH
from game_audio import GameAudio


RESULT_IMAGES = {
    "게임 오버 · 사망": "ending_death",
    "게임 오버 · 좀비화": "ending_infection",
    "새드 엔딩": "ending_sad",
    "해피 엔딩": "ending_happy",
}
RESULT_MUSIC = {
    "게임 오버 · 사망": "ending_loss",
    "게임 오버 · 좀비화": "ending_infection",
    "새드 엔딩": "ending_loss",
    "해피 엔딩": "ending_happy",
}
LOADING_FINISH_SECONDS = 5.0
BUTTONS = {
    "main": (("start", "", 109, 54), ("help", "", 303, 54),
             ("settings", "", 497, 54), ("quit", "종료", 691, 54)),
    "help": (("back", "", 400, 64),),
    "settings": (("back", "", 400, 173),),
    "ending": (("restart", "다시 시작", 294, 46), ("menu", "메인으로", 506, 46)),
    "pause": (("confirm", "확인", 294, 227), ("cancel", "취소", 506, 227),
              ("settings", "", 400, 282)),
    "error": (("menu", "메인으로", 400, 64),),
}
VOLUME_SLIDERS = (("bgm", "BGM", 360), ("effects", "효과음", 270))
SLIDER_LEFT, SLIDER_RIGHT = 249, 551
HELP_GOALS = (
    "마을에 남은 좀비를 모두 정리하세요.",
    "물린 좀비는 10초 뒤 정화됩니다.",
    "물기 성공 시 감염도가 20 오릅니다.",
    "통조림은 체력과 감염을 회복시킵니다.",
    "체력 0 또는 감염 100이면 게임 오버.",
    "20명 중 11명 이상 살리면 해피 엔딩.",
)
HELP_CONTROLS = (
    "WASD  이동   /   마우스  조준",
    "좌클릭  공격   /   B  물기",
    "우클릭  획득·조력자 명령",
    "R  주변 조력자 일괄 명령",
    "1~5  핫바   /   E  사용   /   Q  드롭",
    "I  인벤토리·제작   /   Esc  메뉴",
    "F11  전체화면 전환",
)


class ScreenFlow:
    def enter(self):
        self.state = "main"
        self.play = None
        self.loader = None
        self.images = {}
        self.ui = PlayerUI()
        self.ui.load_font()
        self.pointer = None
        self.pressed = None
        self.error = ""
        self.audio = GameAudio(ASSETS / "sound")
        self.audio.music("title")
        for path in sorted((ASSETS / "screens").glob("*.png")):
            try:
                self.images[path.stem] = p.load_image(str(path))
            except OSError:
                self.images[path.stem] = None

    def exit(self):
        self.close_play()
        self.audio.close()
        self.images.clear()
        self.ui.font = None

    def close_play(self):
        if self.loader is not None:
            self.loader.close()
            self.loader = None
        if self.play is not None:
            if self.loaded:
                self.play.exit()
            self.play = None

    def change_screen(self, state):
        previous = self.state
        self.state = state
        self.pressed = None
        self.dragging_volume = None
        if state != "play":
            self.audio.walk(False)
        if state in ("main", "help"):
            self.audio.music("title")
        elif state in ("play", "pause"):
            self.audio.music("gameplay")
        elif state == "ending":
            self.audio.music(RESULT_MUSIC[self.result])
        elif state == "error" or (state == "loading" and previous == "ending"):
            self.audio.music(None)

    def start_loading(self):
        self.close_play()
        self.play = PlayMode()
        self.play.audio = self.audio
        self.loader = self.play.load_steps()
        self.loaded = self.total = 0
        self.loading_time = 0.0
        self.loading_finish_time = 0.0
        self.loading_progress = 0.0
        self.change_screen("loading")

    def update(self, dt):
        if self.state == "play":
            self.play.update(dt)
            if self.play.ui.result is not None:
                self.result = self.play.ui.result
                actors = self.play.world.zombies
                self.population = len(actors)
                self.survivors = sum(actor.state in ("ally", "fleeing", "escaped") for actor in actors)
                self.close_play()
                self.change_screen("ending")
        elif self.state == "loading":
            self.loading_time += dt
            try:
                if self.loader is not None:
                    step = next(self.loader, None)
                    if step is None:
                        missing = next((path for path, image in self.play.images.items() if image is None), None)
                        if missing:
                            raise OSError(missing)
                        self.loader = None
                    else:
                        self.loaded, self.total = step
                        self.loading_progress = 0.9 * self.loaded / self.total
                elif self.loading_finish_time >= LOADING_FINISH_SECONDS:
                    self.change_screen("play")
                    self.play.mouse = self.pointer
                else:
                    self.loading_finish_time = min(LOADING_FINISH_SECONDS, self.loading_finish_time + dt)
                    self.loading_progress = 0.9 + 0.1 * (self.loading_finish_time / LOADING_FINISH_SECONDS)
            except OSError as error:
                self.error = str(error)
                self.close_play()
                self.change_screen("error")

    def button_at(self):
        if self.pointer is None:
            return None
        x, y = self.pointer
        for action, _, cx, cy in BUTTONS.get(self.state, ()):
            if abs(x - cx) <= 92 and abs(y - cy) <= 23:
                return action
        return None

    def handle_events(self, events):
        for event in events:
            if event.type in (p.SDL_MOUSEMOTION, p.SDL_MOUSEBUTTONDOWN, p.SDL_MOUSEBUTTONUP):
                self.pointer = (event.x, SCREEN_HEIGHT - 1 - event.y)
            if self.state == "play":
                # Esc first closes existing gameplay panels. In the world it opens the pause dialog.
                if self.play.handle_events([event]):
                    self.play.keys.clear()
                    self.change_screen("pause")
                    break
                continue
            if event.type == p.SDL_KEYDOWN and event.key == p.SDLK_ESCAPE:
                if self.state == "main":
                    return True
                if self.state == "pause":
                    self.resume()
                else:
                    self.close_play()
                    self.change_screen("main")
                break
            if self.state == "settings":
                if event.type == p.SDL_MOUSEBUTTONDOWN and event.button == p.SDL_BUTTON_LEFT:
                    x, y = self.pointer
                    self.dragging_volume = next(
                        (category for category, _, cy in VOLUME_SLIDERS
                         if SLIDER_LEFT - 10 <= x <= SLIDER_RIGHT + 10 and abs(y - cy) <= 16),
                        None,
                    )
                    if self.dragging_volume is not None:
                        self.pressed = None
                if self.dragging_volume is not None and (
                    event.type in (p.SDL_MOUSEMOTION, p.SDL_MOUSEBUTTONDOWN, p.SDL_MOUSEBUTTONUP)
                    and (event.type == p.SDL_MOUSEMOTION or event.button == p.SDL_BUTTON_LEFT)
                ):
                    percent = round((self.pointer[0] - SLIDER_LEFT) * 100 / (SLIDER_RIGHT - SLIDER_LEFT))
                    self.audio.set_volume(self.dragging_volume, percent)
                    if event.type == p.SDL_MOUSEBUTTONUP:
                        if self.dragging_volume == "effects":
                            self.audio.play("click")
                        self.dragging_volume = None
                    continue
            if event.type == p.SDL_MOUSEBUTTONDOWN and event.button == p.SDL_BUTTON_LEFT:
                self.pressed = self.button_at()
            elif event.type == p.SDL_MOUSEBUTTONUP and event.button == p.SDL_BUTTON_LEFT:
                action = self.button_at()
                pressed, self.pressed = self.pressed, None
                if action is not None and action == pressed:
                    self.audio.play("click")
                    if action == "quit":
                        return True
                    if action in ("start", "restart"):
                        self.start_loading()
                    elif action == "help":
                        self.change_screen("help")
                    elif action == "settings":
                        self.settings_origin = self.state
                        self.change_screen("settings")
                    elif action == "back" and self.state == "settings":
                        self.change_screen(self.settings_origin)
                    elif action == "cancel":
                        self.resume()
                    else:
                        self.close_play()
                        self.change_screen("main")
                    break
        return False

    def resume(self):
        self.play.mouse = self.pointer
        self.change_screen("play")

    def center_text(self, x, y, label):
        if self.ui.font is None:
            return
        width, height = c_int(), c_int()
        p.TTF_SizeUTF8(self.ui.font.font, label.encode("utf-8"), byref(width), byref(height))
        self.ui.text(x - width.value // 2, y, label)

    def draw_image(self, name, x=400, y=300):
        image = self.images.get(name)
        if image is not None:
            image.draw(x, y)

    def dim(self):
        renderer = renderer_backend.renderer
        blend = c_int()
        p.SDL_GetRenderDrawBlendMode(renderer, byref(blend))
        p.SDL_SetRenderDrawBlendMode(renderer, p.SDL_BLENDMODE_BLEND)
        try:
            p.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 0, 0, 0, 170, filled=True)
        finally:
            p.SDL_SetRenderDrawBlendMode(renderer, blend.value)

    def draw(self):
        if self.state in ("play", "pause"):
            self.play.draw()
            if self.state == "play":
                return
            self.dim()
            self.play.ui.panel(self.play.images, "panel", 240, 412, 320, 224)
            self.center_text(400, 356, "일시정지")
            self.center_text(400, 328, "메인 화면으로 돌아가시겠습니까?")
        elif self.state == "settings":
            if self.settings_origin == "pause":
                self.play.draw()
            else:
                self.draw_image("main")
            self.dim()
            p.draw_rectangle(210, 135, 590, 465, 36, 31, 31, filled=True)
            p.draw_rectangle(210, 135, 590, 465, 143, 104, 68)
            self.center_text(400, 426, "음량 설정")
            for category, label, y in VOLUME_SLIDERS:
                percent = self.audio.bgm_volume if category == "bgm" else self.audio.effects_volume
                position = SLIDER_LEFT + round((SLIDER_RIGHT - SLIDER_LEFT) * percent / 100)
                self.ui.text(SLIDER_LEFT, y + 27, label)
                self.center_text(SLIDER_RIGHT - 20, y + 27, f"{percent}%")
                p.draw_rectangle(SLIDER_LEFT, y - 4, SLIDER_RIGHT, y + 4, 74, 61, 57, filled=True)
                p.draw_rectangle(SLIDER_LEFT, y - 4, position, y + 4, 196, 149, 83, filled=True)
                p.draw_rectangle(position - 5, y - 10, position + 5, y + 10, 241, 219, 171, filled=True)
        elif self.state in ("main", "help"):
            self.draw_image("main")
            if self.state == "help":
                self.dim()
                self.draw_image("help_panel", 400, 339)
                for x, lines in ((100, HELP_GOALS), (428, HELP_CONTROLS)):
                    for row, line in enumerate(lines):
                        self.ui.text(x, 393 - row * 27, line)
        elif self.state == "loading":
            self.draw_image("loading_bg")
            mouth = self.images.get("loading_mouth")
            if mouth is not None:
                mouth.clip_draw(int(self.loading_time / 0.12) % 4 * 192, 0, 192, 128, 400, 320)
            self.draw_image("loading_track", 400, 76)
            width = int(392 * self.loading_progress)
            fill = self.images.get("loading_fill")
            if fill is not None and width:
                fill.clip_draw(0, 0, width, 16, 204 + width / 2, 76)
            self.center_text(400, 113, "로딩 중")
        elif self.state == "ending":
            self.draw_image(RESULT_IMAGES[self.result])
            if self.result in ("해피 엔딩", "새드 엔딩"):
                self.center_text(400, 88, f"회복 생존자 {self.survivors} / {self.population}")
        else:
            p.draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 24, 22, 24, filled=True)
            self.center_text(400, 330, "게임을 불러오지 못했습니다.")
            self.center_text(400, 293, self.error)

        hovered = self.button_at()
        for action, label, x, y in BUTTONS.get(self.state, ()):
            style = "normal"
            if action == hovered:
                style = "pressed" if action == self.pressed else "hover"
            name = f"button_{action}_{style}" if action in ("start", "help", "back", "settings") else f"button_{style}"
            if self.images.get(name) is not None:
                self.draw_image(name, x, y)
            else:
                p.draw_rectangle(x - 92, y - 23, x + 92, y + 23, 75, 57, 47, filled=True)
                label = label or {"start": "게임 시작", "help": "게임 설명", "back": "돌아가기",
                                  "settings": "설정"}[action]
            if label:
                self.center_text(x, y, label)
