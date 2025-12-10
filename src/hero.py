import pygame
from pygame.math import Vector2, Vector3
from typing import Tuple, List, Optional, Dict
from utils import cartesian_to_iso
from boundingbox import BoundingBox, MARGIN
from entity import Entity


class Hero:
    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        super().__init__()
        
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
        
        self._world_pos: Vector3 = Vector3(x, y, z)
        self._screen_pos: Vector2 = Vector2()
        self.HEIGHT: int = 2   # height in tiles
        self.touch_ground: bool = False
        self.is_jumping: bool = False
        self.current_jump: int = 0
        self.is_grabbing: bool = False
        self.grabbed_entity: Optional[Entity] = None
        self.facing_direction: str = "DOWN"  # Can be: "UP", "DOWN", "LEFT", "RIGHT"
        
        # Movement state
        self.is_moving: bool = False

        # Bounding box for collision detection
        bbox_vector = self._world_pos.copy()
        bbox_vector.x += 12 * 16
        bbox_vector.y += 12 * 16
        self.bbox: BoundingBox = BoundingBox(bbox_vector, self.HEIGHT)
        
        # Cache for update_screen_pos parameters
        self._heightmap_left_offset: int = 0
        self._heightmap_top_offset: int = 0
        self._camera_x: float = 0
        self._camera_y: float = 0
    
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
            
            # For left/right, we can use back animation (or add side animations later)
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
            self.animations["idle_front"] = [placeholder]
            self.animations["idle_back"] = [placeholder]
            self.animations["walk_front"] = [placeholder] * 8
            self.animations["walk_back"] = [placeholder] * 8
            self.animations["jump_front"] = [placeholder] * 2
            self.animations["jump_back"] = [placeholder] * 2
            self.animations["idle_left"] = [placeholder]
            self.animations["idle_right"] = [placeholder]
            self.animations["walk_left"] = [placeholder] * 8
            self.animations["walk_right"] = [placeholder] * 8
            self.animations["jump_left"] = [placeholder] * 2
            self.animations["jump_right"] = [placeholder] * 2
    
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
        
        # Determine which animation to play
        # Priority: jumping > moving > idle
        if self.is_jumping:
            # Use jump animations when jumping
            if self.facing_direction == "UP":
                new_animation = "jump_back"
            elif self.facing_direction == "DOWN" or self.facing_direction == "RIGHT":
                new_animation = "jump_front"
            elif self.facing_direction == "LEFT":
                new_animation = "jump_left"
        elif is_moving:
            if self.facing_direction == "UP":
                new_animation = "walk_back"
            elif self.facing_direction == "DOWN" or self.facing_direction == "RIGHT":
                new_animation = "walk_front"
            elif self.facing_direction == "LEFT":
                new_animation = "walk_left"
        else:
            if self.facing_direction == "UP":
                new_animation = "idle_back"
            elif self.facing_direction == "DOWN" or self.facing_direction == "RIGHT":
                new_animation = "idle_front"
            elif self.facing_direction == "LEFT":
                new_animation = "idle_left"
        
        # Reset frame if animation changed
        if new_animation != self.current_animation:
            self.current_animation = new_animation
            self.current_frame = 0
            self.animation_timer = 0.0
        
        # Update animation frame
        if self.is_jumping:
            # For jump: frame 0 = ascending, frame 1 = descending
            # Use current_jump to determine which frame
            # Assuming HERO_MAX_JUMP is available (you may need to pass it or import it)
            jump_peak = 12  # Half of HERO_MAX_JUMP (24 / 2)
            if self.current_jump < jump_peak:
                self.current_frame = 0  # Ascending - first frame
            else:
                self.current_frame = 1  # Descending - second frame
        elif is_moving or len(self.animations[self.current_animation]) == 1:
            # For walk animations, use timer
            self.animation_timer += self.animation_speed
            if self.animation_timer >= 1.0:
                self.animation_timer = 0.0
                self.current_frame = (self.current_frame + 1) % len(self.animations[self.current_animation])
        
        # Update current image
        base_image = self.animations[self.current_animation][self.current_frame]
        
        # Mirror image when facing left or right
        if self.facing_direction == "LEFT" or self.facing_direction == "RIGHT":
            self.image = pygame.transform.flip(base_image, True, False)
        else:
            self.image = base_image
    
    def update_facing_direction(self, dx: float, dy: float) -> None:
        """Update hero's facing direction based on movement delta
        
        Args:
            dx: Change in X position
            dy: Change in Y position
        """
        # Update facing based on actual movement direction
        # Priority: favor the axis with larger movement
        if abs(dx) > abs(dy):
            if dx < 0:
                self.facing_direction = "LEFT"
            elif dx > 0:
                self.facing_direction = "RIGHT"
        else:
            if dy < 0:
                self.facing_direction = "UP"
            elif dy > 0:
                self.facing_direction = "DOWN"
    
    def get_world_pos(self) -> Vector3:
        """Get the hero's world position"""
        return self._world_pos
    
    def get_bounding_box(self, tile_h: int) -> Tuple[float, float, float, float]:
        """Get hero's bounding box in world coordinates with margin applied
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of (x, y, width, height) in world coordinates
        """
        x = self._world_pos.x + MARGIN
        y = self._world_pos.y + MARGIN
        width = tile_h - (MARGIN * 2)
        height = tile_h - (MARGIN * 2)
        return (x, y, width, height)
    
    def get_bbox_corners_world(self, tile_h: int) -> Tuple[Tuple[float, float], ...]:
        """Get the four corners of the hero's bounding box in world coordinates
        
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
        
    def set_world_pos(self, x: float, y: float, z: float, 
                     heightmap_left_offset: int, heightmap_top_offset: int, 
                     camera_x: float, camera_y: float) -> None:
        """Set the hero's world position and update screen position
        
        Args:
            x, y, z: World coordinates
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        self._world_pos.x = x
        self._world_pos.y = y
        self._world_pos.z = z
        self._update_screen_pos(heightmap_left_offset, heightmap_top_offset, camera_x, camera_y)

        self.bbox.world_pos = self._world_pos
    
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
        """Update screen position based on world position and camera (private)"""
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
        HERO_HEIGHT: int = 32
        
        self._screen_pos.x = iso_x - 16 - camera_x
        self._screen_pos.y = iso_y - self._world_pos.z + 12 - camera_y + HERO_HEIGHT
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the hero on the surface"""
        surface.blit(self.image, self._screen_pos)

    def grab_entity(self, entity: Entity) -> None:
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
        if not self.is_grabbing or self.grabbed_entity is None:
            return
        
        # Position entity directly above hero (1 tile higher in Z)
        hero_pos = self.get_world_pos()
        entity_z = hero_pos.z + (self.HEIGHT * tile_h)
        self.grabbed_entity.world_pos = Vector3(hero_pos.x, hero_pos.y, entity_z)
        
        # Update entity's bounding box
        if self.grabbed_entity.bbox:
            self.grabbed_entity.bbox.update_position(self.grabbed_entity.world_pos)