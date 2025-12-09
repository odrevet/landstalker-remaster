from typing import Dict, Any, Optional, Tuple, List, ClassVar
import pygame
from pygame.math import Vector2, Vector3
from boundingbox import BoundingBox
from utils import cartesian_to_iso
import yaml
import os


class Entity:
    """Represents a game entity (NPC, chest, crate, etc.)"""
    
    # Class-level sprite cache - shared across all instances
    _sprite_cache: ClassVar[Dict[str, pygame.Surface]] = {}
    
    # Sprite properties cache - loaded from YAML files
    _sprite_properties_cache: ClassVar[Dict[int, Dict[str, Any]]] = {}
    
    # Entity properties cache - loaded from EntityXXXProperties.yaml files
    _entity_properties_cache: ClassVar[Dict[int, Dict[str, Any]]] = {}
    
    # Default hitbox values if YAML properties are not available
    _default_hitbox: ClassVar[Tuple[float, float, float]] = (1.0, 1.0, 1.0)
    
    @classmethod
    def _load_entity_properties(cls, entity_id: int) -> Optional[Dict[str, Any]]:
        """Load entity properties from EntityXXXProperties.yaml file
        
        Args:
            entity_id: The entity ID to load properties for
            
        Returns:
            Dictionary of entity properties or None if not found
        """
        # Check cache first
        if entity_id in cls._entity_properties_cache:
            return cls._entity_properties_cache[entity_id]
        
        # Construct YAML filename
        yaml_file = f"data/entities/Entity{entity_id:03d}Properties.yaml"
        
        if not os.path.exists(yaml_file):
            print(f"Warning: Entity properties file not found: {yaml_file}")
            cls._entity_properties_cache[entity_id] = None
            return None
        
        try:
            with open(yaml_file, 'r') as f:
                properties = yaml.safe_load(f)
                cls._entity_properties_cache[entity_id] = properties
                print(f"Loaded entity properties for ID {entity_id}: {properties.get('Name', 'Unknown')}")
                return properties
        except Exception as e:
            print(f"Error loading entity properties from {yaml_file}: {e}")
            cls._entity_properties_cache[entity_id] = None
            return None
    
    @classmethod
    def _load_sprite_properties(cls, sprite_id: int) -> Optional[Dict[str, Any]]:
        """Load sprite properties from YAML file
        
        Args:
            sprite_id: The sprite ID to load properties for
            
        Returns:
            Dictionary of sprite properties or None if not found
        """
        # Check cache first
        if sprite_id in cls._sprite_properties_cache:
            return cls._sprite_properties_cache[sprite_id]
        
        # Construct YAML filename
        yaml_file = f"data/sprites/Sprite{sprite_id:03d}Properties.yaml"
        
        if not os.path.exists(yaml_file):
            print(f"Warning: Sprite properties file not found: {yaml_file}")
            cls._sprite_properties_cache[sprite_id] = None
            return None
        
        try:
            with open(yaml_file, 'r') as f:
                properties = yaml.safe_load(f)
                cls._sprite_properties_cache[sprite_id] = properties
                print(f"Loaded sprite properties for ID {sprite_id}: {properties.get('Name', 'Unknown')}")
                return properties
        except Exception as e:
            print(f"Error loading sprite properties from {yaml_file}: {e}")
            cls._sprite_properties_cache[sprite_id] = None
            return None
    
    @classmethod
    def _get_sprite_info(cls, sprite_id: int) -> Optional[Tuple[str, int, int]]:
        """Get sprite file path, frame width, and frame count from sprite properties
        
        Args:
            sprite_id: The sprite ID to get info for
            
        Returns:
            Tuple of (sprite_file_path, frame_width, frame_count) or None if not found
        """
        sprite_props = cls._load_sprite_properties(sprite_id)
        if sprite_props is None:
            print(f"  _get_sprite_info: Could not load sprite properties for sprite ID {sprite_id}")
            return None
        
        # Get the label to construct the sprite file path
        label = sprite_props.get('Label')
        if label is None:
            print(f"  _get_sprite_info: No Label found in sprite properties for sprite ID {sprite_id}")
            return None
        
        # Construct sprite file path: data/sprites/SpriteGfxXXXAnim000.png
        sprite_file = f"data/sprites/{label}Anim000.png"
        
        # Get hitbox to determine frame width
        hitbox = sprite_props.get('Hitbox', {})
        width = hitbox.get('Width', 1.0)
        
        # Calculate frame width in pixels (assuming 16 pixels per tile unit)
        # Round to nearest power of 2 or common sprite size (32, 64, 128, etc.)
        frame_width_pixels = int(width * 32)
        print(f"  _get_sprite_info: Hitbox width={width}, calculated pixels={frame_width_pixels}")
        if frame_width_pixels <= 32:
            frame_width = 32
        elif frame_width_pixels <= 64:
            frame_width = 64
        elif frame_width_pixels <= 128:
            frame_width = 128
        else:
            frame_width = 256
        
        # Get frame count from animation properties
        animation = sprite_props.get('Animation', {})
        idle_frame_count = animation.get('IdleAnimationFrameCount', 0)
        walk_frame_count = animation.get('WalkCycleFrameCount', 0)
        
        # Use the maximum frame count available, default to 1 if both are 0
        frame_count = max(idle_frame_count, walk_frame_count)
        if frame_count == 0:
            frame_count = 1
            print(f"  _get_sprite_info: No animation frames specified, defaulting to 1")
        
        print(f"  _get_sprite_info: label={label}, frame_width={frame_width}, frame_count={frame_count}")
        return (sprite_file, frame_width, frame_count)
    
    @classmethod
    def _get_hitbox_from_yaml(cls, sprite_id: int) -> Tuple[float, float, float]:
        """Get hitbox properties from YAML file based on sprite ID
        
        Args:
            sprite_id: ID of the sprite to load hitbox from
            
        Returns:
            Tuple of (width, height, volume), defaults to (1.0, 1.0, 1.0) if not found
        """
        properties = cls._load_sprite_properties(sprite_id)
        if properties is None:
            return cls._default_hitbox
        
        hitbox = properties.get('Hitbox')
        if hitbox is None:
            return cls._default_hitbox
        
        width = hitbox.get('Width', 1.0)
        height = hitbox.get('Height', 1.0)
        volume = hitbox.get('Volume', 1.0)
        
        return (width, height, volume)
    
    def __init__(self, data: Dict[str, Any], tile_h: int) -> None:
        """Initialize entity from TMX object data
        
        Args:
            data: Dictionary containing entity properties from TMX
            tile_h: Tile height in pixels for world position calculation
        """
        # Basic identification
        self.entity_id: int = data.get('Type', 0)  # Entity ID from TMX
        self.entity_class: str = data.get('class', 'Entity')
        
        # Load entity properties from EntityXXXProperties.yaml
        entity_props = self._load_entity_properties(self.entity_id)
        
        # Set name from entity properties or fall back to TMX name
        if entity_props:
            self.name: str = entity_props.get('Name', data.get('name', 'Unknown'))
            self.sprite_id: int = entity_props.get('SpriteID', 0)
            self.low_palette: int = entity_props.get('LowPalette', 0)
            self.high_palette: int = entity_props.get('HighPalette', 0)
            self.talk_sound_fx: int = entity_props.get('TalkSoundFX', 0)
            self.is_item: bool = entity_props.get('IsItem', False)
            self.is_enemy: bool = entity_props.get('IsEnemy', False)
            
            # Load enemy properties if this is an enemy
            if self.is_enemy and 'Enemy' in entity_props:
                enemy_data = entity_props['Enemy']
                self.health: int = enemy_data.get('Health', 0)
                self.defence: int = enemy_data.get('Defence', 0)
                self.attack: int = enemy_data.get('Attack', 0)
                self.gold_drop: int = enemy_data.get('GoldDrop', 0)
                self.item_drop: int = enemy_data.get('ItemDrop', 0)
                self.drop_probability: int = enemy_data.get('DropProbability', 0)
        else:
            # Fall back to TMX data if entity properties not found
            self.name: str = data.get('name', 'Unknown')
            self.sprite_id: int = 0
            self.low_palette: int = 0
            self.high_palette: int = 0
            self.talk_sound_fx: int = 0
            self.is_item: bool = False
            self.is_enemy: bool = False
        
        self.type: int = self.entity_id  # Keep for backward compatibility
        
        # Initialize world position directly from TMX coordinates
        x: float = data.get('X', 0.0)
        y: float = data.get('Y', 0.0)
        z: float = data.get('Z', 0.0)
        self.world_pos: Vector3 = Vector3(x * tile_h, y * tile_h, z * tile_h)
        
        # Screen position (calculated later)
        self._screen_pos: Vector2 = Vector2()
        
        # Load hitbox from sprite properties using the sprite_id from entity properties
        hitbox_props = self._get_hitbox_from_yaml(self.sprite_id)
        print(f"Hitbox for {self.name} (Entity ID: {self.entity_id}, Sprite ID: {self.sprite_id}): {hitbox_props}")
        
        # Store hitbox as instance attribute
        self.hitbox: Tuple[float, float, float] = hitbox_props
        self.size: float = hitbox_props[0]  # Width and length in tiles
        self.height: float = hitbox_props[1]  # Height in tiles
        self.volume: float = hitbox_props[2]  # Volume
        
        # Height in tiles (entities are 1 tile tall by default, but can be overridden)
        self.HEIGHT: int = int(self.height)
        
        # Initialize bounding box for collision detection
        bbox_pos = self.world_pos.copy()
        bbox_pos.x -= 12 * 16
        bbox_pos.y -= 12 * 16
        self.bbox: BoundingBox = BoundingBox(bbox_pos, self.height, self.size)
        
        # Visual properties
        self.palette: int = data.get('Palette', 0)
        self.orientation: str = data.get('Orientation', 'NE')
        
        # Sprite/animation
        self.sprite_sheet: Optional[pygame.Surface] = None  # Full sprite sheet
        self.frames: List[pygame.Surface] = []  # Individual frames
        self.frame_width: int = 32  # Width of each frame (will be set by sprite properties)
        self.frame_count: int = 1  # Number of frames (will be set by sprite properties)
        self.current_frame: int = 0
        self.image: Optional[pygame.Surface] = None  # Current frame to display
        self.sprite_missing: bool = False  # Flag to indicate missing sprite
        
        # Animation timing
        self.animation_speed: float = 0.1  # Seconds per frame
        self.animation_timer: float = 0.0
        
        # Behavior properties
        self.behaviour: int = data.get('Behaviour', 0)
        self.dialogue: int = data.get('Dialogue', 0)
        self.speed: int = data.get('Speed', 0)
        
        # Flags
        self.hostile: bool = data.get('Hostile', False)
        self.no_rotate: bool = data.get('NoRotate', False)
        self.no_pickup: bool = data.get('NoPickup', False)
        self.has_dialogue: bool = data.get('HasDialogue', False)
        self.visible: bool = data.get('Visible', True)
        self.solid: bool = data.get('Solid', True)
        self.gravity: bool = data.get('Gravity', True)
        self.friction: bool = data.get('Friction', True)
        self.reserved: bool = data.get('Reserved', False)
        
        # Tile properties (for tile copying)
        self.tile_copy: bool = data.get('TileCopy', False)
        self.tile_source: int = data.get('TileSource', 0)
        
        # Load sprite for this entity
        self._load_sprite()
    
    def _load_sprite(self) -> None:
        """Load sprite for this entity using sprite ID from entity properties"""
        print(f"Loading sprite for {self.name} (Entity ID: {self.entity_id}, Sprite ID: {self.sprite_id})")
        
        # Get sprite information from sprite properties
        sprite_info = self._get_sprite_info(self.sprite_id)
        
        if sprite_info is None:
            print(f"Warning: Could not get sprite info for sprite ID {self.sprite_id} (entity: {self.name})")
            self.sprite_missing = True
            return
        
        sprite_file, frame_width, frame_count = sprite_info
        self.frame_width = frame_width
        self.frame_count = frame_count
        print(f"  Sprite info: file={sprite_file}, frame_width={frame_width}, frame_count={frame_count}")
        
        # Check if already in cache
        if sprite_file not in Entity._sprite_cache:
            try:
                loaded_sprite = pygame.image.load(sprite_file).convert_alpha()
                Entity._sprite_cache[sprite_file] = loaded_sprite
                print(f"  Loaded sprite sheet: {sprite_file}")
            except (pygame.error, FileNotFoundError) as e:
                print(f"  ERROR: Could not load sprite {sprite_file}: {e}")
                # Mark sprite as missing instead of creating placeholder
                self.sprite_missing = True
                Entity._sprite_cache[sprite_file] = None
                return
        
        # Get the sprite sheet from cache
        self.sprite_sheet = Entity._sprite_cache[sprite_file]
        
        # Check if sprite was actually loaded
        if self.sprite_sheet is None:
            print(f"  ERROR: Sprite sheet is None in cache for {sprite_file}")
            self.sprite_missing = True
            return
        
        print(f"  Extracting {frame_count} frames from sprite sheet...")
        # Extract individual frames from the sprite sheet
        self._extract_frames()
        print(f"  Extraction complete. self.image = {self.image}, frames count = {len(self.frames)}")
    
    def _extract_frames(self) -> None:
        """Extract individual frames from the sprite sheet"""
        if self.sprite_sheet is None:
            print(f"  ERROR in _extract_frames: sprite_sheet is None!")
            return
        
        sprite_height = self.sprite_sheet.get_height()
        sprite_width = self.sprite_sheet.get_width()
        print(f"  Sprite sheet dimensions: {sprite_width}x{sprite_height}")
        print(f"  Extracting {self.frame_count} frames of width {self.frame_width}")
        
        # Extract each frame
        for i in range(self.frame_count):
            x = i * self.frame_width
            if x + self.frame_width > sprite_width:
                print(f"  WARNING: Frame {i} extends beyond sprite sheet! x={x}, frame_width={self.frame_width}, sheet_width={sprite_width}")
                break
            frame = self.sprite_sheet.subsurface(
                pygame.Rect(x, 0, self.frame_width, sprite_height)
            )
            self.frames.append(frame)
            print(f"  Extracted frame {i}: {frame}")
        
        # Set initial frame
        if self.frames:
            self.image = self.frames[0]
            print(f"  Set initial image to frame 0: {self.image}")
        else:
            print(f"  ERROR: No frames were extracted!")
    
    def update(self, dt: float) -> None:
        """Update entity animation
        
        Args:
            dt: Delta time in seconds
        """
        if len(self.frames) > 1:
            self.animation_timer += dt
            
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0.0
                self.current_frame = (self.current_frame + 1) % len(self.frames)
                self.image = self.frames[self.current_frame]
    
    def set_frame(self, frame_index: int) -> None:
        """Set a specific frame manually
        
        Args:
            frame_index: Index of the frame to display
        """
        if 0 <= frame_index < len(self.frames):
            self.current_frame = frame_index
            self.image = self.frames[frame_index]
    
    def update_screen_pos(self, heightmap_left_offset: int, heightmap_top_offset: int,
                        camera_x: float, camera_y: float, tile_h: int) -> None:
        """Update screen position based on world position and camera
        Args:
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
            tile_h: Tile height in pixels
        """
        offset_x: float = heightmap_left_offset * tile_h
        offset_y: float = heightmap_top_offset * tile_h
        
        # Convert world position to isometric coordinates
        iso_x, iso_y = cartesian_to_iso(
            self.world_pos.x - offset_x,
            self.world_pos.y - offset_y
        )
        
        # Calculate entity height offset
        ENTITY_HEIGHT: int = (self.height) * 16
        
        # Update screen position with camera offset
        # The Z coordinate should be SUBTRACTED from iso_y to move entities up when they're higher
        self._screen_pos.x = iso_x - camera_x
        self._screen_pos.y = iso_y - self.world_pos.z - ENTITY_HEIGHT - camera_y - 8
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the entity on the surface
        
        Args:
            surface: Pygame surface to draw on
        """
        # Only draw sprite if it exists and is visible
        if self.image and self.visible and not self.sprite_missing:
            surface.blit(self.image, self._screen_pos)
    
    def get_bounding_box(self, tile_h: int) -> Tuple[float, float, float, float]:
        """Get entity's bounding box in world coordinates with margin applied
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of (x, y, width, height) in world coordinates
        """
        return self.bbox.get_bounding_box(tile_h)
    
    def get_bbox_corners_world(self, tile_h: int) -> Tuple[Tuple[float, float], ...]:
        """Get the four corners of the entity's bounding box in world coordinates
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of 4 corner positions: (left, bottom, right, top)
            Each corner is (x, y) in world coordinates
        """
        return self.bbox.get_corners_world(tile_h)

    def set_world_pos(self, x: float, y: float, z: float, 
                     heightmap_left_offset: int, heightmap_top_offset: int, 
                     camera_x: float, camera_y: float) -> None:
        """Set the entity's world position and update screen position
        
        Args:
            x, y, z: World coordinates
            heightmap_left_offset: Heightmap left offset
            heightmap_top_offset: Heightmap top offset
            camera_x: Camera X position
            camera_y: Camera Y position
        """
        self.world_pos.x = x
        self.world_pos.y = y
        self.world_pos.z = z
        self.update_screen_pos(heightmap_left_offset, heightmap_top_offset, camera_x, camera_y, 16)

    def is_crate(self) -> bool:
        """Check if entity is a crate"""
        return self.entity_class == 'Crate'
    
    def is_chest(self) -> bool:
        """Check if entity is a chest"""
        return self.entity_class == 'Chest'
    
    def is_npc(self) -> bool:
        """Check if entity is an NPC"""
        return self.entity_class == 'NPC'
    
    def is_raft(self) -> bool:
        """Check if entity is a raft"""
        return self.name == 'Raft'
    
    def __repr__(self) -> str:
        return (f"Entity(name='{self.name}', id={self.entity_id}, class='{self.entity_class}', "
                f"sprite_id={self.sprite_id}, world_pos={self.world_pos}, "
                f"hitbox={self.hitbox}, behaviour={self.behaviour}, "
                f"solid={self.solid}, visible={self.visible})")