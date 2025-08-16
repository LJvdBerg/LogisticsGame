import math
import random
import sys
from dataclasses import dataclass
from typing import Dict, Set, Tuple, Optional, List

import pygame


WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60

GRID_SIZE = 32
BG_COLOR = (28, 28, 35)
GRID_COLOR = (60, 60, 70)
GRID_BOLD_COLOR = (85, 85, 100)
ROAD_COLOR = (180, 180, 180)
ROAD_OUTLINE = (110, 110, 110)
BASE_COLOR = (255, 200, 80)
UI_TEXT = (235, 235, 245)
TREE_COLOR = (40, 145, 75)
TREE_DARK = (25, 100, 55)
LUMBER_COLOR = (160, 120, 60)
UI_BAR_BG = (45, 45, 52)
UI_BAR_BORDER = (80, 80, 95)
TRUCK_COLOR = (200, 160, 60)
TRUCK_OUTLINE = (100, 80, 40)
STONE_COLOR = (120, 120, 125)
STONE_COLOR_DARK = (90, 90, 95)
REFINERY_COLOR = (120, 140, 170)


Coord = Tuple[int, int]


# NOTE: For brevity and to avoid duplication, this file would mirror the current Game class
# from main.py. In a real refactor we would move all logic here and import in main.py.
# For now, we leave this file as a placeholder to structure the project.


