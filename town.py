SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
MAP_WIDTH, MAP_HEIGHT = 2400, 1800

# Local coordinates start at the bottom left of each building image.
# Rooms are the floor footprint, including the door threshold.
# Walls are solid rectangles (left, bottom, right, top).
BUILDING_LAYOUTS = {
    "house_small": (
        (192, 144),
        ((7, 3, 185, 140),),
        (
            (3, 3, 8, 140), (184, 3, 189, 140), (3, 136, 189, 142),
            (3, 3, 82, 9), (110, 3, 189, 9),
            (8, 87, 82, 94), (110, 87, 184, 94),
        ),
    ),
    "house_corner": (
        (216, 176),
        ((7, 3, 143, 171), (143, 97, 209, 171)),
        (
            (3, 3, 8, 172), (3, 168, 213, 174), (208, 96, 213, 172),
            (3, 3, 56, 9), (84, 3, 144, 9), (139, 3, 145, 98),
            (139, 96, 213, 102), (8, 120, 55, 127), (85, 120, 208, 127),
        ),
    ),
    "shop": (
        (264, 184),
        ((7, 3, 257, 179),),
        (
            (3, 3, 8, 180), (256, 3, 261, 180), (3, 176, 261, 182),
            (3, 3, 118, 9), (146, 3, 261, 9),
            (8, 128, 118, 135), (146, 128, 256, 135),
        ),
    ),
}

# Building scales are tuned to their lots.
BUILDING_SCALES = {
    "house_small": 1.625,
    "house_corner": 1.5,
    "shop": 1.4,
}

# Type and world-space center, aligned with the eight lots in ground.png.
BUILDINGS = (
    ("house_small", 250, 1500),
    ("house_corner", 735, 1480),
    ("shop", 1615, 1550),
    ("shop", 2110, 1540),
    ("house_corner", 330, 770),
    ("house_small", 805, 780),
    ("house_small", 2130, 620),
    ("house_small", 1730, 300),
)

# Prop name, local sprite center, and solid footprint size.
FURNITURE = {
    "house_small": (("table", 139, 53, 54, 30),),
    "house_corner": (("table", 105, 55, 54, 30),),
    "shop": (
        ("shelf", 53, 94, 48, 32),
        ("shelf", 210, 94, 48, 32),
        ("checkout", 199, 43, 62, 35),
    ),
}

# Outdoor positions use world coordinates. Tree positions mark the trunks.
TREE_TRUNKS = (
    (70, 1595), (485, 1535), (1010, 1540), (440, 1320), (920, 1280),
    (1340, 1575), (1860, 1490), (2340, 1460), (1460, 1265), (2190, 1280),
    (110, 845), (550, 840), (1035, 830), (100, 220), (470, 150), (950, 220),
    (1385, 450), (1550, 695), (1790, 810), (2170, 842), (2340, 350), (1960, 290),
)
TREE_TRUNK_HALF_WIDTH = 11
TREE_TRUNK_HALF_HEIGHT = 8
TREE_DRAW_OFFSET = 49

# One stone may be active at each outdoor spawn point.
STONE_POINTS = (
    (309, 1350), (540, 1450), (958, 1670), (1325, 1450),
    (1815, 1300), (2330, 1250), (530, 730), (1000, 690),
    (540, 235), (1470, 535), (1770, 660), (2260, 322),
)
STONE_RESPAWN_SECONDS = 20
STONE_SPAWN_CLEARANCE = 24

# Each entry matches BUILDINGS by index. Offsets use each building center.
FARMING_LOOT = (
    (("axe", -48, -68), ("canned_food", 32, -48)),
    (("nails", -80, -68), ("tape", -48, -16)),
    (("canned_food", -45, -48), ("tape", 42, -20)),
    (("axe", -45, -48), ("nails", 42, -20)),
    (("canned_food", -80, -68), ("nails", -48, -16)),
    (("tape", -48, -68), ("canned_food", 32, -48)),
    (("nails", -48, -68), ("tape", 32, -48)),
    (("canned_food", -48, -68), ("axe", 32, -48)),
)

ZOMBIE_POINTS = (
    (580, 1320), (990, 1350), (960, 1655), (72, 1730), (420, 1755),
    (1350, 1650), (1850, 1690), (2310, 1580), (1700, 1285), (2230, 1265),
    (1080, 880), (565, 720), (152, 725), (210, 405), (850, 275),
    (1400, 705), (1740, 790), (1830, 505), (2180, 320), (2240, 835),
)
TREE_RESPAWN_SECONDS = 30
PICKUP_REACH = 64
PICKUP_ICON_HALF_SIZE = 16
