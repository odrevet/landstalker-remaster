import pygame
from pygame.math import Vector2, Vector3
from typing import Tuple, List, Dict, Optional, TYPE_CHECKING
from utils import cartesian_to_iso

if TYPE_CHECKING:
    from boundingbox import BoundingBox

class Drawable:
    """Base class for drawable game objects with position management and animation support"""
    
    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        """Initialize drawable object with world position
        
        Args:
            x: World X coordinate
            y: World Y coordinate
            z: World Z coordinate (height)
        """
        self._world_pos: Vector3 = Vector3(x, y, z)
        self.prev_world_pos = self._world_pos.copy()
        self._screen_pos: Vector2 = Vector2()
        self.display_rotated = False

        # props
        self.orientation: str = 'SW'
        self.no_rotate: bool = False
        self.visible: bool = True

        self.sprite_sheet: Optional[pygame.Surface] = None  # Full sprite sheet

        # Cache for update_screen_pos parameters
        self._heightmap_left_offset: int = 0
        self._heightmap_top_offset: int = 0
        self._camera_x: float = 0
        self._camera_y: float = 0
        
        # Image to be set by subclass
        self.image: pygame.Surface = None
        
        # Bounding box - to be initialized by subclass
        self.bbox: 'BoundingBox' = None
        
        # Animation support
        self.animations: Dict[str, List[pygame.Surface]] = {}
        self.current_animation: str = ""
        self.current_frame: int = 0
        self.animation_speed: float = 0.15  # Default animation speed
        self.animation_timer: float = 0.0
        
    def get_position_delta(self) -> tuple:
        """Get the change in position since last frame"""
        dx = self._world_pos.x - self.prev_world_pos.x
        dy = self._world_pos.y - self.prev_world_pos.y
        dz = self._world_pos.z - self.prev_world_pos.z
        return (dx, dy, dz)

    def update_prev_position(self) -> None:
        """Store current position for next frame's delta calculation"""
        self.prev_world_pos.x = self._world_pos.x
        self.prev_world_pos.y = self._world_pos.y
        self.prev_world_pos.z = self._world_pos.z

    def get_world_pos(self) -> Vector3:
        """Get the object's world position
        
        Returns:
            Vector3 containing x, y, z coordinates
        """
        return self._world_pos
    
    def set_world_pos(self, x: float, y: float, z: float, 
                     heightmap_left_offset: int, heightmap_top_offset: int, 
                     camera_x: float, camera_y: float, tilemap_height: int) -> None:
        """Set the object's world position and update screen position
        
        Args:
            x: World X coordinate
            y: World Y coordinate
            z: World Z coordinate (height)
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
            tilemap_height: Map height
        """
        self._world_pos.x = x
        self._world_pos.y = y
        self._world_pos.z = z
        self._update_screen_pos(heightmap_left_offset, heightmap_top_offset, camera_x, camera_y, tilemap_height)
        
        # Update bounding box if it exists
        if self.bbox is not None:
            self.bbox.world_pos = self._world_pos
    
    def set_world_x(self, x: float) -> None:
        self._world_pos.x = x

    def set_world_y(self, y: float) -> None:
        self._world_pos.y = y

    def set_world_z(self, z: float) -> None:
        self._world_pos.z = z

    def add_world_x(self, dx: float) -> None:
        self._world_pos.x += dx

    def add_world_y(self, dy: float) -> None:
        self._world_pos.y += dy

    def add_world_z(self, dz: float) -> None:
        self._world_pos.z += dz

    def update_camera(self, heightmap_left_offset: int, heightmap_top_offset: int, 
                     camera_x: float, camera_y: float, tilemap_height:int) -> None:
        """Update screen position when camera moves without changing world position
        
        Args:
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
            tilemap_height: Map height
        """
        self._update_screen_pos(heightmap_left_offset, heightmap_top_offset, camera_x, camera_y, tilemap_height)
    
    def _update_screen_pos(self, heightmap_left_offset: int, heightmap_top_offset: int, 
                        camera_x: float, camera_y: float, tilemap_height: int) -> None:
        """Update screen position based on world position and camera
        
        Matches C++ EntityPositionToPixel function exactly
        
        Args:
            heightmap_left_offset: Heightmap left offset (GetLeft())
            heightmap_top_offset: Heightmap top offset (GetTop())
            camera_x: Camera X position
            camera_y: Camera Y position
            tilemap_height: Map height (GetHeight())
        """    
        SCALE_FACTOR = 256  # 0x100

        # Scale offsets
        LEFT = heightmap_left_offset * SCALE_FACTOR
        TOP = heightmap_top_offset * SCALE_FACTOR
        HEIGHT = tilemap_height * SCALE_FACTOR

        x = self._world_pos.x * SCALE_FACTOR + 0x80   # +128
        y = self._world_pos.y * SCALE_FACTOR - 0x80   # -128
        z = self._world_pos.z * SCALE_FACTOR

        # hitbox width/length
        if self.bbox.size_in_tiles * 8 >= 0x0C:
            x += 0x80
            y += 0x80

        xx = x - LEFT
        yy = y - TOP

        ix:int = (xx - yy + (HEIGHT - SCALE_FACTOR)) * 2 + LEFT
        iy:int = (xx + yy - z * 2) + TOP

        tile_width = 8
        tile_height = 8

        px:int = (ix * tile_width)  // SCALE_FACTOR
        py:int = (iy * tile_height) // SCALE_FACTOR

        # Get subsprite offsets if available (from Entity class animation YAML)
        subsprite_x = 0
        subsprite_y = 0
        
        if hasattr(self, 'animation_yaml') and self.animation_yaml:
            # Get current frame index
            frame_idx = 0
            if hasattr(self, 'fixed_frame_index') and self.fixed_frame_index is not None:
                frame_idx = self.fixed_frame_index
            elif hasattr(self, 'current_frame'):
                frame_idx = self.current_frame
            
            # Navigate to frames array in animation YAML
            frames = self.animation_yaml.get('frames', [])
            
            # Check if we have a valid frame entry
            if frame_idx < len(frames):
                frame_data = frames[frame_idx]
                
                # Check if frame_data has subsprites
                if isinstance(frame_data, dict) and 'subsprites' in frame_data:
                    subsprites = frame_data['subsprites']
                    
                    # Use first subsprite's x and y offsets
                    if isinstance(subsprites, list) and len(subsprites) > 0:
                        first_subsprite = subsprites[0]
                        if isinstance(first_subsprite, list) and len(first_subsprite) >= 2:
                            subsprite_x = first_subsprite[0]
                            subsprite_y = first_subsprite[1]

        sx:int = px + subsprite_x
        sy:int = py + subsprite_y

        self._screen_pos.x = sx - camera_x
        self._screen_pos.y = sy - camera_y

    def get_screen_pos(self) -> Vector2:
        """Get the object's screen position
        
        Returns:
            Vector2 containing screen x, y coordinates
        """
        return self._screen_pos
    
    def get_bounding_box(self, tile_h: int) -> Tuple[float, float, float, float]:
        """Get object's bounding box in world coordinates with margin applied
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of (x, y, width, height) in world coordinates
        """
        if self.bbox is not None:
            return self.bbox.get_bounding_box(tile_h)
        return (0, 0, 0, 0)
    
    def get_bbox_corners_world(self, tile_h: int) -> Tuple[Tuple[float, float], ...]:
        """Get the four corners of the object's bounding box in world coordinates
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of 4 corner positions: (left, bottom, right, top)
            Each corner is (x, y) in world coordinates
        """
        if self.bbox is not None:
            return self.bbox.get_corners_world(tile_h)
        return ((0, 0), (0, 0), (0, 0), (0, 0))
    
    def extract_frames(self, spritesheet: pygame.Surface, frame_width: int, 
                      frame_height: int, num_frames: int) -> List[pygame.Surface]:
        """Extract individual frames from a spritesheet
        
        Args:
            spritesheet: The sprite sheet surface
            frame_width: Width of each frame
            frame_height: Height of each frame
            num_frames: Number of frames to extract
            
        Returns:
            List of frame surfaces
        """
        frames = []
        for i in range(num_frames):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(spritesheet, (0, 0), (i * frame_width, 0, frame_width, frame_height))
            frames.append(frame)
        return frames
    
    def load_animation_from_file(self, animation_name: str, file_path: str, 
                                frame_width: int, frame_height: int, num_frames: int) -> bool:
        """Load an animation from a sprite sheet file
        
        Args:
            animation_name: Name to store the animation under
            file_path: Path to the sprite sheet file
            frame_width: Width of each frame
            frame_height: Height of each frame  
            num_frames: Number of frames to extract
            
        Returns:
            True if animation loaded successfully, False otherwise
        """
        try:
            sheet = pygame.image.load(file_path).convert_alpha()
            self.animations[animation_name] = self.extract_frames(sheet, frame_width, frame_height, num_frames)
            return True
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load animation {animation_name} from {file_path}: {e}")
            return False
    
    def set_animation(self, animation_name: str) -> None:
        """Set the current animation
        
        Args:
            animation_name: Name of the animation to play
        """
        if animation_name in self.animations and animation_name != self.current_animation:
            self.current_animation = animation_name
            self.current_frame = 0
            self.animation_timer = 0.0
            # Update image immediately to first frame
            if self.animations[animation_name]:
                self.image = self.animations[animation_name][0]
    
    def update_animation_frame(self, advance: bool = True) -> None:
        """Update the current animation frame
        
        Args:
            advance: Whether to advance the frame based on timer (True) or keep current frame (False)
        """
        if not self.current_animation or self.current_animation not in self.animations:
            return
        
        frames = self.animations[self.current_animation]
        
        if len(frames) <= 1:
            # Single frame animation
            if frames:
                self.image = frames[0]
            return
        
        if advance:
            # Multi-frame animation - advance based on timer
            self.animation_timer += self.animation_speed
            if self.animation_timer >= 1.0:
                self.animation_timer = 0.0
                self.current_frame = (self.current_frame + 1) % len(frames)
        
        # Update image to current frame
        self.image = frames[self.current_frame]
    
    def set_animation_frame(self, frame_index: int) -> None:
        """Set a specific animation frame manually
        
        Args:
            frame_index: Index of the frame to display
        """
        if not self.current_animation or self.current_animation not in self.animations:
            return
        
        frames = self.animations[self.current_animation]
        if 0 <= frame_index < len(frames):
            self.current_frame = frame_index
            self.image = frames[frame_index]
    
    def get_animation_for_orientation(self, base_animation: str, orientation: Optional[str] = None) -> str:
        """Get the appropriate animation name based on orientation
        
        Args:
            base_animation: Base animation name (e.g., "walk", "idle")
            orientation: Direction to face (NE, SE, SW, NW), uses self.orientation if None
            
        Returns:
            Full animation name with direction suffix (e.g., "walk_back", "idle_front")
        """
        if orientation is None:
            orientation = self.orientation
        
        # Map orientations to animation suffixes
        direction_map = {
            "NE": "back",
            "SE": "front", 
            "NW": "back",
            "SW": "front",
        }
        
        direction = direction_map.get(orientation, "front")
        return f"{base_animation}_{direction}"
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the object on the surface
        
        Args:
            surface: Pygame surface to draw on
        """
        if self.visible and self.image is not None:
            display_image = self.image 
            if self.display_rotated:
                display_image = pygame.transform.flip(self.image, True, False)
            surface.blit(display_image, self._screen_pos)

    def update_display_rotated(self) -> None:
        self.display_rotated = self.no_rotate == False and self.orientation in ("SE", "NW")

    def set_orientation(self, orientation, update_display_rotate = True) -> None:
        self.orientation = orientation
        if update_display_rotate:
            self.update_display_rotated()