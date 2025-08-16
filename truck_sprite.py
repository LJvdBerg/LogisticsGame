"""
Truck sprite rendering for the logistics game.
Handles truck sprite rotation based on movement direction.
"""

import pygame
import math
from typing import Tuple, Optional, List

class TruckSprite:
    def __init__(self, width: int = 36, height: int = 24):
        """Initialize truck sprite with given dimensions (150% larger)"""
        self.width = width
        self.height = height
        self.sprite_surface = self._create_truck_sprite()
        
    def _create_truck_sprite(self) -> pygame.Surface:
        """Load the real truck sprite image"""
        try:
            # Load the truck image from the LogisticsGame folder
            image_path = "LogisticsGame/Truck.png"
            sprite = pygame.image.load(image_path).convert_alpha()
            
            # Scale the image to the desired size if needed
            if sprite.get_width() != self.width or sprite.get_height() != self.height:
                # Use smoothscale for better quality when scaling down
                sprite = pygame.transform.smoothscale(sprite, (self.width, self.height))
            
            return sprite
        except pygame.error as e:
            print(f"Could not load truck sprite: {e}")
            # Fallback to generated sprite if image loading fails
            return self._create_fallback_sprite()
    
    def _create_fallback_sprite(self) -> pygame.Surface:
        """Create a fallback truck sprite if image loading fails"""
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Draw the truck body (orange rounded rectangle)
        truck_color = (255, 140, 0)  # Orange color
        truck_rect = pygame.Rect(0, 0, self.width, self.height)
        pygame.draw.rect(surface, truck_color, truck_rect, border_radius=4)
        
        # Add some details to make it look more like a truck
        # Front window (slightly darker)
        window_color = (200, 110, 0)
        window_rect = pygame.Rect(self.width - 8, 2, 6, self.height - 4)
        pygame.draw.rect(surface, window_color, window_rect, border_radius=2)
        
        # Back details
        detail_color = (220, 120, 0)
        detail_rect = pygame.Rect(2, 2, 4, self.height - 4)
        pygame.draw.rect(surface, detail_color, detail_rect, border_radius=2)
        
        return surface
        
    def get_rotated_sprite(self, direction: Tuple[float, float]) -> pygame.Surface:
        """Get truck sprite rotated to face the movement direction"""
        if direction == (0, 0):
            # No movement, return original sprite (facing right)
            return self.sprite_surface
            
        # Calculate angle from direction vector
        # Note: pygame's rotate uses clockwise rotation, and 0 degrees is right
        # We need to convert our direction vector to the correct angle
        angle = math.degrees(math.atan2(-direction[1], direction[0]))
        
        # Rotate the sprite
        rotated = pygame.transform.rotate(self.sprite_surface, angle)
        
        return rotated
        
    def draw_truck(self, screen: pygame.Surface, position: Tuple[float, float], 
                   direction: Tuple[float, float], camera_x: int, camera_y: int) -> None:
        """Draw the truck sprite at the given position with proper rotation"""
        # Get rotated sprite
        sprite = self.get_rotated_sprite(direction)
        
        # Calculate screen position
        screen_x = int(position[0] - camera_x - sprite.get_width() // 2)
        screen_y = int(position[1] - camera_y - sprite.get_height() // 2)
        
        # Draw the sprite
        screen.blit(sprite, (screen_x, screen_y))
        
    def get_truck_direction(self, current_pos: Tuple[float, float], 
                           target_pos: Tuple[float, float]) -> Tuple[float, float]:
        """Calculate direction vector from current to target position"""
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        
        # Normalize the direction vector
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            return (dx / length, dy / length)
        return (0, 0)
    
    def get_smooth_direction(self, current_pos: Tuple[float, float], 
                            target_pos: Tuple[float, float], 
                            current_direction: Tuple[float, float],
                            smoothing_factor: float = 0.1) -> Tuple[float, float]:
        """Calculate smooth direction with interpolation to prevent jerky rotation"""
        # Get the ideal direction
        ideal_direction = self.get_truck_direction(current_pos, target_pos)
        
        # If no ideal direction (stationary), keep current direction
        if ideal_direction == (0, 0):
            return current_direction
        
        # Interpolate between current and ideal direction
        smooth_x = current_direction[0] + (ideal_direction[0] - current_direction[0]) * smoothing_factor
        smooth_y = current_direction[1] + (ideal_direction[1] - current_direction[1]) * smoothing_factor
        
        # Normalize the smoothed direction
        length = math.sqrt(smooth_x * smooth_x + smooth_y * smooth_y)
        if length > 0:
            return (smooth_x / length, smooth_y / length)
        return ideal_direction
    
    def get_path_based_direction(self, current_pos: Tuple[float, float], 
                                path_cells: List, 
                                current_direction: Tuple[float, float],
                                smoothing_factor: float = 0.15) -> Tuple[float, float]:
        """Calculate direction based on the actual path cells for better movement"""
        if not path_cells:
            return current_direction
            
        # Get the next cell in the path
        next_cell = path_cells[0]
        target_pos = (
            next_cell[0] * 32 + 16,  # Assuming GRID_SIZE = 32
            next_cell[1] * 32 + 16
        )
        
        # Calculate ideal direction to next cell
        ideal_direction = self.get_truck_direction(current_pos, target_pos)
        
        # If no ideal direction, keep current
        if ideal_direction == (0, 0):
            return current_direction
        
        # Calculate the angle difference between current and ideal direction
        current_angle = math.atan2(current_direction[1], current_direction[0])
        ideal_angle = math.atan2(ideal_direction[1], ideal_direction[0])
        
        # Handle angle wrapping (e.g., -180 to 180 degrees)
        angle_diff = ideal_angle - current_angle
        if angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        elif angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Apply smoothing to the angle change
        smoothed_angle = current_angle + angle_diff * smoothing_factor
        
        # Convert back to direction vector
        return (math.cos(smoothed_angle), math.sin(smoothed_angle))
    
    def get_grid_aligned_direction(self, current_pos: Tuple[float, float], 
                                  path_cells: List, 
                                  current_direction: Tuple[float, float],
                                  smoothing_factor: float = 0.2) -> Tuple[float, float]:
        """Calculate direction with perfect grid alignment for 90-degree rotations"""
        if not path_cells:
            return current_direction
            
        # Get the next cell in the path
        next_cell = path_cells[0]
        target_pos = (
            next_cell[0] * 32 + 16,  # Assuming GRID_SIZE = 32
            next_cell[1] * 32 + 16
        )
        
        # Calculate ideal direction to next cell
        ideal_direction = self.get_truck_direction(current_pos, target_pos)
        
        # If no ideal direction, keep current
        if ideal_direction == (0, 0):
            return current_direction
        
        # Calculate the angle difference between current and ideal direction
        current_angle = math.atan2(current_direction[1], current_direction[0])
        ideal_angle = math.atan2(ideal_direction[1], ideal_direction[0])
        
        # Handle angle wrapping (e.g., -180 to 180 degrees)
        angle_diff = ideal_angle - current_angle
        if angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        elif angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Apply smoothing to the angle change
        smoothed_angle = current_angle + angle_diff * smoothing_factor
        
        # Snap to grid-aligned angles for better visual alignment
        # This ensures perfect 90-degree rotations
        grid_angles = [0, math.pi/2, math.pi, -math.pi/2]  # Right, Down, Left, Up
        closest_grid_angle = min(grid_angles, key=lambda x: abs(x - smoothed_angle))
        
        # If we're close to a grid angle, snap to it
        if abs(smoothed_angle - closest_grid_angle) < 0.3:  # Within ~17 degrees
            smoothed_angle = closest_grid_angle
        
        # Convert back to direction vector
        return (math.cos(smoothed_angle), math.sin(smoothed_angle))
