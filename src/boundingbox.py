from typing import Tuple, List
from pygame.math import Vector3
from utils import cartesian_to_iso

# Margin to reduce bounding box size for tighter collision detection
MARGIN: int = 2


class BoundingBox:
    """Represents a 3D bounding box for collision detection"""
    
    def __init__(self, world_pos: Vector3, height_in_tiles: float, size_in_tiles: float = 1.0) -> None:
        """Initialize bounding box
        
        Args:
            world_pos: Position in world coordinates (x, y, z)
            height_in_tiles: Height of the entity in tiles (e.g., 1.0 for entities, 2.0 for hero)
            size_in_tiles: Width and length of the entity in tiles (e.g., 2.0 for raft, 1.0 for crate)
        """
        self.world_pos: Vector3 = world_pos
        self.height_in_tiles: float = height_in_tiles

        self.size_in_tiles: float = size_in_tiles
    
    def get_bounding_box(self, tile_h: int) -> Tuple[float, float, float, float]:
        """Get bounding box in world coordinates with margin applied
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of (x, y, width, height) in world coordinates
        """
        x = self.world_pos.x + MARGIN
        y = self.world_pos.y + MARGIN
        # Use size_in_tiles to determine the actual bounding box dimensions
        width = (tile_h * self.size_in_tiles) - (MARGIN * 2)
        height = (tile_h * self.size_in_tiles) - (MARGIN * 2)
        
        return (x, y, width, height)
    
    def get_corners_world(self, tile_h: int) -> Tuple[Tuple[float, float], ...]:
        """Get the four corners of the bounding box in world coordinates
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of 4 corner positions: (left, bottom, right, top)
            Each corner is (x, y) in world coordinates
        """
        x, y, width, height = self.get_bounding_box(tile_h)
        
        left = (x, y + height)
        bottom = (x + width, y + height)
        right = (x + width, y)
        top = (x, y)
        
        return (left, bottom, right, top)
    
    def get_corners_iso(self, tile_h: int, left_offset: int, top_offset: int, 
                        camera_x: float, camera_y: float) -> List[Tuple[float, float]]:
        """Get the four corners of the bounding box in isometric screen coordinates
        
        This is useful for debug drawing.
        
        Args:
            tile_h: Tile height in pixels
            left_offset: Heightmap left offset
            top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
            
        Returns:
            List of 4 corner positions in screen space: [left, bottom, right, top]
        """
        offset_x = (left_offset - 12 + 4) * tile_h - 12
        offset_y = (top_offset - 11 + 4) * tile_h - 12

        corners_world = self.get_corners_world(tile_h)
        corners_iso = []
        
        for wx, wy in corners_world:
            iso_x, iso_y = cartesian_to_iso(wx - offset_x, wy - offset_y)
            corners_iso.append((iso_x - camera_x, iso_y - camera_y))
        
        return corners_iso
    
    def get_center(self, tile_h: int) -> Tuple[float, float]:
        """Get the center position of the bounding box in world XY coordinates
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of (center_x, center_y) in world coordinates
        """
        x, y, width, height = self.get_bounding_box(tile_h)
        return (x + width / 2, y + height / 2)
    
    def update_position(self, world_pos: Vector3) -> None:
        """Update the bounding box position
        
        Args:
            world_pos: New position in world coordinates
        """
        self.world_pos = world_pos