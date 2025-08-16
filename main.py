import math
import random
import sys
from dataclasses import dataclass
from typing import Dict, Set, Tuple, Optional, List

import pygame
from bulldoze import BulldozeManager
from truck_sprite import TruckSprite
from truck_factory import TruckFactory
from truck_selector import TruckSelector


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


@dataclass(frozen=True)
class RoadCell:
    x: int
    y: int


@dataclass
class Building:
    type: str
    cell: Coord
    radius_cells: int
    production_rate_per_sec: float
    storage: Dict[str, float]


@dataclass
class Truck:
    truck_id: int
    position_px: Tuple[float, float]
    current_cell: Coord
    path_cells: List[Coord]
    speed_px_per_sec: float
    state: str  # 'idle' | 'to_source' | 'loading' | 'to_dest' | 'unloading' | 'waiting_for_bmats'
    cargo_type: Optional[str]
    cargo_amount: float
    cargo_capacity: float
    repeat_enabled: bool = False
    saved_source: Optional[Coord] = None
    saved_dest: Optional[Coord] = None
    saved_resource: Optional[str] = None
    marker_color: Tuple[int, int, int] = (255, 235, 120)
    path_color: Tuple[int, int, int] = (120, 200, 230)
    current_direction: Tuple[float, float] = (1, 0)  # Default facing right


