import pygame
from typing import Optional, TYPE_CHECKING
from utils import cartesian_to_iso
from boundingbox import BoundingBox
from drawable import Drawable

if TYPE_CHECKING:
    from entity import Entity


class Hero(Drawable):
    """Represents the player character with animation, movement, and interaction capabilities"""
    
    # Animation constants
    ANIMATION_SPEED = 0.15  # Frames per game tick
    
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
        
        # Set animation speed
        self.animation_speed = self.ANIMATION_SPEED
        
        # Load all hero animations
        self._load_animations()
        
        # Set initial animation state
        self.current_animation = "idle_front"
        self.set_animation("idle_front")
        
        # Movement state
        self.touch_ground: bool = False
        self.is_jumping: bool = False
        self.current_jump: int = 0
        self.is_moving: bool = False
        self.facing_direction: str = "DOWN"  # UP, DOWN, LEFT, RIGHT
        
        # Z-axis movement tracking
        self.previous_z: float = z
        self.z_velocity: float = 0.0  # Positive = ascending, negative = descending
        
        # Interaction state
        self.is_grabbing: bool = False
        self.grabbed_entity: Optional['Entity'] = None
        
        # Collision detection
        self.bbox: BoundingBox = BoundingBox(self._world_pos, self.HEIGHT)
    
    def _load_animations(self) -> None:
        """Load all hero animation spritesheets and extract frames"""
        animation_config = [
            # (animation_name, file_path, frame_width, frame_height, num_frames)
            ("idle_back", "data/sprites/SpriteGfx000Anim000.png", 32, 48, 1),
            ("idle_front", "data/sprites/SpriteGfx000Anim001.png", 32, 48, 1),
            ("walk_back", "data/sprites/SpriteGfx000Anim002.png", 32, 48, 8),
            ("walk_front", "data/sprites/SpriteGfx000Anim003.png", 32, 48, 8),
            ("pickup_back", "data/sprites/SpriteGfx000Anim004.png", 32, 48, 3),
            ("pickup_front", "data/sprites/SpriteGfx000Anim005.png", 32, 48, 3),
            ("carry_walk_back", "data/sprites/SpriteGfx000Anim006.png", 32, 48, 8),
            ("carry_walk_front", "data/sprites/SpriteGfx000Anim007.png", 32, 48, 8),
            ("jump_back", "data/sprites/SpriteGfx000Anim008.png", 32, 48, 2),
            ("jump_front", "data/sprites/SpriteGfx000Anim009.png", 32, 48, 2),
            ("carry_jump_back", "data/sprites/SpriteGfx000Anim010.png", 32, 48, 2),
            ("carry_jump_front", "data/sprites/SpriteGfx000Anim011.png", 32, 48, 2),
        ]
        
        try:
            # Load each animation
            for anim_name, file_path, width, height, frames in animation_config:
                sheet = pygame.image.load(file_path).convert_alpha()
                self.animations[anim_name] = self.extract_frames(sheet, width, height, frames)
            
            # Create left/right animations as references (will be flipped during rendering)
            self.animations["idle_left"] = self.animations["idle_back"]
            self.animations["idle_right"] = self.animations["idle_back"]
            self.animations["walk_left"] = self.animations["walk_back"]
            self.animations["walk_right"] = self.animations["walk_front"]
            self.animations["jump_left"] = self.animations["jump_back"]
            self.animations["jump_right"] = self.animations["jump_front"]
            self.animations["carry_walk_left"] = self.animations["carry_walk_back"]
            self.animations["carry_walk_right"] = self.animations["carry_walk_front"]
            self.animations["carry_jump_left"] = self.animations["carry_jump_back"]
            self.animations["carry_jump_right"] = self.animations["carry_jump_front"]
            
            # Create carry idle animations using first frame of pickup animations
            self.animations["carry_idle_back"] = [self.animations["pickup_back"][0]]
            self.animations["carry_idle_front"] = [self.animations["pickup_front"][0]]
            self.animations["carry_idle_left"] = [self.animations["pickup_back"][0]]
            self.animations["carry_idle_right"] = [self.animations["pickup_back"][0]]
            
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load hero animation sprites: {e}")
            self._create_placeholder_animations()
    
    def _create_placeholder_animations(self) -> None:
        """Create placeholder animations when sprite files are missing"""
        placeholder = pygame.Surface((32, 48), pygame.SRCALPHA)
        placeholder.fill((255, 0, 255, 128))  # Magenta placeholder
        
        # Single frame animations
        for anim_name in ["idle_front", "idle_back", "idle_left", "idle_right",
                          "carry_idle_front", "carry_idle_back", "carry_idle_left", "carry_idle_right"]:
            self.animations[anim_name] = [placeholder.copy()]
        
        # Multi-frame walk animations
        for anim_name in ["walk_front", "walk_back", "walk_left", "walk_right",
                          "carry_walk_front", "carry_walk_back", "carry_walk_left", "carry_walk_right"]:
            self.animations[anim_name] = [placeholder.copy() for _ in range(8)]
        
        # Jump animations
        for anim_name in ["jump_front", "jump_back", "jump_left", "jump_right",
                          "carry_jump_front", "carry_jump_back", "carry_jump_left", "carry_jump_right"]:
            self.animations[anim_name] = [placeholder.copy() for _ in range(2)]
        
        # Pickup animations
        for anim_name in ["pickup_front", "pickup_back"]:
            self.animations[anim_name] = [placeholder.copy() for _ in range(3)]
    
    def update_z_velocity(self) -> None:
        """Calculate Z-axis velocity based on position change"""
        current_z = self._world_pos.z
        self.z_velocity = current_z - self.previous_z
        self.previous_z = current_z
    
    def is_ascending(self) -> bool:
        """Check if hero is moving upward in Z-axis
        
        Returns:
            True if ascending (positive Z velocity)
        """
        return self.z_velocity > 0
    
    def is_descending(self) -> bool:
        """Check if hero is moving downward in Z-axis
        
        Returns:
            True if descending (negative Z velocity)
        """
        return self.z_velocity < 0
    
    def is_airborne(self) -> bool:
        """Check if hero is in the air (jumping or falling)
        
        Returns:
            True if not touching ground
        """
        return not self.touch_ground
    
    def update_animation(self, is_moving: bool) -> None:
        """Update the current animation based on movement state and direction
        
        Args
            is_moving: Whether the hero is currently moving
        """
        self.is_moving = is_moving
        
        # Select and set appropriate animation
        animation_name = self._get_animation_name()
        self.set_animation(animation_name)
        
        # Update the frame index
        self._update_frame_index(is_moving)
        
        # Apply horizontal mirroring if needed
        self._apply_direction_mirroring()
    
    def _get_animation_name(self) -> str:
        """Determine which animation to play based on current state
        
        Returns:
            Name of the animation to play
        """
        # Determine animation prefix based on carrying state
        prefix = "carry_" if self.is_grabbing else ""
        
        # Priority: jumping (is_jumping) > airborne (falling) > walking > idle
        if self.is_jumping:
            state = "jump"
        elif self.is_airborne():
            state = "jump"
        elif self.is_moving:
            state = "walk"
        else:
            # Use carry_idle when carrying and stationary
            state = "idle"
        
        # Determine direction suffix
        direction_map = {
            "UP": "back",
            "DOWN": "front",
            "LEFT": "left",
            "RIGHT": "front",  # Uses front animation, flipped during rendering
        }
        
        direction = direction_map.get(self.facing_direction, "front")
        return f"{prefix}{state}_{direction}"

    def _update_frame_index(self, is_moving: bool) -> None:
        """Update the current frame index based on animation state
        
        Args:
            is_moving: Whether the hero is currently moving
        """
        if self.is_airborne() or self.is_jumping:
            # Jump animation: frame 0 = ascending, frame 1 = descending
            # During active jump (is_jumping=True), always show ascending frame
            # When falling (is_jumping=False), show descending frame
            if self.is_jumping or self.is_ascending():
                frame_index = 0  # Ascending frame
            else:
                frame_index = 1  # Descending/falling frame
            self.set_animation_frame(frame_index)
        else:
            # Walk/idle animations advance automatically
            should_advance = is_moving or len(self.animations[self.current_animation]) == 1
            self.update_animation_frame(advance=should_advance)

    def _apply_direction_mirroring(self) -> None:
        """Apply horizontal mirroring to the image based on facing direction"""
        if not self.current_animation or self.current_animation not in self.animations:
            return
        
        frames = self.animations[self.current_animation]
        if not frames or self.current_frame >= len(frames):
            return
        
        base_image = frames[self.current_frame]
        
        # Mirror horizontally for left and right directions
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
        # No update if there's no movement
        if dx == 0 and dy == 0:
            return
        
        # Prioritize the axis with larger absolute movement
        if abs(dx) > abs(dy):
            self.facing_direction = "LEFT" if dx < 0 else "RIGHT"
        else:
            self.facing_direction = "UP" if dy < 0 else "DOWN"
    
    def _update_screen_pos(self, heightmap_left_offset: int, heightmap_top_offset: int, 
                          camera_x: float, camera_y: float) -> None:
        """Update screen position based on world position and camera
        
        Overridden to apply Hero-specific isometric positioning
        
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
        
        # Calculate world-to-screen offset
        offset_x = (heightmap_left_offset - 8) * 16
        offset_y = (heightmap_top_offset - 8) * 16
        
        # Convert to isometric screen coordinates
        iso_x, iso_y = cartesian_to_iso(
            self._world_pos.x - offset_x, 
            self._world_pos.y - offset_y
        )
        
        # Apply hero sprite positioning (32 pixels tall)
        self._screen_pos.x = iso_x - camera_x
        self._screen_pos.y = iso_y - self._world_pos.z - camera_y + 32
    
    def grab_entity(self, entity: 'Entity') -> None:
        """Start grabbing an entity
        
        Args:
            entity: The entity to grab
        """
        self.is_grabbing = True
        self.grabbed_entity = entity
        # Force animation update to switch to carry animation
        self.update_animation(self.is_moving)
    
    def release_entity(self) -> None:
        """Release the currently grabbed entity"""
        self.is_grabbing = False
        self.grabbed_entity = None
        # Force animation update to switch back to regular animation
        self.update_animation(self.is_moving)
    
    def has_grabbed_entity(self) -> bool:
        """Check if hero is currently grabbing an entity
        
        Returns:
            True if an entity is grabbed, False otherwise
        """
        return self.is_grabbing and self.grabbed_entity is not None
    
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
        if not self.has_grabbed_entity():
            return
        
        # Position entity directly above hero (HEIGHT tiles higher in Z)
        hero_pos = self.get_world_pos()
        entity_z = hero_pos.z + (self.HEIGHT * tile_h)
        
        # Update entity world and screen position
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
        """String representation of the Hero for debugging
        
        Returns:
            Detailed string representation of hero state
        """
        return (
            f"Hero("
            f"pos={self._world_pos}, "
            f"facing={self.facing_direction}, "
            f"animation={self.current_animation}, "
            f"frame={self.current_frame}, "
            f"airborne={self.is_airborne()}, "
            f"z_vel={self.z_velocity:.2f}, "
            f"moving={self.is_moving}, "
            f"grabbing={self.is_grabbing}"
            f")"
        )