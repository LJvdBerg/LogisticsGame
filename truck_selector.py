"""
Truck selection functionality for the logistics game.
Handles keyboard number selection and detailed truck info display.
"""

import pygame
from typing import Optional, Dict, List
from dataclasses import dataclass

# Colors for truck selection UI
SELECTED_TRUCK_BG = (80, 120, 200)
TRUCK_INFO_BG = (45, 45, 52)
TRUCK_INFO_BORDER = (80, 80, 95)
TRUCK_STATUS_IDLE = (120, 120, 120)
TRUCK_STATUS_MOVING = (60, 200, 60)
TRUCK_STATUS_LOADING = (200, 200, 60)
TRUCK_STATUS_UNLOADING = (200, 120, 60)

@dataclass
class TruckInfo:
    """Information about a truck's current status"""
    truck_id: int
    position: tuple
    state: str
    cargo_type: Optional[str]
    cargo_amount: float
    destination: Optional[str]
    path_length: int

class TruckSelector:
    def __init__(self):
        self.selected_truck_id: Optional[int] = None
        self.truck_info_panel_rect: Optional[pygame.Rect] = None
        
    def select_truck_by_number(self, number: int, trucks: List) -> Optional[int]:
        """Select truck by number key (1-9)"""
        if 1 <= number <= 9 and number <= len(trucks):
            return number
        return None
        
    def get_truck_info_panel_rect(self, screen_width: int, screen_height: int) -> pygame.Rect:
        """Get the truck info panel rectangle"""
        panel_width = 300
        panel_height = 200
        margin = 20
        # Position on the right side of the screen
        x = screen_width - panel_width - margin
        y = margin
        self.truck_info_panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        return self.truck_info_panel_rect
        
    def draw_truck_info_panel(self, screen: pygame.Surface, font: pygame.font.Font, 
                             selected_truck, trucks: List) -> None:
        """Draw the truck info panel"""
        if self.truck_info_panel_rect is None:
            self.get_truck_info_panel_rect(screen.get_width(), screen.get_height())
            
        if selected_truck is None:
            return
            
        # Draw panel background
        pygame.draw.rect(screen, TRUCK_INFO_BG, self.truck_info_panel_rect, border_radius=8)
        pygame.draw.rect(screen, TRUCK_INFO_BORDER, self.truck_info_panel_rect, 2, border_radius=8)
        
        # Panel title
        title = font.render(f"TRUCK {selected_truck.truck_id}", True, (255, 255, 255))
        title_rect = title.get_rect(midtop=(self.truck_info_panel_rect.centerx, self.truck_info_panel_rect.y + 10))
        screen.blit(title, title_rect)
        
        # Truck status
        status_color = self._get_status_color(selected_truck.state)
        status_text = f"Status: {selected_truck.state.upper()}"
        status_surf = font.render(status_text, True, status_color)
        screen.blit(status_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 40))
        
        # Cargo information
        if selected_truck.cargo_type:
            cargo_text = f"Cargo: {selected_truck.cargo_type.upper()} ({selected_truck.cargo_amount:.1f})"
            cargo_surf = font.render(cargo_text, True, (255, 255, 255))
            screen.blit(cargo_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 65))
        else:
            cargo_text = "Cargo: Empty"
            cargo_surf = font.render(cargo_text, True, (150, 150, 150))
            screen.blit(cargo_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 65))
        
        # Destination information
        if selected_truck.path_cells:
            if self._is_going_to_base(selected_truck):
                dest_text = "Destination: MAIN BASE"
                dest_color = (60, 200, 60)  # Green for base
            else:
                dest_text = "Destination: Resource Facility"
                dest_color = (200, 200, 60)  # Yellow for resource
            dest_surf = font.render(dest_text, True, dest_color)
            screen.blit(dest_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 90))
            
            # Path length
            path_text = f"Path Length: {len(selected_truck.path_cells)} cells"
            path_surf = font.render(path_text, True, (200, 200, 200))
            screen.blit(path_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 115))
        else:
            dest_text = "Destination: None (Idle)"
            dest_surf = font.render(dest_text, True, (150, 150, 150))
            screen.blit(dest_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 90))
        
        # Resource preview (if going to base)
        if selected_truck.cargo_type and selected_truck.cargo_amount > 0 and self._is_going_to_base(selected_truck):
            resource_text = f"→ Will deliver {selected_truck.cargo_amount:.1f} {selected_truck.cargo_type.upper()}"
            resource_surf = font.render(resource_text, True, (60, 200, 60))
            screen.blit(resource_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 140))
        
        # Keyboard shortcuts hint
        hint_text = "Press 1-9 to select trucks"
        hint_surf = font.render(hint_text, True, (150, 150, 150))
        screen.blit(hint_surf, (self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 170))
        
        # Reset button
        reset_btn_rect = pygame.Rect(self.truck_info_panel_rect.x + 15, self.truck_info_panel_rect.y + 190, 80, 25)
        pygame.draw.rect(screen, (200, 80, 80), reset_btn_rect, border_radius=4)
        pygame.draw.rect(screen, (150, 60, 60), reset_btn_rect, 2, border_radius=4)
        reset_text = font.render("RESET", True, (255, 255, 255))
        reset_rect = reset_text.get_rect(center=reset_btn_rect.center)
        screen.blit(reset_text, reset_rect)
        
        # Store the reset button rect for click detection
        self.reset_button_rect = reset_btn_rect
        
    def handle_reset_click(self, pos: tuple) -> bool:
        """Handle click on reset button, return True if clicked"""
        if hasattr(self, 'reset_button_rect') and self.reset_button_rect.collidepoint(pos):
            return True
        return False
        
    def reset_truck(self, truck) -> None:
        """Reset truck to idle state"""
        if truck:
            truck.state = "idle"
            truck.path_cells.clear()
            truck.cargo_type = None
            truck.cargo_amount = 0.0
            # Clear any saved assignment data
            truck.saved_source = None
            truck.saved_dest = None
            truck.saved_resource = None
            if hasattr(truck, '_dest_cell'):
                delattr(truck, '_dest_cell')
            
    def _get_status_color(self, state: str) -> tuple:
        """Get color for truck status"""
        if state == "idle":
            return TRUCK_STATUS_IDLE
        elif state == "to_source":
            return TRUCK_STATUS_MOVING
        elif state == "to_dest":
            return TRUCK_STATUS_MOVING
        else:
            return TRUCK_STATUS_MOVING
            
    def _is_going_to_base(self, truck) -> bool:
        """Check if truck is heading to the main base"""
        # This will need to be implemented based on your game's logic
        # For now, we'll assume if there's a destination and it's not "to_source", it's going to base
        return truck.state == "to_dest" and hasattr(truck, "_dest_cell")
        
    def draw_truck_numbers(self, screen: pygame.Surface, font: pygame.font.Font, 
                          trucks: List, camera_x: int, camera_y: int) -> None:
        """Draw truck numbers above each truck for easy identification"""
        for i, truck in enumerate(trucks, 1):
            if i <= 9:  # Only show numbers 1-9
                # Only show numbers for deployed trucks (not idle or have a path)
                if truck.state == "idle" and not truck.path_cells:
                    continue
                    
                x = truck.position_px[0] - camera_x
                y = truck.position_px[1] - camera_y - 30  # Above the truck
                
                # Draw number background
                number_text = str(i)
                number_surf = font.render(number_text, True, (255, 255, 255))
                number_rect = number_surf.get_rect(center=(x, y))
                
                # Highlight selected truck
                if truck.truck_id == self.selected_truck_id:
                    # Draw selection indicator
                    pygame.draw.circle(screen, SELECTED_TRUCK_BG, (int(x), int(y)), 12)
                    pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 12, 2)
                else:
                    # Draw regular number background
                    pygame.draw.circle(screen, (80, 80, 80), (int(x), int(y)), 10)
                    pygame.draw.circle(screen, (120, 120, 120), (int(x), int(y)), 10, 1)
                
                # Draw the number
                screen.blit(number_surf, (number_rect.x - number_surf.get_width() // 2, 
                                        number_rect.y - number_surf.get_height() // 2))
