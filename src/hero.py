import pygame
from pygame.math import Vector2, Vector3
from typing import Tuple, List, Optional, Dict, TYPE_CHECKING
from utils import cartesian_to_iso
from boundingbox import BoundingBox
from drawable import Drawable

if TYPE_CHECKING:
    from entity import Entity


class Hero(Drawable):
    """Represents the player character with animation, movement, and interaction capabilities"""
    
    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        """Initialize the hero at given world coordinates
        
        Args:
            x: World X coordinate
            y: World Y coordinate  
            z: World Z coordinate (height)
        """
        super().__init__(x, y, z)
        
        # Physical properties
        self.HEIGHT: int = 2   # Height in tiles
        
        # Animation setup
        self.animations: Dict[str, List[pygame.Surface]] = {}
        self.current_animation: str = "idle_front"
        self.current_frame: int = 0
        self.animation_speed: float = 0.15  # Frames per game tick
        self.animation_timer: float = 0.0
        
        # Load all animations
        self._load_animations()
        
        # Set initial image
        self.image: pygame.Surface = self.animations[self.current_animation][0]
        
        # Movement and state
        self.touch_ground: bool = False
        self.is_jumping: bool = False
        self.current_jump: int = 0
        self.is_moving: bool = False
        self.facing_direction: str = "DOWN"  # Can be: "UP", "DOWN", "LEFT", "RIGHT"
        
        # Interaction state
        self.is_grabbing: bool = False
        self.grabbed_entity: Optional['Entity'] = None
        
        # Bounding box for collision detection
        self.bbox: BoundingBox = BoundingBox(self._world_pos, self.HEIGHT)
    
    def _load_animations(self) -> None:
        """Load all animation spritesheets and extract frames"""
        try:
            # Idle animations (32x48 - single frame)
            idle_back = pygame.image.load('data/sprites/SpriteGfx000Anim000.png').convert_alpha()
            idle_front = pygame.image.load('data/sprites/SpriteGfx000Anim001.png').convert_alpha()
            
            self.animations["idle_back"] = [idle_back]
            self.animations["idle_front"] = [idle_front]
            
            # Walk animations (256x48 - 8 frames of 32x48 each)
            walk_back_sheet = pygame.image.load('data/sprites/SpriteGfx000Anim002.png').convert_alpha()
            walk_front_sheet = pygame.image.load('data/sprites/SpriteGfx000Anim003.png').convert_alpha()
            
            self.animations["walk_back"] = self._extract_frames(walk_back_sheet, 32, 48, 8)
            self.animations["walk_front"] = self._extract_frames(walk_front_sheet, 32, 48, 8)
            
            # Jump animations (64x48 - 2 frames of 32x48 each)
            jump_back_sheet = pygame.image.load('data/sprites/SpriteGfx000Anim008.png').convert_alpha()
            jump_front_sheet = pygame.image.load('data/sprites/SpriteGfx000Anim009.png').convert_alpha()
            
            self.animations["jump_back"] = self._extract_frames(jump_back_sheet, 32, 48, 2)
            self.animations["jump_front"] = self._extract_frames(jump_front_sheet, 32, 48, 2)
            
            # Left/right animations (use back/front as base, will be flipped)
            self.animations["idle_left"] = [idle_back]
            self.animations["idle_right"] = [idle_back]
            self.animations["walk_left"] = self.animations["walk_back"]
            self.animations["walk_right"] = self.animations["walk_front"]
            self.animations["jump_left"] = self.animations["jump_back"]
            self.animations["jump_right"] = self.animations["jump_front"]
            
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load animation sprites: {e}")
            # Create placeholder
            placeholder = pygame.Surface((32, 48), pygame.SRCALPHA)
            placeholder.fill((255, 0, 255, 128))
            
            # Initialize all animations with placeholder
            for anim_name in ["idle_front", "idle_back", "idle_left", "idle_right"]:
                self.animations[anim_name] = [placeholder]
            
            for anim_name in ["walk_front", "walk_back", "walk_left", "walk_right"]:
                self.animations[anim_name] = [placeholder] * 8
            
            for anim_name in ["jump_front", "jump_back", "jump_left", "jump_right"]:
                self.animations[anim_name] = [placeholder] * 2
    
    def _extract_frames(self, spritesheet: pygame.Surface, frame_width: int, 
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
    
    def update_animation(self, is_moving: bool) -> None:
        """Update the current animation based on movement state and direction
        
        Args:
            is_moving: Whether the hero is currently moving
        """
        self.is_moving = is_moving
        
        # Determine which animation to play based on priority: jumping > moving > idle
        new_animation = self._select_animation(is_moving)
        
        # Reset frame if animation changed
        if new_animation != self.current_animation:
            self.current_animation = new_animation
            self.current_frame = 0
            self.animation_timer = 0.0
        
        # Update animation frame
        self._update_animation_frame(is_moving)
        
        # Update current image
        self._update_image()
    
    def _select_animation(self, is_moving: bool) -> str:
        """Select the appropriate animation based on current state
        
        Args:
            is_moving: Whether the hero is moving
            
        Returns:
            Name of the animation to play
        """
        # Animation priority: jumping > moving > idle
        if self.is_jumping:
            prefix = "jump"
        elif is_moving:
            prefix = "walk"
        else:
            prefix = "idle"
        
        # Direction mapping
        if self.facing_direction == "UP":
            suffix = "back"
        elif self.facing_direction == "DOWN" or self.facing_direction == "RIGHT":
            suffix = "front"
        elif self.facing_direction == "LEFT":
            suffix = "left"
        else:
            suffix = "front"
        
        return f"{prefix}_{suffix}"
    
    def _update_animation_frame(self, is_moving: bool) -> None:
        """Update the current animation frame based on state
        
        Args:
            is_moving: Whether the hero is moving
        """
        if self.is_jumping:
            # For jump: frame 0 = ascending, frame 1 = descending
            jump_peak = 12  # Half of HERO_MAX_JUMP (24 / 2)
            self.current_frame = 0 if self.current_jump < jump_peak else 1
        elif is_moving or len(self.animations[self.current_animation]) == 1:
            # For walk animations, advance frame based on timer
            self.animation_timer += self.animation_speed
            if self.animation_timer >= 1.0:
                self.animation_timer = 0.0
                num_frames = len(self.animations[self.current_animation])
                self.current_frame = (self.current_frame + 1) % num_frames
    
    def _update_image(self) -> None:
        """Update the current image based on animation frame and facing direction"""
        base_image = self.animations[self.current_animation][self.current_frame]
        
        # Mirror image when facing left or right
        if self.facing_direction in ("LEFT", "RIGHT"):
            self.image = pygame.transform.flip(base_image, True, False)
        else:
            self.image = base_image
    
    def update_facing_direction(self, dx: float, dy: float) -> None:
        """Update hero's facing direction based on movement delta
        
        Args:
            dx: Change in X position
            dy: Change in Y position
        """
        # Only update if there's actual movement
        if dx == 0 and dy == 0:
            return
        
        # Priority: favor the axis with larger movement
        if abs(dx) > abs(dy):
            self.facing_direction = "LEFT" if dx < 0 else "RIGHT"
        else:
            self.facing_direction = "UP" if dy < 0 else "DOWN"
    
    def _update_screen_pos(self, heightmap_left_offset: int, heightmap_top_offset: int, 
                          camera_x: float, camera_y: float) -> None:
        """Update screen position based on world position and camera
        
        Overridden from Drawable to apply Hero-specific positioning
        
        Args:
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        # Cache parameters
        self._heightmap_left_offset = heightmap_left_offset
        self._heightmap_top_offset = heightmap_top_offset
        self._camera_x = camera_x
        self._camera_y = camera_y
        
        # Calculate offset
        offset_x: float = (heightmap_left_offset - 12 + 4) * 16
        offset_y: float = (heightmap_top_offset - 11 + 4) * 16
        
        # Convert to isometric coordinates
        iso_x, iso_y = cartesian_to_iso(
            self._world_pos.x - offset_x, 
            self._world_pos.y - offset_y
        )
        
        # Apply hero-specific positioning
        HERO_HEIGHT: int = 32
        self._screen_pos.x = iso_x - 16 - camera_x
        self._screen_pos.y = iso_y - self._world_pos.z + 12 - camera_y + HERO_HEIGHT
    
    def grab_entity(self, entity: 'Entity') -> None:
        """Start grabbing an entity
        
        Args:
            entity: The entity to grab
        """
        self.is_grabbing = True
        self.grabbed_entity = entity
    
    def release_entity(self) -> None:
        """Release the currently grabbed entity"""
        self.is_grabbing = False
        self.grabbed_entity = None
    
    def update_grabbed_entity_position(self, left_offset: int, top_offset: int, 
                                      camera_x: float, camera_y: float, tile_h: int) -> None:
        """Update the position of the grabbed entity to be above the hero
        
        Args:
            left_offset: Heightmap left offset
            top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
            tile_h: Tile height in pixels
        """
        if self.grabbed_entity is None:
            return
        
        # Position entity directly above hero (HEIGHT tiles higher in Z)
        hero_pos = self.get_world_pos()
        entity_z = hero_pos.z + (self.HEIGHT * tile_h)
        
        # Update entity position
        self.grabbed_entity.set_world_pos(
            hero_pos.x, 
            hero_pos.y, 
            entity_z,
            left_offset,
            top_offset,
            camera_x,
            camera_y
        )
    
    def __repr__(self) -> str:
        """String representation of the Hero"""
        return (f"Hero(pos={self._world_pos}, facing={self.facing_direction}, "
                f"jumping={self.is_jumping}, moving={self.is_moving}, "
                f"grabbing={self.is_grabbing})")