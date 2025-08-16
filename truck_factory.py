"""
Truck factory functionality for the logistics game.
Handles building new trucks with increasing costs.
"""

import pygame
from typing import Tuple, Optional

# Colors for truck factory button
TRUCK_BUTTON_BG = (60, 120, 60)
TRUCK_BUTTON_BORDER = (80, 160, 80)
TRUCK_BUTTON_HOVER = (80, 140, 80)

class TruckFactory:
    def __init__(self):
        self.trucks_built = 0
        self.button_rect: Optional[pygame.Rect] = None
        
    def get_truck_cost(self) -> int:
        """Calculate cost for next truck: 10 + (15 * trucks_built)"""
        return 10 + (15 * self.trucks_built)
        
    def get_button_rect(self, base_rect: pygame.Rect) -> pygame.Rect:
        """Get the + button rectangle positioned on the base"""
        button_size = 24
        # Position the button in the top-right corner of the base
        x = base_rect.x + base_rect.width - button_size - 4
        y = base_rect.y + 4
        self.button_rect = pygame.Rect(x, y, button_size, button_size)
        return self.button_rect
        
    def draw_button(self, screen: pygame.Surface, font: pygame.font.Font, base_rect: pygame.Rect, 
                   bmats: int, can_afford: bool) -> None:
        """Draw the truck building button on the base"""
        if self.button_rect is None:
            self.get_button_rect(base_rect)
            
        # Determine button color based on affordability
        if can_afford:
            bg_color = TRUCK_BUTTON_BG
            border_color = TRUCK_BUTTON_BORDER
        else:
            bg_color = (80, 80, 80)  # Gray when can't afford
            border_color = (100, 100, 100)
            
        # Draw button background
        pygame.draw.rect(screen, bg_color, self.button_rect, border_radius=4)
        pygame.draw.rect(screen, border_color, self.button_rect, 2, border_radius=4)
        
        # Draw + symbol
        plus_color = (255, 255, 255) if can_afford else (150, 150, 150)
        plus_surf = font.render("+", True, plus_color)
        plus_rect = plus_surf.get_rect(center=self.button_rect.center)
        screen.blit(plus_surf, plus_rect)
        
        # Draw cost below the button
        cost_text = f"{self.get_truck_cost()}"
        cost_surf = font.render(cost_text, True, (255, 255, 255) if can_afford else (150, 150, 150))
        cost_x = self.button_rect.centerx - cost_surf.get_width() // 2
        cost_y = self.button_rect.bottom + 2
        screen.blit(cost_surf, (cost_x, cost_y))
        
    def handle_click(self, mouse_pos: Tuple[int, int]) -> bool:
        """Handle click on truck building button, return True if clicked"""
        if self.button_rect and self.button_rect.collidepoint(mouse_pos):
            return True
        return False
        
    def build_truck(self) -> None:
        """Increment truck count after building"""
        self.trucks_built += 1
