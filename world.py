from town import BUILDING_LAYOUTS, BUILDINGS, MAP_HEIGHT, MAP_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH


class World:
    def __init__(self):
        self.buildings = []
        self.walls = []
        for kind, x, y in BUILDINGS:
            (width, height), rooms, walls = BUILDING_LAYOUTS[kind]
            left, bottom = x - width // 2, y - height // 2
            footprint = tuple((left+a, bottom+b, left+c, bottom+d) for a, b, c, d in rooms)
            self.buildings.append((kind, x, y, width, height, footprint))
            self.walls.extend((left+a, bottom+b, left+c, bottom+d) for a, b, c, d in walls)
