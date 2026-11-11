from town import BUILDING_LAYOUTS, BUILDINGS, FURNITURE, MAP_HEIGHT, MAP_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH


class World:
    def __init__(self):
        self.buildings = []
        self.walls = []
        self.furniture = {}
        for kind, x, y in BUILDINGS:
            (width, height), rooms, walls = BUILDING_LAYOUTS[kind]
            left, bottom = x - width // 2, y - height // 2
            footprint = tuple((left+a, bottom+b, left+c, bottom+d) for a, b, c, d in rooms)
            furniture = tuple((name, left + px, bottom + py)
                              for name, px, py, _, _ in FURNITURE[kind])
            self.buildings.append((kind, x, y, width, height, footprint))
            self.furniture[x, y] = furniture
            for _, px, py, prop_width, prop_height in FURNITURE[kind]:
                cx, cy = left + px, bottom + py
                half_width, half_height = prop_width / 2, prop_height / 2
                self.walls.append((cx - half_width, cy - half_height,
                                   cx + half_width, cy + half_height))
            self.walls.extend((left+a, bottom+b, left+c, bottom+d) for a, b, c, d in walls)


    def camera(self, x, y):
        return (
            min(max(round(x) - SCREEN_WIDTH // 2, 0), MAP_WIDTH - SCREEN_WIDTH),
            min(max(round(y) - SCREEN_HEIGHT // 2, 0), MAP_HEIGHT - SCREEN_HEIGHT),
        )


    def move(self, x, y, dx, dy, radius):
        # Sweep each axis separately so the actor can slide along a wall.
        next_x = min(max(x + dx, radius), MAP_WIDTH - radius)
        for left, bottom, right, top in self.walls:
            if bottom - radius < y < top + radius:
                if x <= left - radius:
                    next_x = min(next_x, left - radius)
                elif x >= right + radius:
                    next_x = max(next_x, right + radius)

        next_y = min(max(y + dy, radius), MAP_HEIGHT - radius)
        for left, bottom, right, top in self.walls:
            if left - radius < next_x < right + radius:
                if y <= bottom - radius:
                    next_y = min(next_y, bottom - radius)
                elif y >= top + radius:
                    next_y = max(next_y, top + radius)
        return next_x, next_y
