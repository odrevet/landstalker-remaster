from typing import Dict, Tuple, Any

class Warp:
    """Represents a warp zone that transitions between rooms"""
    
    def __init__(self, warp_data: Dict[str, Any]) -> None:
        self.room1: int = warp_data['room1']
        self.room2: int = warp_data['room2']
        # Warp data contains tile indices
        self.x: int = warp_data['x']
        self.y: int = warp_data['y']
        self.x2: int = warp_data['x2']
        self.y2: int = warp_data['y2']
        self.width: int = warp_data['width']
        self.height: int = warp_data['height']
        self.warp_type: str = warp_data['type']
        
        # Debug: Print warp initialization
        print(f"\n=== WARP INITIALIZED ===")
        print(f"Type: {self.warp_type}")
        print(f"Room1: {self.room1} at tile ({self.x}, {self.y})")
        print(f"Room2: {self.room2} at tile ({self.x2}, {self.y2})")
        print(f"Size: {self.width}x{self.height} tiles")
        print(f"========================\n")

    def check_collision(
        self, 
        hero_x: float, 
        hero_y: float, 
        hero_width: float, 
        hero_height: float, 
        tile_h: int, 
        current_room: int, 
        heightmap: Any
    ) -> bool:
        """Check if hero collides with this warp zone
        
        Args:
            hero_x, hero_y: Hero position in PIXELS (from bounding box)
            hero_width, hero_height: Hero size in PIXELS (from bounding box)
            tile_h: Tile height in pixels
            current_room: Current room number
            heightmap: Heightmap object for offset calculations
            
        Returns:
            True if hero is in warp zone
        """
        # Get the correct warp tile coordinates based on current room
        if self.room1 == current_room:
            warp_tile_x = self.x
            warp_tile_y = self.y
        else:
            warp_tile_x = self.x2
            warp_tile_y = self.y2
        
        # Convert hero PIXEL position to tile coordinates
        # Use center of hero's bounding box
        hero_center_x_pixels = hero_x + hero_width // 2
        hero_center_y_pixels = hero_y + hero_height // 2
                
        hero_tile_x = int(hero_center_x_pixels)
        hero_tile_y = int(hero_center_y_pixels)
        
        # Point-in-rectangle collision: check if hero tile is within warp bounds
        x_in_range = warp_tile_x  - 12 <= hero_tile_x < warp_tile_x  - 12 + self.width
        y_in_range = warp_tile_y  - 12 <= hero_tile_y < warp_tile_y  - 12 + self.height
        
        collision = x_in_range and y_in_range
        
        return collision

    def get_destination(
        self, 
        current_room: int, 
        heightmap: Any
    ) -> Tuple[int, int]:
        """Get the destination coordinates in TILE coordinates
        
        Args:
            current_room: Current room number
            heightmap: Heightmap object (for consistency, not used)
            
        Returns:
            Tuple of (x, y) in TILE coordinates
        """
        if current_room == self.room1:
            # Going from room1 to room2
            dest_tile_x = self.x2  # Note: swapped! Going TO room2
            dest_tile_y = self.y2
        else:
            # Going from room2 to room1
            dest_tile_x = self.x   # Going TO room1
            dest_tile_y = self.y
        
        # Apply 12-tile offset
        tile_x = dest_tile_x - 12
        tile_y = dest_tile_y - 12
        
        print(f"\n*** WARP DESTINATION ***")
        print(f"From room {current_room} to room {self.get_target_room(current_room)}")
        print(f"Raw destination tile: ({dest_tile_x}, {dest_tile_y})")
        print(f"Adjusted destination: ({tile_x}, {tile_y})")
        print(f"************************\n")
        
        return tile_x, tile_y

    def get_target_room(self, current_room: int) -> int:
        """Get the target room based on current room"""
        return self.room2 if current_room == self.room1 else self.room1