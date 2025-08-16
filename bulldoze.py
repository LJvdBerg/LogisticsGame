"""
Bulldoze functionality for the logistics game.
Handles drag bulldozing with red grid highlighting and confirm button.
"""

import pygame
from typing import Set, Tuple, Optional

# Colors for bulldoze mode
BULLDOZE_HIGHLIGHT = (200, 50, 50, 100)  # Semi-transparent red
BULLDOZE_CONFIRM_BG = (180, 40, 40)
BULLDOZE_CONFIRM_BORDER = (220, 80, 80)

class BulldozeManager:
    def __init__(self):
        self.is_dragging = False
        self.drag_start_cell: Optional[Tuple[int, int]] = None
        self.drag_end_cell: Optional[Tuple[int, int]] = None
        self.highlighted_cells: Set[Tuple[int, int]] = set()
        self.confirm_rect: Optional[pygame.Rect] = None
        
    def start_drag(self, cell: Tuple[int, int]) -> None:
        """Start bulldoze drag operation"""
        self.is_dragging = True
        self.drag_start_cell = cell
        self.drag_end_cell = cell
        self.highlighted_cells = {cell}
        
    def update_drag(self, cell: Tuple[int, int]) -> None:
        """Update drag operation with new end cell"""
        if not self.is_dragging or self.drag_start_cell is None:
            return
            
        self.drag_end_cell = cell
        # Add this cell to highlighted cells (follow exact mouse path)
        self.highlighted_cells.add(cell)
        
    def end_drag(self) -> None:
        """End drag operation"""
        self.is_dragging = False
        
    def clear_highlight(self) -> None:
        """Clear all highlighted cells"""
        self.highlighted_cells.clear()
        self.drag_start_cell = None
        self.drag_end_cell = None
        
    def _get_cells_between(self, start: Tuple[int, int], end: Tuple[int, int]) -> Set[Tuple[int, int]]:
        """Get all cells between start and end points using Bresenham's line algorithm"""
        cells = set()
        x0, y0 = start
        x1, y1 = end
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        
        dx *= 2
        dy *= 2
        
        for _ in range(n):
            cells.add((x, y))
            if x == x1 and y == y1:
                break
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
                
        return cells
        
    def get_confirm_button_rect(self, screen_width: int, screen_height: int) -> pygame.Rect:
        """Get the confirm button rectangle positioned above the bulldoze button"""
        button_w = 150
        button_h = 40
        margin = 12
        # Position above the bulldoze button (which is on the right)
        x = screen_width - margin - button_w
        y = screen_height - button_h - margin - 50  # 50 pixels above bulldoze button
        self.confirm_rect = pygame.Rect(x, y, button_w, button_h)
        return self.confirm_rect
        
    def draw_highlight(self, screen: pygame.Surface, camera_x: int, camera_y: int, grid_size: int) -> None:
        """Draw red highlighting for cells to be bulldozed"""
        if not self.highlighted_cells:
            return
            
        for cell in self.highlighted_cells:
            # Convert cell to screen coordinates
            rect = pygame.Rect(
                cell[0] * grid_size - camera_x,
                cell[1] * grid_size - camera_y,
                grid_size,
                grid_size
            )
            
            # Draw semi-transparent red highlight
            highlight_surface = pygame.Surface((grid_size, grid_size), pygame.SRCALPHA)
            highlight_surface.fill(BULLDOZE_HIGHLIGHT)
            screen.blit(highlight_surface, rect)
            
            # Draw red border
            pygame.draw.rect(screen, (255, 100, 100), rect, 2)
            
    def draw_confirm_button(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw the confirm button above the bulldoze button"""
        if self.confirm_rect is None:
            return
            
        # Only show confirm button when there are highlighted cells
        if not self.highlighted_cells:
            return
            
        # Draw button background
        pygame.draw.rect(screen, BULLDOZE_CONFIRM_BG, self.confirm_rect, border_radius=6)
        pygame.draw.rect(screen, BULLDOZE_CONFIRM_BORDER, self.confirm_rect, 2, border_radius=6)
        
        # Draw button text
        label = font.render("CONFIRM", True, (255, 255, 255))
        label_rect = label.get_rect(center=self.confirm_rect.center)
        screen.blit(label, label_rect)
        
    def handle_click(self, mouse_pos: Tuple[int, int]) -> bool:
        """Handle click on confirm button, return True if confirmed"""
        if self.confirm_rect and self.confirm_rect.collidepoint(mouse_pos):
            return True
        return False