@dataclass
class Assignment:
    active: bool = False
    source_cell: Optional[Coord] = None
    destination_cell: Optional[Coord] = None
    truck_id: Optional[int] = None
    resource_type: Optional[str] = None


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Logistics Game - Prototype")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)

        # World state
        self.build_mode: bool = False
        self.grid_visible: bool = False
        self.roads: Set[Coord] = set()
        # Binary road grid: 1 = driveable road, 0 = not driveable
        self.road_grid: Dict[Coord, int] = {}
        self.trees: Set[Coord] = set()
        self.stones: Set[Coord] = set()
        self.resources: Dict[str, int] = {
            "oil": 0,
            "steel": 0,
            "wood": 0,
            "stone": 0,
            "bmats": 10,
        }
        self.resource_fractional_buffer: Dict[str, float] = {"wood": 0.0}
        self.buildings: List[Building] = []
        self.current_tool: str = "road"  # 'road' | 'lumber' | 'quarry' | 'refinery'

        # Trucks and assignments
        self.trucks: List[Truck] = []
        self.next_truck_id: int = 1
        self.pending_source: Optional[Coord] = None
        self.pending_truck_id: Optional[int] = None
        self.pending_resource: Optional[str] = None
        self.pending_destination: Optional[Coord] = None
        self.assign_stage: str = "idle"  # 'idle' | 'choose_truck' | 'choose_source' | 'choose_resource' | 'confirm'

        # Camera (pixel offset from world origin)
        self.camera_x: int = 0
        self.camera_y: int = 0

        # Mouse drag state for painting roads
        self.is_dragging: bool = False
        self.last_painted_cell: Coord | None = None

        # Mouse drag state for panning in explore mode
        self.is_panning: bool = False
        self.last_mouse_pos: Tuple[int, int] | None = None

        # Build preview state (for lumber camp)
        self.preview_cell: Optional[Coord] = None

        # Base spawn within viewport
        max_cells_x = WINDOW_WIDTH // GRID_SIZE
        max_cells_y = WINDOW_HEIGHT // GRID_SIZE
        self.base_cell: Coord = (
            random.randint(2, max(2, max_cells_x - 3)),
            random.randint(2, max(2, max_cells_y - 3)),
        )

        # Scatter trees and stones around the starting area (avoid base cell)
        self._generate_resources_around_view(max_cells_x, max_cells_y)

        # Bulldoze manager
        self.bulldoze_manager = BulldozeManager()
        
        # Truck sprite manager
        self.truck_sprite = TruckSprite()
        
        # Truck factory
        self.truck_factory = TruckFactory()
        
        # Truck selector
        self.truck_selector = TruckSelector()
        
        # Mark base area as driveable
        bx, by = self.base_cell
        for dx in range(2):
            for dy in range(2):
                self.road_grid[(bx + dx, by + dy)] = 1
        
        # Starting trucks at base
        self.spawn_starting_truck()
        self.spawn_starting_truck()
        # Update truck factory count for starting trucks
        self.truck_factory.trucks_built = 2

    def spawn_starting_truck(self) -> None:
        self.spawn_truck_at_base()
        
    def spawn_truck_at_base(self) -> None:
        """Spawn a new truck at the base"""
        bx, by = self.base_cell
        px = bx * GRID_SIZE + GRID_SIZE // 2
        py = by * GRID_SIZE + GRID_SIZE // 2
        # 1.2 tiles/sec
        colors = [
            ((255, 235, 120), (120, 200, 230)),
            ((255, 140, 140), (235, 140, 140)),
            ((140, 255, 170), (120, 220, 160)),
            ((180, 180, 255), (150, 150, 235)),
        ]
        mc, pc = colors[(self.next_truck_id - 1) % len(colors)]
        truck = Truck(
            truck_id=self.next_truck_id,
            position_px=(float(px), float(py)),
            current_cell=(bx, by),
            path_cells=[],
            speed_px_per_sec=GRID_SIZE * 1.2,
            state="idle",
            cargo_type=None,
            cargo_amount=0.0,
            cargo_capacity=20.0,
            marker_color=mc,
            path_color=pc,
            current_direction=(1, 0),  # Default facing right
        )
        self.next_truck_id += 1
        self.trucks.append(truck)

    def _generate_resources_around_view(self, view_cells_x: int, view_cells_y: int) -> None:
        area_min_x = -view_cells_x
        area_max_x = view_cells_x * 2
        area_min_y = -view_cells_y
        area_max_y = view_cells_y * 2
        # Half the previous density
        num_trees = max(75, (view_cells_x * view_cells_y) // 4)
        attempts = 0
        while len(self.trees) < num_trees and attempts < num_trees * 10:
            attempts += 1
            cx = random.randint(area_min_x, area_max_x)
            cy = random.randint(area_min_y, area_max_y)
            cell = (cx, cy)
            if self.is_cell_in_base_area(cell):
                continue
            self.trees.add(cell)
        # Stones: around 1/4 of the amount of trees
        target_stones = max(10, len(self.trees) // 4)
        attempts = 0
        while len(self.stones) < target_stones and attempts < target_stones * 20:
            attempts += 1
            cx = random.randint(area_min_x, area_max_x)
            cy = random.randint(area_min_y, area_max_y)
            cell = (cx, cy)
            if self.is_cell_in_base_area(cell) or cell in self.trees:
                continue
            self.stones.add(cell)

    # -------- Input --------
    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                if event.key == pygame.K_SPACE:
                    # Toggle truck menu: if already showing, hide it; if not showing, show it
                    if self.assign_stage == "choose_truck":
                        # Menu is already open, close it
                        self.clear_pending_selection()
                        print("Closed truck menu")
                    else:
                        # Menu is not open, open it and go to base
                        self.center_camera_on_base()
                        self.pending_destination = self.base_cell
                        self.assign_stage = "choose_truck"
                        print("Opened truck menu")
                if event.key == pygame.K_b:
                    self.build_mode = not self.build_mode
                    self.grid_visible = self.build_mode
                    self.is_dragging = False
                    self.last_painted_cell = None
                # Truck selection with number keys 1-9
                if pygame.K_1 <= event.key <= pygame.K_9:
                    truck_number = event.key - pygame.K_0  # Convert key to number
                    if truck_number <= len(self.trucks):
                        # If same truck is already selected, deselect it
                        if self.truck_selector.selected_truck_id == truck_number:
                            self.truck_selector.selected_truck_id = None
                            print(f"Deselected Truck {truck_number}")
                        else:
                            # Select the new truck
                            self.truck_selector.selected_truck_id = truck_number
                            print(f"Selected Truck {truck_number}")
                            # Center camera on the selected truck
                            selected_truck = self.get_truck_by_id(truck_number)
                            if selected_truck:
                                self.center_camera_on_cell(selected_truck.current_cell)
                    else:
                        print(f"No truck {truck_number} available")

            if self.build_mode:
                # UI bar interactions take priority
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    bar_rects = self.get_build_bar_rects()
                    for tool, rect in bar_rects.items():
                        if rect.collidepoint(mx, my):
                            self.current_tool = tool
                            # Cancel any ongoing drag
                            self.is_dragging = False
                            self.last_painted_cell = None
                            break
                    else:
                        # Not clicking on UI; handle tool-specific actions
                        if self.current_tool == "road":
                            self.is_dragging = True
                            cell = self.world_to_cell((mx, my))
                            self.paint_cell(cell)
                            self.last_painted_cell = cell
                        elif self.current_tool == "lumber":
                            cell = self.world_to_cell((mx, my))
                            self.place_lumber_camp(cell)
                        elif self.current_tool == "quarry":
                            cell = self.world_to_cell((mx, my))
                            self.place_quarry(cell)
                        elif self.current_tool == "refinery":
                            cell = self.world_to_cell((mx, my))
                            self.place_refinery(cell)
                        elif self.current_tool == "bulldoze":
                            # Check if clicking on confirm button first
                            if self.bulldoze_manager.handle_click((mx, my)):
                                self.execute_bulldoze()
                            else:
                                cell = self.world_to_cell((mx, my))
                                self.bulldoze_manager.start_drag(cell)
                                self.last_painted_cell = cell
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.current_tool == "bulldoze":
                        self.bulldoze_manager.end_drag()
                    else:
                        self.is_dragging = False
                        self.last_painted_cell = None
                if event.type == pygame.MOUSEMOTION:
                    if self.current_tool == "lumber":
                        self.preview_cell = self.world_to_cell(pygame.mouse.get_pos())
                    elif self.current_tool == "quarry":
                        self.preview_cell = self.world_to_cell(pygame.mouse.get_pos())
                    elif self.current_tool == "refinery":
                        self.preview_cell = self.world_to_cell(pygame.mouse.get_pos())
                    elif self.current_tool == "bulldoze" and self.bulldoze_manager.is_dragging:
                        cell = self.world_to_cell(pygame.mouse.get_pos())
                        self.bulldoze_manager.update_drag(cell)
            else:
                # Explore mode: hold LMB and drag to pan
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # If clicking on UI panel, handle that first
                    if self.handle_explore_ui_click(pygame.mouse.get_pos()):
                        pass
                    # Check if clicking on reset button in truck info panel
                    elif (self.truck_selector.selected_truck_id and 
                          self.truck_selector.handle_reset_click(pygame.mouse.get_pos())):
                        selected_truck = self.get_truck_by_id(self.truck_selector.selected_truck_id)
                        if selected_truck:
                            self.truck_selector.reset_truck(selected_truck)
                            print(f"Reset Truck {self.truck_selector.selected_truck_id}")
                    else:
                        clicked_cell = self.world_to_cell(pygame.mouse.get_pos())
                        if self.assign_stage == "idle":
                            # Start assignment by clicking the base OR a source facility
                            if self.is_cell_in_base_area(clicked_cell):
                                self.pending_destination = self.base_cell
                                self.assign_stage = "choose_truck"
                                return
                            else:
                                b = self.get_building_at_cell(clicked_cell)
                                if b is not None:
                                    print(f"Clicked on building: {b.type} at {clicked_cell}")
                                    if b.type in ("lumber", "quarry"):
                                        # Lumber and quarry are sources - they produce resources
                                        self.pending_source = clicked_cell
                                        self.pending_destination = self.base_cell
                                        self.assign_stage = "choose_truck"
                                        print(f"Starting truck assignment for {b.type} (source)")
                                        return
                                    elif b.type == "refinery":
                                        # Refinery is a destination - it needs stone delivered
                                        # For refinery, we'll set up a route from base (which has stone) to refinery
                                        self.pending_source = self.base_cell  # Base has stone
                                        self.pending_destination = clicked_cell  # Refinery needs stone
                                        self.assign_stage = "choose_truck"
                                        print(f"Refinery selected: Base → Refinery route (stone delivery)")
                                        return
                        elif self.assign_stage == "choose_source":
                            # Select source facility
                            b = self.get_building_at_cell(clicked_cell)
                            if b is not None and b.type in ("lumber", "quarry", "refinery"):
                                self.pending_source = clicked_cell
                                self.assign_stage = "choose_resource"
                                return
                        # Otherwise begin panning
                        self.is_panning = True
                        self.last_mouse_pos = pygame.mouse.get_pos()
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.is_panning = False
                    self.last_mouse_pos = None
                if event.type == pygame.MOUSEMOTION and self.is_panning and self.last_mouse_pos is not None:
                    mx, my = pygame.mouse.get_pos()
                    lx, ly = self.last_mouse_pos
                    dx = mx - lx
                    dy = my - ly
                    # Drag world with cursor
                    self.camera_x -= dx
                    self.camera_y -= dy
                    self.last_mouse_pos = (mx, my)

        if self.build_mode and self.is_dragging and self.current_tool == "road":
            current_cell = self.world_to_cell(pygame.mouse.get_pos())
            if self.last_painted_cell is None or current_cell != self.last_painted_cell:
                # Paint along the line between last and current to avoid gaps while dragging fast
                if self.last_painted_cell is not None:
                    for cell in self.cells_on_line(self.last_painted_cell, current_cell):
                        self.paint_cell(cell)
                else:
                    self.paint_cell(current_cell)
                self.last_painted_cell = current_cell

    # -------- World helpers --------
    def world_to_cell(self, pos: Tuple[int, int]) -> Coord:
        # Convert screen pixel to world cell using camera offset
        x, y = pos
        world_px_x = x + self.camera_x
        world_px_y = y + self.camera_y
        return (world_px_x // GRID_SIZE, world_px_y // GRID_SIZE)

    def cell_to_rect(self, cell: Coord) -> pygame.Rect:
        # Convert world cell to on-screen rect using camera offset
        cx, cy = cell
        return pygame.Rect(
            cx * GRID_SIZE - self.camera_x,
            cy * GRID_SIZE - self.camera_y,
            GRID_SIZE,
            GRID_SIZE,
        )

    def paint_cell(self, cell: Coord) -> None:
        # Do not build on trees or existing roads
        if cell in self.trees or cell in self.stones or cell in self.roads:
            return
        # Require BMATs to build
        if self.resources.get("bmats", 0) <= 0:
            return
        self.roads.add(cell)
        self.road_grid[cell] = 1  # Mark as driveable road
        self.resources["bmats"] -= 1

    def can_place_lumber(self, cell: Coord) -> bool:
        if cell in self.trees or cell in self.stones:
            return False
        if cell in self.roads:
            return False
        for b in self.buildings:
            if b.cell == cell:
                return False
        # Don't allow building directly adjacent to base (including diagonals)
        if self.is_cell_adjacent_to_base(cell):
            return False
        return True

    def place_lumber_camp(self, cell: Coord) -> None:
        if not self.can_place_lumber(cell):
            return
        radius_cells = 5
        tree_count = self.count_trees_in_radius(cell, radius_cells)
        # Production scales with trees in radius (0.2 wood/sec per tree)
        production_rate = tree_count * 0.2
        self.buildings.append(
            Building(type="lumber", cell=cell, radius_cells=radius_cells, production_rate_per_sec=production_rate, storage={"wood": 0.0})
        )
        # Mark facility cell as driveable so trucks can enter
        self.road_grid[cell] = 1

    def can_place_quarry(self, cell: Coord) -> bool:
        if cell in self.trees or cell in self.stones:
            return False
        if cell in self.roads:
            return False
        for b in self.buildings:
            if b.cell == cell:
                return False
        # Don't allow building directly adjacent to base (including diagonals)
        if self.is_cell_adjacent_to_base(cell):
            return False
        return True

    def place_quarry(self, cell: Coord) -> None:
        if not self.can_place_quarry(cell):
            return
        radius_cells = 5
        stone_count = self.count_stones_in_radius(cell, radius_cells)
        production_rate = stone_count * 0.2
        self.buildings.append(
            Building(type="quarry", cell=cell, radius_cells=radius_cells, production_rate_per_sec=production_rate, storage={"stone": 0.0})
        )
        # Mark facility cell as driveable so trucks can enter
        self.road_grid[cell] = 1

    def can_place_refinery(self, cell: Coord) -> bool:
        if cell in self.trees or cell in self.stones:
            return False
        if cell in self.roads:
            return False
        for b in self.buildings:
            if b.cell == cell:
                return False
        # Don't allow building directly adjacent to base (including diagonals)
        if self.is_cell_adjacent_to_base(cell):
            return False
        return True

    def place_refinery(self, cell: Coord) -> None:
        if not self.can_place_refinery(cell):
            return
        # Refineries convert stone to bmats: 1 stone = 1 bmat every 5 seconds
        self.buildings.append(
            Building(type="refinery", cell=cell, radius_cells=0, production_rate_per_sec=0.2, storage={"stone": 0.0, "bmats": 0.0})
        )
        # Mark facility cell as driveable so trucks can enter
        self.road_grid[cell] = 1

    def execute_bulldoze(self) -> None:
        """Execute bulldoze operation on all highlighted cells"""
        for cell in self.bulldoze_manager.highlighted_cells:
            if cell in self.roads:
                self.roads.remove(cell)
                self.road_grid[cell] = 0  # Mark as not driveable
                self.resources["bmats"] += 1  # Refund
            else:
                # Check if there's a building here
                for i, b in enumerate(list(self.buildings)):
                    if b.cell == cell:
                        # Remove from road grid if it was a facility
                        if b.cell in self.road_grid:
                            self.road_grid[b.cell] = 0
                        del self.buildings[i]
                        break
        
        # Clear the highlight after execution
        self.bulldoze_manager.clear_highlight()

    def build_new_truck(self) -> None:
        """Build a new truck if player has enough BMATS"""
        cost = self.truck_factory.get_truck_cost()
        if self.resources.get("bmats", 0) >= cost:
            self.resources["bmats"] -= cost
            self.spawn_truck_at_base()
            self.truck_factory.build_truck()
            print(f"Built new truck for {cost} BMATS! Total trucks: {len(self.trucks)}")
        else:
            print(f"Not enough BMATS! Need {cost}, have {self.resources.get('bmats', 0)}")

    def bulldoze_at(self, cell: Coord) -> None:
        # Refund rules:
        # - Road cell → +1 BMAT and remove road
        # - Building (lumber/refinery) → no cost yet, simply remove
        if cell in self.roads:
            self.roads.remove(cell)
            self.resources["bmats"] += 1
            return
        for i, b in enumerate(list(self.buildings)):
            if b.cell == cell:
                # Simple refund logic placeholder; could refund some materials later
                del self.buildings[i]
                return

    def count_trees_in_radius(self, center_cell: Coord, radius_cells: int) -> int:
        rc2 = radius_cells * radius_cells
        cx, cy = center_cell
        count = 0
        for tx, ty in self.trees:
            dx = tx - cx
            dy = ty - cy
            if dx * dx + dy * dy <= rc2:
                count += 1
        return count

    def count_stones_in_radius(self, center_cell: Coord, radius_cells: int) -> int:
        rc2 = radius_cells * radius_cells
        cx, cy = center_cell
        count = 0
        for sx, sy in self.stones:
            dx = sx - cx
            dy = sy - cy
            if dx * dx + dy * dy <= rc2:
                count += 1
        return count

    def cells_on_line(self, start: Coord, end: Coord) -> Set[Coord]:
        # Bresenham's line algorithm over grid cells
        x0, y0 = start
        x1, y1 = end
        cells: Set[Coord] = set()

        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        x, y = x0, y0
        while True:
            cells.add((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return cells

    # -------- Rendering --------
    def draw_grid(self) -> None:
        if not self.grid_visible:
            return
        # Minor grid aligned to camera
        start_x = -(self.camera_x % GRID_SIZE)
        start_y = -(self.camera_y % GRID_SIZE)
        for x in range(start_x, WINDOW_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(start_y, WINDOW_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))

        # Bold lines every 4 cells (overlay)
        for x in range(start_x, WINDOW_WIDTH, GRID_SIZE):
            world_cell_x = (x + self.camera_x) // GRID_SIZE
            if world_cell_x % 4 == 0:
                pygame.draw.line(self.screen, GRID_BOLD_COLOR, (x, 0), (x, WINDOW_HEIGHT), 2)
        for y in range(start_y, WINDOW_HEIGHT, GRID_SIZE):
            world_cell_y = (y + self.camera_y) // GRID_SIZE
            if world_cell_y % 4 == 0:
                pygame.draw.line(self.screen, GRID_BOLD_COLOR, (0, y), (WINDOW_WIDTH, y), 2)

    def draw_roads(self) -> None:
        for cell in self.roads:
            rect = self.cell_to_rect(cell)
            pygame.draw.rect(self.screen, ROAD_COLOR, rect)
            pygame.draw.rect(self.screen, ROAD_OUTLINE, rect, 1)

    def draw_base(self) -> None:
        rect = self.cell_to_rect(self.base_cell)
        # Make base 2x2 instead of 1x1
        base_rect = pygame.Rect(
            rect.x,
            rect.y,
            rect.w * 2,
            rect.h * 2,
        )
        pygame.draw.rect(self.screen, BASE_COLOR, base_rect, border_radius=6)
        
        # Base label and truck factory button removed - will be in truck selection panel instead

    def draw_trees(self) -> None:
        for cell in self.trees:
            rect = self.cell_to_rect(cell)
            center = (rect.centerx, rect.centery)
            radius = GRID_SIZE // 2 - 4
            pygame.draw.circle(self.screen, TREE_COLOR, center, radius)
            pygame.draw.circle(self.screen, TREE_DARK, center, radius, 2)

    def draw_stones(self) -> None:
        for cell in self.stones:
            rect = self.cell_to_rect(cell)
            center = (rect.centerx, rect.centery)
            # 50% bigger than trees but clamp to cell
            radius = min(GRID_SIZE // 2 - 2, int((GRID_SIZE // 2 - 4) * 1.5))
            # Not a perfect circle: draw two overlapping blobs
            pygame.draw.circle(self.screen, STONE_COLOR, (center[0] - 2, center[1]), radius)
            pygame.draw.circle(self.screen, STONE_COLOR, (center[0] + 3, center[1] - 1), int(radius * 0.9))
            pygame.draw.circle(self.screen, STONE_COLOR_DARK, center, radius, 2)

    def draw_buildings(self) -> None:
        for b in self.buildings:
            if b.type == "lumber":
                rect = self.cell_to_rect(b.cell)
                pygame.draw.rect(self.screen, LUMBER_COLOR, rect, border_radius=4)
                # No text on building - only in popup UI
            elif b.type == "quarry":
                rect = self.cell_to_rect(b.cell)
                pygame.draw.rect(self.screen, REFINERY_COLOR, rect, border_radius=4)
                # No text on building - only in popup UI
            elif b.type == "refinery":
                rect = self.cell_to_rect(b.cell)
                pygame.draw.rect(self.screen, (180, 120, 80), rect, border_radius=4)  # Brown color for refinery
                # No text on building - only in popup UI

    def draw_trucks(self) -> None:
        for t in self.trucks:
            # Calculate direction for sprite rotation
            direction = t.current_direction
            if t.path_cells:
                # Use grid-aligned direction calculation for perfect 90-degree rotations
                new_direction = self.truck_sprite.get_grid_aligned_direction(
                    t.position_px, t.path_cells, t.current_direction
                )
                t.current_direction = new_direction
                direction = new_direction
            
            # Draw the truck sprite
            self.truck_sprite.draw_truck(
                self.screen, 
                t.position_px, 
                direction, 
                self.camera_x, 
                self.camera_y
            )
            
            # Truck ID is now displayed by the truck selector system

    def draw_truck_paths(self) -> None:
        node_radius = 4
        for t in self.trucks:
            for cell in t.path_cells:
                cx = cell[0] * GRID_SIZE + GRID_SIZE // 2 - self.camera_x
                cy = cell[1] * GRID_SIZE + GRID_SIZE // 2 - self.camera_y
                pygame.draw.circle(self.screen, t.path_color, (int(cx), int(cy)), node_radius, 1)

    def draw_truck_markers(self) -> None:
        # Moving marker at the truck's live position
        for t in self.trucks:
            mx = int(t.position_px[0] - self.camera_x)
            my = int(t.position_px[1] - self.camera_y)
            pygame.draw.circle(self.screen, t.marker_color, (mx, my), 6, 2)

    def draw_lumber_preview(self) -> None:
        if not self.build_mode or self.current_tool != "lumber" or self.preview_cell is None:
            return
        cx, cy = self.preview_cell
        radius_cells = 5
        radius_px = radius_cells * GRID_SIZE
        center_px = (
            cx * GRID_SIZE + GRID_SIZE // 2 - self.camera_x,
            cy * GRID_SIZE + GRID_SIZE // 2 - self.camera_y,
        )
        overlay = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (60, 170, 90, 50), (radius_px, radius_px), radius_px)
        pygame.draw.circle(overlay, (60, 200, 110, 120), (radius_px, radius_px), radius_px, 2)
        self.screen.blit(overlay, (center_px[0] - radius_px, center_px[1] - radius_px))
        # Draw preview building footprint
        brect = self.cell_to_rect(self.preview_cell)
        pygame.draw.rect(self.screen, LUMBER_COLOR, brect, 2, border_radius=4)

    def draw_quarry_preview(self) -> None:
        if not self.build_mode or self.current_tool != "quarry" or self.preview_cell is None:
            return
        cx, cy = self.preview_cell
        radius_cells = 5
        radius_px = radius_cells * GRID_SIZE
        center_px = (
            cx * GRID_SIZE + GRID_SIZE // 2 - self.camera_x,
            cy * GRID_SIZE + GRID_SIZE // 2 - self.camera_y,
        )
        overlay = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (150, 160, 185, 50), (radius_px, radius_px), radius_px)
        pygame.draw.circle(overlay, (170, 180, 200, 120), (radius_px, radius_px), radius_px, 2)
        self.screen.blit(overlay, (center_px[0] - radius_px, center_px[1] - radius_px))
        brect = self.cell_to_rect(self.preview_cell)
        pygame.draw.rect(self.screen, REFINERY_COLOR, brect, 2, border_radius=4)

    def draw_refinery_preview(self) -> None:
        if not self.build_mode or self.current_tool != "refinery" or self.preview_cell is None:
            return
        # Refinery is just a single cell, no radius needed
        brect = self.cell_to_rect(self.preview_cell)
        pygame.draw.rect(self.screen, (180, 120, 80), brect, 2, border_radius=4)

    def draw_building_info_panels(self) -> None:
        """Draw info panels for buildings when clicked"""
        if self.build_mode:
            return
            
        # Check if we're hovering over a building
        mouse_pos = pygame.mouse.get_pos()
        hover_cell = self.world_to_cell(mouse_pos)
        building = self.get_building_at_cell(hover_cell)
        
        if building:
            if building.type == "refinery":
                # Draw refinery info panel
                self.draw_refinery_info_panel(building, mouse_pos)
            elif building.type == "quarry":
                # Draw quarry info panel
                self.draw_quarry_info_panel(building, mouse_pos)
            elif building.type == "lumber":
                # Draw lumber camp info panel
                self.draw_lumber_info_panel(building, mouse_pos)

    def draw_refinery_info_panel(self, building, mouse_pos) -> None:
        """Draw a nice info panel for refinery buildings"""
        panel_width = 200
        panel_height = 120
        margin = 20
        
        # Position panel near mouse but keep it on screen
        x = min(mouse_pos[0] + 20, WINDOW_WIDTH - panel_width - margin)
        y = max(mouse_pos[1] - panel_height - 20, margin)
        
        # Panel background
        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (45, 45, 52), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 95), panel_rect, 2, border_radius=8)
        
        # Title
        title = self.font.render("REFINERY", True, (255, 255, 255))
        title_rect = title.get_rect(midtop=(panel_rect.centerx, panel_rect.y + 10))
        self.screen.blit(title, title_rect)
        
        # Resource info in a nice square
        info_x = panel_rect.x + 15
        info_y = panel_rect.y + 40
        
        # Stone input section
        stone_amt = int(building.storage.get("stone", 0))
        stone_text = self.font.render(f"Stone Input: {stone_amt}", True, (200, 200, 200))
        self.screen.blit(stone_text, (info_x, info_y))
        
        # BMAT output section
        bmat_amt = int(building.storage.get("bmats", 0))
        bmat_text = self.font.render(f"BMAT Output: {bmat_amt}", True, (255, 200, 80))
        self.screen.blit(bmat_text, (info_x, info_y + 25))
        
        # Production rate
        rate_text = self.font.render(f"Rate: {building.production_rate_per_sec:.1f}/s", True, (150, 200, 150))
        self.screen.blit(rate_text, (info_x, info_y + 50))
        
        # Status
        if stone_amt > 0:
            status_text = self.font.render("Status: Converting", True, (100, 200, 100))
        else:
            status_text = self.font.render("Status: Waiting for stone", True, (200, 100, 100))
        self.screen.blit(status_text, (info_x, info_y + 75))
        
        # Loading bar for bmat production
        if stone_amt > 0:
            bar_width = 150
            bar_height = 8
            bar_x = info_x
            bar_y = info_y + 95
            
            # Background bar
            pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            
            # Progress bar (5 seconds = 1 bmat)
            if "conversion_timer" in building.__dict__:
                progress = building.conversion_timer / 5.0
                progress_width = int(bar_width * progress)
                if progress_width > 0:
                    pygame.draw.rect(self.screen, (100, 200, 100), (bar_x, bar_y, progress_width, bar_height), border_radius=4)
            
            # Border
            pygame.draw.rect(self.screen, (120, 120, 120), (bar_x, bar_y, bar_width, bar_height), 1, border_radius=4)

    def draw_quarry_info_panel(self, building, mouse_pos) -> None:
        """Draw a nice info panel for quarry buildings"""
        panel_width = 200
        panel_height = 100
        margin = 20
        
        # Position panel near mouse but keep it on screen
        x = min(mouse_pos[0] + 20, WINDOW_WIDTH - panel_width - margin)
        y = max(mouse_pos[1] - panel_height - 20, margin)
        
        # Panel background
        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (45, 45, 52), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 95), panel_rect, 2, border_radius=8)
        
        # Title
        title = self.font.render("QUARRY", True, (255, 255, 255))
        title_rect = title.get_rect(midtop=(panel_rect.centerx, panel_rect.y + 10))
        self.screen.blit(title, title_rect)
        
        # Stone storage info
        info_x = panel_rect.x + 15
        info_y = panel_rect.y + 40
        
        stone_amt = int(building.storage.get("stone", 0))
        stone_text = self.font.render(f"Stone Stored: {stone_amt}", True, (200, 200, 200))
        self.screen.blit(stone_text, (info_x, info_y))
        
        # Production rate
        rate_text = self.font.render(f"Rate: {building.production_rate_per_sec:.1f}/s", True, (150, 200, 150))
        self.screen.blit(rate_text, (info_x, info_y + 25))

    def draw_lumber_info_panel(self, building, mouse_pos) -> None:
        """Draw a nice info panel for lumber camp buildings"""
        panel_width = 200
        panel_height = 100
        margin = 20
        
        # Position panel near mouse but keep it on screen
        x = min(mouse_pos[0] + 20, WINDOW_WIDTH - panel_width - margin)
        y = max(mouse_pos[1] - panel_height - 20, margin)
        
        # Panel background
        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (45, 45, 52), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 95), panel_rect, 2, border_radius=8)
        
        # Title
        title = self.font.render("LUMBER CAMP", True, (255, 255, 255))
        title_rect = title.get_rect(midtop=(panel_rect.centerx, panel_rect.y + 10))
        self.screen.blit(title, title_rect)
        
        # Wood storage info
        info_x = panel_rect.x + 15
        info_y = panel_rect.y + 40
        
        wood_amt = int(building.storage.get("wood", 0))
        wood_text = self.font.render(f"Wood Stored: {wood_amt}", True, (160, 120, 60))
        self.screen.blit(wood_text, (info_x, info_y))
        
        # Production rate
        rate_text = self.font.render(f"Rate: {building.production_rate_per_sec:.1f}/s", True, (150, 200, 150))
        self.screen.blit(rate_text, (info_x, info_y + 25))

    def draw_ui(self) -> None:
        mode_text = "BUILD MODE" if self.build_mode else "EXPLORE"
        hint = "[Drag] Pan" if not self.build_mode else "[LMB Drag] Build"
        # Resources row (top-left, left to right)
        res_text = (
            f"Oil: {self.resources['oil']}   "
            f"Steel: {self.resources['steel']}   "
            f"Wood: {self.resources['wood']}   "
            f"Stone: {self.resources['stone']}   "
            f"BMATS: {self.resources['bmats']}"
        )
        res_surf = self.font.render(res_text, True, UI_TEXT)
        # Background behind resources for visibility
        padding = 8
        res_pos = (12, 10)
        res_bg = pygame.Rect(res_pos[0] - 4, res_pos[1] - 4, res_surf.get_width() + padding, res_surf.get_height() + padding)
        pygame.draw.rect(self.screen, (55, 55, 60), res_bg, border_radius=6)
        self.screen.blit(res_surf, res_pos)

        # Controls row beneath
        controls_surf = self.font.render(
            f"[B] Toggle Build | {hint} | Mode: {mode_text}", True, UI_TEXT
        )
        self.screen.blit(controls_surf, (12, 34))

        # Build toolbar in build mode
        if self.build_mode:
            bar_rects = self.get_build_bar_rects()
            # Draw bar background spanning its bounds
            full_bar = self.get_full_build_bar_rect(bar_rects)
            pygame.draw.rect(self.screen, UI_BAR_BG, full_bar, border_radius=8)
            pygame.draw.rect(self.screen, UI_BAR_BORDER, full_bar, 2, border_radius=8)
            for tool, rect in bar_rects.items():
                selected = tool == self.current_tool
                if tool == "bulldoze":
                    bg_color = (140, 40, 40) if selected else (100, 35, 35)
                    brd = (200, 90, 90) if selected else (150, 70, 70)
                else:
                    bg_color = (75, 75, 88) if selected else (62, 62, 72)
                    brd = (130, 130, 150) if selected else (90, 90, 105)
                pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
                pygame.draw.rect(self.screen, brd, rect, 2, border_radius=6)
                label = (
                    "Road" if tool == "road" else
                    "Lumber Camp" if tool == "lumber" else
                    "Quarry" if tool == "quarry" else
                    "Refinery" if tool == "refinery" else
                    "Bulldoze"
                )
                tsurf = self.font.render(label, True, UI_TEXT)
                tx = rect.x + (rect.width - tsurf.get_width()) // 2
                ty = rect.y + (rect.height - tsurf.get_height()) // 2
                self.screen.blit(tsurf, (tx, ty))

        # Explore staged UI
        self.draw_top_banner()
        self.draw_explore_panel()

    def get_build_bar_rects(self) -> Dict[str, pygame.Rect]:
        # Horizontal bar at bottom
        margin = 12
        button_w = 150
        button_w_small = 120  # Smaller buttons to fit more tools
        button_h = 40
        spacing = 10
        start_x = margin
        y = WINDOW_HEIGHT - button_h - margin
        rects: Dict[str, pygame.Rect] = {}
        rects["road"] = pygame.Rect(start_x, y, button_w, button_h)
        rects["lumber"] = pygame.Rect(start_x + button_w + spacing, y, button_w_small, button_h)
        rects["quarry"] = pygame.Rect(start_x + button_w + button_w_small + spacing * 2, y, button_w_small, button_h)
        rects["refinery"] = pygame.Rect(start_x + button_w + button_w_small * 2 + spacing * 3, y, button_w_small, button_h)
        # Bulldoze on right side
        rects["bulldoze"] = pygame.Rect(WINDOW_WIDTH - margin - button_w, y, button_w, button_h)
        return rects

    def get_full_build_bar_rect(self, rects: Dict[str, pygame.Rect]) -> pygame.Rect:
        # Compute bounding rect around given button rects
        xs = [r.x for r in rects.values()]
        ys = [r.y for r in rects.values()]
        ws = [r.x + r.w for r in rects.values()]
        hs = [r.y + r.h for r in rects.values()]
        x = min(xs) - 8
        y = min(ys) - 8
        w = max(ws) - x + 8
        h = max(hs) - y + 8
        return pygame.Rect(x, y, w, h)

    # -------- Explore mode staged UI --------
    def draw_top_banner(self) -> None:
        if self.build_mode:
            return
        text: Optional[str] = None
        if self.assign_stage == "choose_truck":
            text = "Choose a truck at the base"
        elif self.assign_stage == "choose_source":
            text = "Fetching where? Click a source (e.g., Lumber Camp)"
        elif self.assign_stage == "choose_resource":
            text = "Choose resource to fetch"
        elif self.assign_stage == "confirm":
            text = "Confirm assignment and toggle repeat if desired"
        if text:
            surf = self.font.render(text, True, UI_TEXT)
            bg = pygame.Rect(8, 56, surf.get_width() + 16, surf.get_height() + 10)
            pygame.draw.rect(self.screen, (55, 55, 60), bg, border_radius=6)
            self.screen.blit(surf, (bg.x + 8, bg.y + 5))

    def get_truck_panel_rects(self) -> Dict[str, pygame.Rect]:
        margin = 12
        panel_h = 100
        panel_rect = pygame.Rect(8, WINDOW_HEIGHT - panel_h - margin, WINDOW_WIDTH - 16, panel_h)
        rects: Dict[str, pygame.Rect] = {"panel": panel_rect}
        x = panel_rect.x + 12
        y = panel_rect.y + 12
        btn_w = 140
        btn_h = 36
        spacing = 10
        
        # Add truck buttons
        for t in self.trucks:
            rects[f"truck_{t.truck_id}"] = pygame.Rect(x, y, btn_w, btn_h)
            x += btn_w + spacing
        
        # Add + truck button
        rects["add_truck"] = pygame.Rect(x, y, btn_w, btn_h)
        x += btn_w + spacing
        
        # Cancel button on the right
        rects["cancel"] = pygame.Rect(panel_rect.right - btn_w - 12, y, btn_w, btn_h)
        return rects

    def get_resource_panel_rects(self) -> Dict[str, pygame.Rect]:
        margin = 12
        panel_h = 100
        panel_rect = pygame.Rect(8, WINDOW_HEIGHT - panel_h - margin, WINDOW_WIDTH - 16, panel_h)
        rects: Dict[str, pygame.Rect] = {"panel": panel_rect}
        x = panel_rect.x + 12
        y = panel_rect.y + 12
        btn_w = 140
        btn_h = 36
        # Determine options from source building type and destination
        options: List[str] = []
        if self.pending_source is not None:
            # Check if this is a base → refinery route
            if self.pending_source == self.base_cell and self.pending_destination is not None:
                dest_building = self.get_building_at_cell(self.pending_destination)
                if dest_building and dest_building.type == "refinery":
                    # Base → Refinery route: truck picks up stone from base
                    options = ["stone"]
                else:
                    # Base → Other: show available resources at base
                    if self.resources.get("wood", 0) > 0:
                        options.append("wood")
                    if self.resources.get("stone", 0) > 0:
                        options.append("stone")
                    if self.resources.get("bmats", 0) > 0:
                        options.append("bmats")
            else:
                # Regular source building route
                b = self.get_building_at_cell(self.pending_source)
                if b is not None:
                    if b.type == "lumber":
                        options = ["wood"]
                    elif b.type == "quarry":
                        options = ["stone"]
                    elif b.type == "refinery":
                        options = ["bmats"]
        
        if not options:
            options = ["wood"]
        for opt in options:
            key = f"res_{opt}"
            rects[key] = pygame.Rect(x, y, btn_w, btn_h)
            x += btn_w + 10
        rects["cancel"] = pygame.Rect(panel_rect.right - btn_w - 12, y, btn_w, btn_h)
        return rects

    def get_confirm_panel_rects(self) -> Dict[str, pygame.Rect]:
        margin = 12
        panel_h = 100
        panel_rect = pygame.Rect(8, WINDOW_HEIGHT - panel_h - margin, WINDOW_WIDTH - 16, panel_h)
        rects: Dict[str, pygame.Rect] = {"panel": panel_rect}
        x = panel_rect.x + 12
        y = panel_rect.y + 12
        btn_w = 140
        btn_h = 36
        rects["confirm"] = pygame.Rect(x, y, btn_w, btn_h)
        rects["repeat"] = pygame.Rect(x + btn_w + 10, y, btn_w, btn_h)
        rects["cancel"] = pygame.Rect(panel_rect.right - btn_w - 12, y, btn_w, btn_h)
        return rects

    def draw_explore_panel(self) -> None:
        if self.build_mode:
            return
        if self.assign_stage == "idle":
            return
        # Choose Truck panel
        if self.assign_stage == "choose_truck":
            rects = self.get_truck_panel_rects()
            panel = rects["panel"]
            pygame.draw.rect(self.screen, UI_BAR_BG, panel, border_radius=8)
            pygame.draw.rect(self.screen, UI_BAR_BORDER, panel, 2, border_radius=8)
            
            # Draw truck buttons
            for t in self.trucks:
                r = rects[f"truck_{t.truck_id}"]
                pygame.draw.rect(self.screen, (62, 62, 72), r, border_radius=6)
                pygame.draw.rect(self.screen, (90, 90, 105), r, 2, border_radius=6)
                label = f"Truck {t.truck_id} ({t.state})"
                ts = self.font.render(label, True, UI_TEXT)
                self.blit_text_clipped(ts, r)
            
            # Draw + truck button
            add_btn = rects["add_truck"]
            can_afford = self.resources.get("bmats", 0) >= self.truck_factory.get_truck_cost()
            bg_color = (60, 120, 60) if can_afford else (80, 80, 80)
            border_color = (80, 160, 80) if can_afford else (100, 100, 100)
            pygame.draw.rect(self.screen, bg_color, add_btn, border_radius=6)
            pygame.draw.rect(self.screen, border_color, add_btn, 2, border_radius=6)
            
            # Show cost and + symbol
            cost = self.truck_factory.get_truck_cost()
            label_text = f"+ Truck ({cost})"
            label_surf = self.font.render(label_text, True, (255, 255, 255) if can_afford else (150, 150, 150))
            self.blit_text_clipped(label_surf, add_btn)
            
            # Cancel button
            rcancel = rects["cancel"]
            pygame.draw.rect(self.screen, (120, 70, 70), rcancel, border_radius=6)
            pygame.draw.rect(self.screen, (90, 90, 105), rcancel, 2, border_radius=6)
            tsca = self.font.render("Cancel", True, UI_TEXT)
            self.blit_text_clipped(tsca, rcancel)
            return
        # Choose Resource panel
        if self.assign_stage == "choose_resource":
            rects = self.get_resource_panel_rects()
            panel = rects["panel"]
            pygame.draw.rect(self.screen, UI_BAR_BG, panel, border_radius=8)
            pygame.draw.rect(self.screen, UI_BAR_BORDER, panel, 2, border_radius=8)
            for key, r in rects.items():
                if key == "panel" or key == "cancel":
                    continue
                pygame.draw.rect(self.screen, (62, 62, 72), r, border_radius=6)
                pygame.draw.rect(self.screen, (90, 90, 105), r, 2, border_radius=6)
                label = "Wood" if key.endswith("wood") else "Stone" if key.endswith("stone") else "BMATS"
                ts2 = self.font.render(label, True, UI_TEXT)
                self.blit_text_clipped(ts2, r)
            rcancel = rects["cancel"]
            pygame.draw.rect(self.screen, (120, 70, 70), rcancel, border_radius=6)
            pygame.draw.rect(self.screen, (90, 90, 105), rcancel, 2, border_radius=6)
            tsca = self.font.render("Cancel", True, UI_TEXT)
            self.blit_text_clipped(tsca, rcancel)
            return
        # Confirm panel
        if self.assign_stage == "confirm":
            rects = self.get_confirm_panel_rects()
            panel = rects["panel"]
            pygame.draw.rect(self.screen, UI_BAR_BG, panel, border_radius=8)
            pygame.draw.rect(self.screen, UI_BAR_BORDER, panel, 2, border_radius=8)
            rconf = rects["confirm"]
            rrepeat = rects["repeat"]
            rcancel = rects["cancel"]
            ready = self.pending_source is not None and self.pending_destination is not None and self.pending_truck_id is not None and self.pending_resource is not None
            pygame.draw.rect(self.screen, (70, 120, 70) if ready else (60, 70, 60), rconf, border_radius=6)
            pygame.draw.rect(self.screen, (90, 90, 105), rconf, 2, border_radius=6)
            tsc = self.font.render("Confirm", True, UI_TEXT)
            self.blit_text_clipped(tsc, rconf)
            # Repeat toggle
            repeat_on = False
            if self.pending_truck_id is not None:
                tsel = self.get_truck_by_id(self.pending_truck_id)
                repeat_on = bool(tsel and tsel.repeat_enabled)
            pygame.draw.rect(self.screen, (90, 120, 160) if repeat_on else (62, 62, 72), rrepeat, border_radius=6)
            pygame.draw.rect(self.screen, (130, 160, 190) if repeat_on else (90, 90, 105), rrepeat, 2, border_radius=6)
            tsr = self.font.render("Repeat", True, UI_TEXT)
            self.blit_text_clipped(tsr, rrepeat)
            # Cancel
            pygame.draw.rect(self.screen, (120, 70, 70), rcancel, border_radius=6)
            pygame.draw.rect(self.screen, (90, 90, 105), rcancel, 2, border_radius=6)
            tsca = self.font.render("Cancel", True, UI_TEXT)
            self.blit_text_clipped(tsca, rcancel)
            return

    def handle_explore_ui_click(self, pos: Tuple[int, int]) -> bool:
        if self.build_mode:
            return False
        if self.assign_stage == "choose_truck":
            rects = self.get_truck_panel_rects()
            if not rects["panel"].collidepoint(pos):
                return False
            
            # Check if + truck button was clicked
            if rects["add_truck"].collidepoint(pos):
                self.build_new_truck()
                return True
            
            # Check if any truck button was clicked
            for t in self.trucks:
                r = rects[f"truck_{t.truck_id}"]
                if r.collidepoint(pos):
                    self.pending_truck_id = t.truck_id
                    # After choosing truck, move to choose_source and hide panel
                    self.assign_stage = "choose_source"
                    return True
            
            # Check if cancel was clicked
            if rects["cancel"].collidepoint(pos):
                self.clear_pending_selection()
                return True
            return True
        if self.assign_stage == "choose_resource":
            rects = self.get_resource_panel_rects()
            if not rects["panel"].collidepoint(pos):
                return False
            # Check all possible resource buttons
            for key, r in rects.items():
                if key.startswith("res_") and r.collidepoint(pos):
                    self.pending_resource = key.split("_", 1)[1]
                    self.assign_stage = "confirm"
                    return True
            if rects["cancel"].collidepoint(pos):
                self.clear_pending_selection()
                return True
            return True
        if self.assign_stage == "confirm":
            rects = self.get_confirm_panel_rects()
            if not rects["panel"].collidepoint(pos):
                return False
            if rects["repeat"].collidepoint(pos):
                if self.pending_truck_id is not None:
                    t = self.get_truck_by_id(self.pending_truck_id)
                    if t:
                        t.repeat_enabled = not t.repeat_enabled
                return True
            if rects["confirm"].collidepoint(pos):
                if self.pending_source and self.pending_truck_id and self.pending_resource and self.pending_destination:
                    self.start_assignment(
                        truck_id=self.pending_truck_id,
                        source=self.pending_source,
                        dest=self.pending_destination,
                        resource=self.pending_resource,
                    )
                    self.clear_pending_selection()
                return True
            if rects["cancel"].collidepoint(pos):
                self.clear_pending_selection()
                return True
            return True
        return False

    def blit_text_clipped(self, text_surface: pygame.Surface, rect: pygame.Rect, padding: int = 6) -> None:
        # Centers and clips text within the given rect
        prev_clip = self.screen.get_clip()
        clip = rect.inflate(-padding, -padding)
        self.screen.set_clip(clip)
        x = rect.x + (rect.w - text_surface.get_width()) // 2
        y = rect.y + (rect.h - text_surface.get_height()) // 2
        self.screen.blit(text_surface, (x, y))
        self.screen.set_clip(prev_clip)

    def clear_pending_selection(self) -> None:
        self.pending_source = None
        self.pending_truck_id = None
        self.pending_resource = None
        self.pending_destination = None
        self.assign_stage = "idle"

    def start_assignment(self, truck_id: int, source: Coord, dest: Coord, resource: str) -> None:
        truck = self.get_truck_by_id(truck_id)
        if truck is None:
            return
        
        # determine road endpoints near truck, source, dest
        start_cell = self.find_nearest_road_to_cell(self.world_pos_to_cell(truck.position_px))
        source_road = self.find_nearest_road_to_cell(source)
        dest_road = self.find_nearest_road_to_cell(dest)
        
        if start_cell is None or source_road is None or dest_road is None:
            print(f"No path found: start_road={start_cell}, source_road={source_road}, dest_road={dest_road}")
            return
        
        print(f"Pathfinding: truck at {self.world_pos_to_cell(truck.position_px)} -> start_road={start_cell}, source_road={source_road}, dest_road={dest_road}")
        
        # Special handling for base → refinery assignments
        if source == self.base_cell and resource == "stone":
            # For base → refinery, truck needs to go to base first to load stone
            if not self.is_cell_in_base_area(truck.current_cell):
                print(f"Truck {truck.truck_id} not at base, routing to base first to load stone")
                # Route truck to base first
                base_road = self.find_nearest_road_to_cell(self.base_cell)
                if base_road:
                    path_to_base = self.find_path_on_roads(start_cell, base_road)
                    if path_to_base:
                        # Add the base cell so truck can enter it
                        path_to_base.append(self.base_cell)
                        truck.path_cells = path_to_base
                        truck.state = "to_source"
                        truck.cargo_type = resource
                        truck.current_cell = start_cell
                        truck._dest_cell = dest
                        truck.saved_source = source
                        truck.saved_dest = dest
                        truck.saved_resource = resource
                        truck.refinery_loop = True
                        print(f"Truck {truck.truck_id} routing to base first to load stone for refinery")
                        return
                    else:
                        print(f"No path to base found for truck {truck.truck_id}")
                        return
                else:
                    print(f"No road to base found")
                    return
            else:
                # Truck is already at base, go directly to refinery
                print(f"Truck {truck.truck_id} already at base, going directly to refinery")
                refinery_road = self.find_nearest_road_to_cell(dest)
                if refinery_road:
                    path_to_refinery = self.find_path_on_roads(start_cell, refinery_road)
                    if path_to_refinery:
                        # Add the refinery cell so truck can enter it
                        path_to_refinery.append(dest)
                        truck.path_cells = path_to_refinery
                        truck.state = "to_dest"  # Going directly to destination
                        truck.cargo_type = resource
                        truck.current_cell = start_cell
                        truck._dest_cell = dest
                        truck.saved_source = source
                        truck.saved_dest = dest
                        truck.saved_resource = resource
                        truck.refinery_loop = True
                        print(f"Truck {truck.truck_id} going directly to refinery from base")
                        return
                    else:
                        print(f"No path to refinery found for truck {truck.truck_id}")
                        return
                else:
                    print(f"No road to refinery found")
                    return
        
        # Special handling for buildings very close to base
        # If source and dest are close, we need to ensure proper pathfinding
        source_to_base_distance = abs(source[0] - self.base_cell[0]) + abs(source[1] - self.base_cell[1])
        
        if source_to_base_distance <= 3:  # Very close to base
            print(f"Building close to base detected, using special pathfinding")
            # For close buildings, ensure we have a proper road path
            if source_road == dest_road:
                # Same road, need to find a different path
                print(f"Source and destination share same road, finding alternative path")
                # Try to find a path through the base area
                base_road = self.find_nearest_road_to_cell(self.base_cell)
                if base_road and base_road != source_road:
                    # Route through base: truck -> base -> source -> base
                    path1 = self.find_path_on_roads(start_cell, base_road)
                    if path1:
                        # Add the source building to the path so truck can enter it
                        path1.append(source)
                        truck.path_cells = path1
                        truck.state = "to_source"
                        truck.cargo_type = resource
                        truck.current_cell = start_cell
                        truck._dest_cell = dest
                        truck.saved_source = source
                        truck.saved_dest = dest
                        truck.saved_resource = resource
                        return
                else:
                    print(f"Cannot find alternative path for close building")
                    return
        
        # Normal pathfinding for buildings further from base
        # Find path from truck to source building (via roads only)
        path1 = self.find_path_on_roads(start_cell, source_road)
        if not path1:
            print(f"No road path found from truck to source building")
            return
        
        # The path should only contain road cells - trucks can't move to non-road cells
        # The source building will be handled when the truck reaches the last road cell
        truck.path_cells = path1
        truck.state = "to_source"
        truck.cargo_type = resource
        truck.current_cell = start_cell
        truck._dest_cell = dest
        truck.saved_source = source
        truck.saved_dest = dest
        truck.saved_resource = resource
        
        # Special handling for base → refinery assignments
        if source == self.base_cell and resource == "stone":
            # This is a stone delivery from base to refinery - set up the loop
            dest_building = self.get_building_at_cell(dest)
            if dest_building and dest_building.type == "refinery":
                truck.refinery_loop = True
                print(f"Truck {truck.truck_id} set up for refinery stone delivery loop from base")
        
        # Special handling for refinery assignments
        if resource == "stone" and dest != self.base_cell:
            # This is a stone delivery to refinery - set up the loop
            dest_building = self.get_building_at_cell(dest)
            if dest_building and dest_building.type == "refinery":
                truck.refinery_loop = True
                print(f"Truck {truck.truck_id} set up for refinery stone delivery loop")

    def get_truck_by_id(self, truck_id: int) -> Optional[Truck]:
        for t in self.trucks:
            if t.truck_id == truck_id:
                return t
        return None

    def get_building_at_cell(self, cell: Coord) -> Optional[Building]:
        for b in self.buildings:
            if b.cell == cell:
                return b
        return None

    # -------- Roads and pathfinding --------
    def world_pos_to_cell(self, pos_px: Tuple[float, float]) -> Coord:
        return (int(pos_px[0]) // GRID_SIZE, int(pos_px[1]) // GRID_SIZE)

    def is_road(self, cell: Coord) -> bool:
        return cell in self.roads

    def is_driveable(self, cell: Coord) -> bool:
        """Check if a tile is driveable (has road value 1)"""
        return self.road_grid.get(cell, 0) == 1

    def neighbors4(self, cell: Coord) -> List[Coord]:
        x, y = cell
        return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    def find_nearest_road_to_cell(self, cell: Coord, max_dist: int = 12) -> Optional[Coord]:
        if self.is_driveable(cell):
            return cell
        # expand rings
        cx, cy = cell
        for d in range(1, max_dist + 1):
            for dx in range(-d, d + 1):
                dy = d - abs(dx)
                for sy in (-1, 1):
                    ny = cy + sy * dy
                    nx = cx + dx
                    cand = (nx, ny)
                    if self.is_driveable(cand):
                        return cand
        return None

    def find_path_on_roads(self, start: Coord, goal: Coord) -> List[Coord]:
        if start == goal:
            return [start]
        from collections import deque
        queue = deque([start])
        came: Dict[Coord, Optional[Coord]] = {start: None}
        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            for nb in self.neighbors4(cur):
                # Only move to driveable road cells
                if self.is_driveable(nb) and nb not in came:
                    came[nb] = cur
                    queue.append(nb)
        if goal not in came:
            return []
        # reconstruct
        path: List[Coord] = []
        cur: Optional[Coord] = goal
        while cur is not None:
            path.append(cur)
            cur = came[cur]
        path.reverse()
        return path



    def is_cell_connected_to_base_by_roads(self, cell: Coord) -> bool:
        # Check path between nearest driveable road to cell and nearest driveable road to base
        start = self.find_nearest_road_to_cell(cell)
        goal = self.find_nearest_road_to_cell(self.base_cell)
        if start is None or goal is None:
            return False
        return len(self.find_path_on_roads(start, goal)) > 0

    def is_cell_in_base_area(self, cell: Coord) -> bool:
        """Check if a cell is within the 2x2 base area"""
        bx, by = self.base_cell
        return bx <= cell[0] <= bx + 1 and by <= cell[1] <= by + 1

    def is_cell_adjacent_to_base(self, cell: Coord) -> bool:
        """Check if a cell is directly adjacent to the base area (including diagonals)"""
        bx, by = self.base_cell
        # Check if cell is in the 4x4 area around the 2x2 base
        return (bx - 1 <= cell[0] <= bx + 2) and (by - 1 <= cell[1] <= by + 2)

    def center_camera_on_cell(self, cell: Coord) -> None:
        cx, cy = cell
        base_center_px_x = cx * GRID_SIZE + GRID_SIZE // 2
        base_center_px_y = cy * GRID_SIZE + GRID_SIZE // 2
        self.camera_x = int(base_center_px_x - WINDOW_WIDTH // 2)
        self.camera_y = int(base_center_px_y - WINDOW_HEIGHT // 2)

    def center_camera_on_base(self) -> None:
        """Center camera on the middle of the 2x2 base"""
        bx, by = self.base_cell
        # Center on the middle of the 2x2 base
        center_x = (bx + 0.5) * GRID_SIZE
        center_y = (by + 0.5) * GRID_SIZE
        self.camera_x = int(center_x - WINDOW_WIDTH // 2)
        self.camera_y = int(center_y - WINDOW_HEIGHT // 2)

    # -------- Update & Main loop --------
    def update(self, dt: float) -> None:
        # Production from buildings (only if connected to base by roads)
        for b in self.buildings:
            if b.production_rate_per_sec <= 0:
                continue
            if not self.is_cell_connected_to_base_by_roads(b.cell):
                continue
            if b.type == "lumber":
                b.storage["wood"] = b.storage.get("wood", 0.0) + b.production_rate_per_sec * dt
            elif b.type == "quarry":
                b.storage["stone"] = b.storage.get("stone", 0.0) + b.production_rate_per_sec * dt
            elif b.type == "refinery":
                # Refineries convert stone to bmats: 1 stone = 1 bmat every 5 seconds
                stone_available = b.storage.get("stone", 0.0)
                if stone_available > 0:
                    # Add to conversion timer
                    if "conversion_timer" not in b.__dict__:
                        b.conversion_timer = 0.0
                    b.conversion_timer += dt
                    
                    # Every 5 seconds, convert 1 stone to 1 bmat
                    if b.conversion_timer >= 5.0:
                        b.storage["stone"] = stone_available - 1.0
                        b.storage["bmats"] = b.storage.get("bmats", 0.0) + 1.0
                        b.conversion_timer = 0.0  # Reset timer

        # Truck movement and logistics
        for t in self.trucks:
            self.update_truck(t, dt)

    def update_truck(self, t: Truck, dt: float) -> None:
        # Move along path if any
        if t.path_cells:
            # Move towards next cell center
            next_cell = t.path_cells[0]
            target_px = (
                next_cell[0] * GRID_SIZE + GRID_SIZE // 2,
                next_cell[1] * GRID_SIZE + GRID_SIZE // 2,
            )
            vx = target_px[0] - t.position_px[0]
            vy = target_px[1] - t.position_px[1]
            dist = (vx * vx + vy * vy) ** 0.5
            if dist < 1e-3:
                # Reached this cell
                t.position_px = (float(target_px[0]), float(target_px[1]))
                t.current_cell = next_cell
                t.path_cells.pop(0)
                # If reached end of path, handle arrival state
                if not t.path_cells:
                    self.on_truck_arrival(t)
            else:
                ux = vx / dist
                uy = vy / dist
                step = t.speed_px_per_sec * dt
                if step >= dist:
                    t.position_px = (float(target_px[0]), float(target_px[1]))
                else:
                    t.position_px = (t.position_px[0] + ux * step, t.position_px[1] + uy * step)

    def on_truck_arrival(self, t: Truck) -> None:
        # Arrived to source or destination depending on state
        if t.state == "to_source":
            # Check if we're at the source building (not just close to it)
            src_cell = getattr(t, "saved_source", None)
            if src_cell is None:
                t.state = "idle"
                return
                
            # Check if we're actually at the source building cell
            if t.current_cell == src_cell:
                # We're at the building, load cargo
                src_building = self.get_building_at_cell(src_cell)
                if src_building is None:
                    t.state = "idle"
                    return
                
                # Load from source building storage
                if t.cargo_type == "wood":
                    if src_cell == self.base_cell:
                        # Loading wood from base
                        amount_available = self.resources.get("wood", 0)
                        load_amount = min(5.0, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            self.resources["wood"] = max(0, amount_available - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} wood from base")
                    else:
                        # Loading from lumber camp
                        b = src_building
                        amount_available = 0.0
                        if b and b.type == "lumber":
                            amount_available = b.storage.get("wood", 0.0)
                        load_amount = min(5.0, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            if b and b.type == "lumber":
                                b.storage["wood"] = max(0.0, b.storage.get("wood", 0.0) - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} wood from lumber camp")
                elif t.cargo_type == "stone":
                    if src_cell == self.base_cell:
                        # Loading stone from base - always try to get 5 stone for refinery delivery
                        amount_available = self.resources.get("stone", 0)
                        # For refinery delivery, always try to get 5 stone
                        target_load = 5.0
                        load_amount = min(target_load, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            self.resources["stone"] = max(0, amount_available - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} stone from base")
                            
                            # If destination is refinery, set up refinery loop
                            dest = getattr(t, "_dest_cell", None)
                            if dest is not None:
                                dest_building = self.get_building_at_cell(dest)
                                if dest_building and dest_building.type == "refinery":
                                    t.refinery_loop = True
                                    t.stone_delivered = load_amount  # Track how much stone was delivered
                                    print(f"Truck {t.truck_id} set up for refinery stone delivery loop")
                    else:
                        # Loading from quarry
                        b = src_building
                        amount_available = 0.0
                        if b and b.type == "quarry":
                            amount_available = b.storage.get("stone", 0.0)
                        load_amount = min(5.0, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            if b and b.type == "quarry":
                                b.storage["stone"] = max(0.0, b.storage.get("stone", 0.0) - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} stone from quarry")
                            
                            # If this is a refinery loop, go directly to refinery
                            if hasattr(t, "refinery_loop") and t.refinery_loop:
                                dest = getattr(t, "_dest_cell", None)
                                if dest is not None:
                                    # Go directly to refinery with stone
                                    cur_road = self.find_nearest_road_to_cell(t.current_cell) or t.current_cell
                                    dest_road = self.find_nearest_road_to_cell(dest)
                                    if dest_road:
                                        path2 = self.find_path_on_roads(cur_road, dest_road)
                                        if path2:
                                            path2.append(dest)
                                            t.path_cells = path2
                                            t.state = "to_dest"
                                            print(f"Truck {t.truck_id} heading to refinery with {load_amount} stone")
                                            return
                elif t.cargo_type == "bmats":
                    if src_cell == self.base_cell:
                        # Loading bmats from base
                        amount_available = self.resources.get("bmats", 0)
                        load_amount = min(5.0, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            self.resources["bmats"] = max(0, amount_available - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} bmats from base")
                    else:
                        # Loading from refinery
                        b = src_building
                        amount_available = 0.0
                        if b and b.type == "refinery":
                            amount_available = b.storage.get("bmats", 0.0)
                        load_amount = min(5.0, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            if b and b.type == "refinery":
                                b.storage["bmats"] = max(0.0, b.storage.get("bmats", 0.0) - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} bmats from refinery")
                else:
                    # If cargo type unknown yet, infer from source building
                    if src_building:
                        if src_building.type == "lumber":
                            t.cargo_type = "wood"
                        elif src_building.type == "quarry":
                            t.cargo_type = "stone"
                        elif src_building.type == "refinery":
                            t.cargo_type = "bmats"
                
                # Now go to destination
                dest = getattr(t, "_dest_cell", None)
                if dest is not None:
                    # For close buildings, route through base if needed
                    if dest == self.base_cell:
                        # Going to base, find path from current position
                        cur_road = self.find_nearest_road_to_cell(t.current_cell) or t.current_cell
                        base_road = self.find_nearest_road_to_cell(dest)
                        if base_road:
                            path2 = self.find_path_on_roads(cur_road, base_road)
                            if path2:
                                # Add the base cell so truck can enter it
                                path2.append(dest)
                                t.path_cells = path2
                                t.state = "to_dest"
                                return
                    else:
                        # Going to another building
                        cur_road = self.find_nearest_road_to_cell(t.current_cell) or t.current_cell
                        dest_road = self.find_nearest_road_to_cell(dest)
                        if dest_road:
                            path2 = self.find_path_on_roads(cur_road, dest_road)
                            if path2:
                                # Add the destination building so truck can enter it
                                path2.append(dest)
                                t.path_cells = path2
                                t.state = "to_dest"
                                return
            else:
                # Not at building yet, continue moving
                return
                
        elif t.state == "waiting_for_bmats":
            # Truck is waiting at refinery for bmats to be produced
            if not hasattr(t, "waiting_timer"):
                t.waiting_timer = 0.0
            t.waiting_timer += dt
            
            # Check if we have enough bmats to collect
            dest_cell = getattr(t, "_dest_cell", None)
            if dest_cell is not None:
                dest_building = self.get_building_at_cell(dest_cell)
                if dest_building and dest_building.type == "refinery":
                    bmat_available = dest_building.storage.get("bmats", 0.0)
                    waiting_target = getattr(t, "waiting_target", 5.0)  # Default to 5 if not set
                    if bmat_available >= waiting_target:
                        # Collect the target amount of bmats and return to base
                        t.cargo_type = "bmats"
                        t.cargo_amount = waiting_target
                        dest_building.storage["bmats"] = bmat_available - waiting_target
                        print(f"Truck {t.truck_id} collected {waiting_target} bmats from refinery")
                        
                        # Return to base
                        cur_road = self.find_nearest_road_to_cell(t.current_cell) or t.current_cell
                        base_road = self.find_nearest_road_to_cell(self.base_cell)
                        if base_road:
                            path_to_base = self.find_path_on_roads(cur_road, base_road)
                            if path_to_base:
                                path_to_base.append(self.base_cell)
                                t.path_cells = path_to_base
                                t.state = "to_dest"
                                t._dest_cell = self.base_cell
                                return
                        # If no path to base, go idle
                        t.state = "idle"
                        return
                        
        elif t.state == "to_dest":
            # Check if we're at the destination (not just close to it)
            dest_cell = getattr(t, "_dest_cell", None)
            if dest_cell is None:
                t.state = "idle"
                return
                
            # Check if we're actually at the destination cell
            if t.current_cell == dest_cell:
                # We're at the destination, unload
                if dest_cell == self.base_cell:
                    # At base, unload cargo
                    if t.cargo_type in ("wood", "stone", "bmats") and t.cargo_amount > 0:
                        delivered = int(t.cargo_amount)  # Deliver all cargo
                        self.resources[t.cargo_type] += delivered
                        t.cargo_amount = 0.0  # Clear cargo completely
                        print(f"Truck {t.truck_id} delivered {delivered} {t.cargo_type} to base")
                else:
                    # At another building, unload cargo
                    dest_building = self.get_building_at_cell(dest_cell)
                    if dest_building:
                        if t.cargo_type == "stone" and dest_building.type == "refinery" and t.cargo_amount > 0:
                            # Deliver all stone to refinery
                            delivered = int(t.cargo_amount)
                            dest_building.storage["stone"] = dest_building.storage.get("stone", 0.0) + delivered
                            t.cargo_amount = 0.0  # Clear cargo completely
                            print(f"Truck {t.truck_id} delivered {delivered} stone to refinery")
                            
                            # Now wait for bmats to be produced (wait for the amount of stone delivered)
                            if delivered > 0:
                                t.state = "waiting_for_bmats"
                                t.waiting_timer = 0.0
                                t.waiting_target = delivered  # Wait for the amount of stone delivered
                                print(f"Truck {t.truck_id} now waiting for {delivered} bmats at refinery")
                                return
                        elif t.cargo_type in ("wood", "bmats") and t.cargo_amount > 0:
                            delivered = int(t.cargo_amount)  # Deliver all cargo
                            # For now, just deliver to base instead of storage buildings
                            self.resources[t.cargo_type] += delivered
                            t.cargo_amount = 0.0  # Clear cargo completely
                            print(f"Truck {t.truck_id} delivered {delivered} {t.cargo_type} to base")
            else:
                # Not at destination yet, but check if we need to load stone for refinery delivery
                if hasattr(t, "refinery_loop") and t.refinery_loop and t.cargo_type == "stone" and t.cargo_amount == 0:
                    # Truck is going to refinery but has no stone - needs to load from base first
                    if self.is_cell_in_base_area(t.current_cell):
                        # We're at base, load stone
                        amount_available = self.resources.get("stone", 0)
                        target_load = 5.0  # Always try to get 5 stone for refinery
                        load_amount = min(target_load, amount_available, t.cargo_capacity - t.cargo_amount)
                        if load_amount > 0:
                            t.cargo_amount += load_amount
                            self.resources["stone"] = max(0, amount_available - load_amount)
                            print(f"Truck {t.truck_id} loaded {load_amount} stone from base for refinery delivery")
                        else:
                            print(f"Truck {t.truck_id} cannot load stone from base (available: {amount_available})")
                            t.state = "idle"
                            return
            
            # Repeat or return to idle
            saved_src = getattr(t, "saved_source", None)
            saved_dst = getattr(t, "saved_dest", None)
            saved_res = getattr(t, "saved_resource", None)
            if t.repeat_enabled and saved_src and saved_dst and saved_res:
                # Queue next trip back to source
                cur_road = self.find_nearest_road_to_cell(t.current_cell) or t.current_cell
                src_road = self.find_nearest_road_to_cell(saved_src)
                if src_road:
                    path_back = self.find_path_on_roads(cur_road, src_road)
                    if path_back:
                        # Add the source building so truck can enter it
                        path_back.append(saved_src)
                        t.path_cells = path_back
                        t.state = "to_source"
                        t.cargo_type = saved_res
                        t._dest_cell = saved_dst
                        return
            # Otherwise stop
            t.state = "idle"
            t.cargo_type = None
            if hasattr(t, "_dest_cell"):
                delattr(t, "_dest_cell")

    def is_truck_at_base(self, t: Truck) -> bool:
        # Check by cell to make it robust
        return self.is_cell_in_base_area(t.current_cell) or (
            abs((t.position_px[0]) - (self.base_cell[0] * GRID_SIZE + GRID_SIZE // 2)) <= GRID_SIZE and
            abs((t.position_px[1]) - (self.base_cell[1] * GRID_SIZE + GRID_SIZE // 2)) <= GRID_SIZE
        )

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)

            self.screen.fill(BG_COLOR)
            self.draw_grid()
            self.draw_roads()
                        # Draw trucks first (below buildings)
            self.draw_trucks()
            self.draw_truck_paths()
            self.draw_truck_markers()
            
            # Draw truck numbers and selection indicators
            self.truck_selector.draw_truck_numbers(self.screen, self.font, self.trucks, self.camera_x, self.camera_y)
            
            # Draw world elements
            self.draw_trees()
            self.draw_stones()
            self.draw_buildings()
            
            # Tool preview overlays
            self.draw_lumber_preview()
            self.draw_quarry_preview()
            self.draw_refinery_preview()
            
            # Bulldoze highlighting
            self.bulldoze_manager.draw_highlight(self.screen, self.camera_x, self.camera_y, GRID_SIZE)
            self.draw_base()
            self.draw_ui()
            # Bulldoze confirm button (drawn on top of everything) - initialize rect first
            self.bulldoze_manager.get_confirm_button_rect(WINDOW_WIDTH, WINDOW_HEIGHT)
            self.bulldoze_manager.draw_confirm_button(self.screen, self.font)
            
            # Building info panels (drawn on top)
            self.draw_building_info_panels()
            
            # Truck info panel (drawn on top)
            if self.truck_selector.selected_truck_id:
                selected_truck = self.get_truck_by_id(self.truck_selector.selected_truck_id)
                if selected_truck:
                    self.truck_selector.draw_truck_info_panel(self.screen, self.font, selected_truck, self.trucks)
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()


