from logging import getLogger
from random import Random
from time import monotonic

import pico2d as p


EFFECTS = {
    "bite": (112, ("biting",)),
    "zombie_bite": (65, ("zombie-bite",)),
    "zombie_voice": (43, ("zombie1", "zombie2")),
    "step": (35, ("walking",)),
    "swing": (53, ("swish",)),
    "hit": (66, ("hard-slap",)),
    "tree": (67, ("hit-tree",)),
    "craft": (64, ("make",)),
    "eat": (65, ("eat",)),
    "click": (55, ("click",)),
    "ally_hello": (60, ("helper-hello1", "helper-hello2")),
    "ally_order": (59, ("helper-ok",)),
    "ally_death": (63, ("helper-dead1", "helper-dead2")),
    "runaway": (56, ("runaway-1", "runaway-2")),
}
MUSIC = {
    "title": 48,
    "gameplay": 36,
    "ending_loss": 48,
    "ending_infection": 48,
    "ending_happy": 48,
}
LOG = getLogger(__name__)
WALK_CHANNEL = 0
BITE_CHANNEL = 1


class GameAudio:
    def __init__(self, root):
        self.effects = {}
        self.tracks = {}
        self.current = None
        self.random = Random()
        self.next_voice_at = 0.0
        self.walking = False
        for event, (volume, names) in EFFECTS.items():
            clips = []
            for name in names:
                clip = self.load(p.load_wav, root / f"{name}.mp3")
                if clip is not None:
                    clip.set_volume(volume)
                    clips.append(clip)
            self.effects[event] = clips
        for name in MUSIC:
            self.tracks[name] = self.load(p.load_music, root / "bgm" / f"{name}.wav")
        if self.effects["bite"]:
            # A successful bite must be audible even when all shared channels are busy.
            p.Mix_ReserveChannels(BITE_CHANNEL + 1)
        elif self.effects["step"]:
            p.Mix_ReserveChannels(1)

    @staticmethod
    def load(loader, path):
        try:
            return loader(str(path))
        except OSError:
            LOG.warning("Cannot load audio: %s", path)
            return None

    def music(self, name):
        if name == self.current:
            return
        previous = self.tracks.get(self.current)
        if previous is not None:
            previous.stop()
        self.current = name
        track = self.tracks.get(name)
        if track is not None:
            track.set_volume(MUSIC[name])
            track.repeat_play()

    def play(self, event):
        clips = self.effects[event]
        if not clips:
            return
        if event == "bite":
            p.Mix_PlayChannel(BITE_CHANNEL, clips[0].wav, 0)
            return
        if event == "zombie_voice":
            now = monotonic()
            if now < self.next_voice_at:
                return
            self.next_voice_at = now + 1.4
        self.random.choice(clips).play()

    def close(self):
        self.music(None)
        if any(self.effects.values()):
            p.Mix_HaltChannel(-1)
        self.effects.clear()
        self.tracks.clear()

    def walk(self, moving):
        clips = self.effects["step"]
        if not clips or moving == self.walking:
            return
        self.walking = moving
        if moving:
            p.Mix_PlayChannel(WALK_CHANNEL, clips[0].wav, -1)
        else:
            p.Mix_HaltChannel(WALK_CHANNEL)
