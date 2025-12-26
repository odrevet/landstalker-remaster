import pygame
from pygame.math import Vector2, Vector3
from typing import Tuple, List, Dict, TYPE_CHECKING
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
        self._screen_pos: Vector2 = Vector2()
        
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
    
        self.prev_world_pos = Vector3(x, y, z)

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
    
    def set_animation(self, animation_name: str) -> None:
        """Set the current animation
        
        Args:
            animation_name: Name of the animation to play
        """
        if animation_name in self.animations and animation_name != self.current_animation:
            self.current_animation = animation_name
            self.current_frame = 0
            self.animation_timer = 0.0
    
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
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the object on the surface
        
        Args:
            surface: Pygame surface to draw on
        """
        if self.image:
            surface.blit(self.image, self._screen_pos)