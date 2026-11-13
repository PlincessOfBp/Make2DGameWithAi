ITEM_NAMES = {
    "wood": "나무", "stone": "돌멩이", "axe": "도끼", "nails": "못", "tape": "테이프",
    "canned_food": "통조림", "knife": "나이프", "stone_axe": "돌도끼",
    "nailed_bat": "못 박힌 방망이", "barricade": "바리케이트",
}
ITEM_ICON_CELLS = {
    item: (index % 5 * 32, 32 - index // 5 * 32)
    for index, item in enumerate(ITEM_NAMES)
}
RECIPES = {
    "stone_axe": {"wood": 1, "stone": 1, "tape": 1},
    "nailed_bat": {"wood": 2, "nails": 2},
    "barricade": {"wood": 3, "nails": 2},
}
WEAPON_DAMAGE = {None: 5, "knife": 10, "stone_axe": 13, "nailed_bat": 17, "axe": 25}
WEAPON_COLUMNS = {"knife": 0, "stone_axe": 1, "nailed_bat": 2, "axe": 3}
TOOL_DURABILITY = {"knife": 30, "stone_axe": 24, "nailed_bat": 36, "axe": 48}
TREE_MAX_HP = 60
TREE_DAMAGE = {"axe": 30, "stone_axe": 20}
HOTBAR_ITEMS = {*WEAPON_COLUMNS, "canned_food", "barricade"}
