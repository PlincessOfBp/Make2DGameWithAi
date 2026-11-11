from math import pi
from types import SimpleNamespace as Event

from item_data import WEAPON_DAMAGE
from play_mode import PlayMode, p
from player import Player
from world import World


def key(mode, keycode, down=True):
    mode.handle_events([Event(type=p.SDL_KEYDOWN if down else p.SDL_KEYUP, key=keycode)])


def click(mode, x, y, button=p.SDL_BUTTON_LEFT):
    mode.handle_events([Event(type=p.SDL_MOUSEBUTTONDOWN, button=button, x=x, y=599-y)])


def click_world(mode, x, y, button):
    cam_x, cam_y = mode.camera
    click(mode, round(x-cam_x), round(y-cam_y), button)


def relocate(mode, x, y):
    mode.player.x, mode.player.y = x, y
    mode.camera = mode.world.camera(x, y)


def draw(mode):
    p.clear_canvas()
    mode.draw()
    p.update_canvas()


p.open_canvas()
try:
    mode = PlayMode()
    mode.enter()
    assert mode.ui.font is not None and all(image is not None for image in mode.images.values())
    player = mode.player
    inventory = player.inventory
    click_world(mode, 309, 1350, p.SDL_BUTTON_RIGHT)
    key(mode, p.SDLK_w)
    mode.update(.4)
    key(mode, p.SDLK_w, False)
    click_world(mode, 202, 1432, p.SDL_BUTTON_RIGHT)
    assert inventory.items == {"stone": 1, "axe": 1}, inventory.items
    draw(mode)

    key(mode, p.SDLK_s)
    mode.update(.4)
    key(mode, p.SDLK_s, False)
    key(mode, p.SDLK_d)
    mode.update(.56)
    key(mode, p.SDLK_d, False)
    click_world(mode, 440, 1320, p.SDL_BUTTON_LEFT)
    mode.update(.12)
    assert (440, 1320) not in mode.world.trees and inventory.items["wood"] == 1
    mode.update(.24)

    relocate(mode, 671, 1444)
    click_world(mode, 687, 1464, p.SDL_BUTTON_RIGHT)
    assert inventory.items["tape"] == 1
    key(mode, p.SDLK_i)
    draw(mode)
    click(mode, 480, 463)
    clock = mode.world.resource_time
    mode.update(5)
    assert mode.world.resource_time == clock
    draw(mode)
    click(mode, 525, 212)
    assert inventory.items == {"axe": 1, "stone_axe": 1}
    click(mode, 525, 212)
    assert inventory.items["stone_axe"] == 1
    key(mode, p.SDLK_i)
    key(mode, p.SDLK_2)
    assert inventory.slots[inventory.selected] == "stone_axe"
    draw(mode)
    mode.exit()

    mode = PlayMode()
    mode.enter()
    player = mode.player
    world = mode.world
    world.random.seed(1)
    z = world.zombies[0]
    z.x,z.y=285,1360
    mode.mouse=(285,300)
    key(mode,p.SDLK_b)
    mode.update(.12)
    assert player.infection == 10 and z.purify_at == 10.12
    mode.update(.24)
    key(mode,p.SDLK_b)
    mode.update(.12)
    assert 9.9 < player.infection < 10 and z.purify_at == 10.12
    mode.update(.24)
    world.resource_time=10.119
    mode.update(.002)
    assert z.state == "ally" and z.health==50
    click_world(mode,z.x,z.y,p.SDL_BUTTON_RIGHT)
    assert mode.ui.ally is z
    before=world.resource_time
    mode.update(.01)
    assert world.resource_time>before
    draw(mode)
    click(mode,350,312)
    assert z.command=="follow" and player.action is None and mode.ui.ally is None

    player.inventory.add("canned_food")
    player.health=65
    player.infection=31
    key(mode,p.SDLK_e)
    assert (player.health,player.infection)==(95,11)
    player.inventory.add("barricade")
    player.target_angle=-pi/2
    relocate(mode, 8, 60)
    mode.mouse = None
    player.target_angle=pi/2
    key(mode,p.SDLK_e)
    assert player.items["barricade"] == 1 and not world.barricades
    relocate(mode, 750, 450)
    player.target_angle=pi/2
    mode.handle_events([
        Event(type=p.SDL_MOUSEMOTION, x=500, y=299),
        Event(type=p.SDL_KEYDOWN, key=p.SDLK_e),
    ])
    assert world.barricades == [(814,450)] and "barricade" not in player.items
    draw(mode)
    mode.exit()
finally:
    p.close_canvas()

for item, damage in WEAPON_DAMAGE.items():
    world = World()
    player = Player()
    zombie = world.zombies[0]
    zombie.x,zombie.y=285,1360
    count = (50 + damage - 1) // damage
    for _ in range(count-1):
        world.resolve_player_action(player,"attack",-pi/2,item)
    assert zombie.state=="zombie"
    world.resolve_player_action(player,"attack",-pi/2,item)
    assert zombie.state=="dead"
print("Windows SDL rendering, pickup-to-crafting, bite timing, ally command, food, placement and all damage thresholds passed.")


