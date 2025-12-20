import pygame
from pygame.math import Vector2, Vector3
from utils import cartesian_to_iso


class Drawable:
    """Base class for drawable game objects with position management"""
    
    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        """Initialize drawable object with world position
        
        Args:
            x: World X coordinate
            y: World Y coordinate
            z: World Z coordinate (height)
        """
        self._world_pos: Vector3 = Vector3(x, y, z)
        self._screen_pos: Vector2 = Vector2()
        
        # Cache for update_screen_pos parameters
        self._heightmap_left_offset: int = 0
        self._heightmap_top_offset: int = 0
        self._camera_x: float = 0
        self._camera_y: float = 0
        
        # Image to be set by subclass
        self.image: pygame.Surface = None
    
    def get_world_pos(self) -> Vector3:
        """Get the object's world position
        
        Returns:
            Vector3 containing x, y, z coordinates
        """
        return self._world_pos
    
    def set_world_pos(self, x: float, y: float, z: float, 
                     heightmap_left_offset: int, heightmap_top_offset: int, 
                     camera_x: float, camera_y: float) -> None:
        """Set the object's world position and update screen position
        
        Args:
            x: World X coordinate
            y: World Y coordinate
            z: World Z coordinate (height)
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        self._world_pos.x = x
        self._world_pos.y = y
        self._world_pos.z = z
        self._update_screen_pos(heightmap_left_offset, heightmap_top_offset, camera_x, camera_y)
    
    def update_camera(self, heightmap_left_offset: int, heightmap_top_offset: int, 
                     camera_x: float, camera_y: float) -> None:
        """Update screen position when camera moves without changing world position
        
        Args:
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        self._update_screen_pos(heightmap_left_offset, heightmap_top_offset, camera_x, camera_y)
    
    def _update_screen_pos(self, heightmap_left_offset: int, heightmap_top_offset: int, 
                          camera_x: float, camera_y: float) -> None:
        """Update screen position based on world position and camera (private)
        
        This method should be overridden by subclasses if they need custom screen positioning
        
        Args:
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        # Cache the parameters for potential future use
        self._heightmap_left_offset = heightmap_left_offset
        self._heightmap_top_offset = heightmap_top_offset
        self._camera_x = camera_x
        self._camera_y = camera_y
        
        offset_x: float = (heightmap_left_offset - 12 + 4) * 16
        offset_y: float = (heightmap_top_offset - 11 + 4) * 16
        
        iso_x: float
        iso_y: float
        iso_x, iso_y = cartesian_to_iso(self._world_pos.x - offset_x, self._world_pos.y - offset_y)
        
        self._screen_pos.x = iso_x - 16 - camera_x
        self._screen_pos.y = iso_y - self._world_pos.z - camera_y
    
    def get_screen_pos(self) -> Vector2:
        """Get the object's screen position
        
        Returns:
            Vector2 containing screen x, y coordinates
        """
        return self._screen_pos
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the object on the surface
        
        Args:
            surface: Pygame surface to draw on
        """
        if self.image:
            surface.blit(self.image, self._screen_pos)