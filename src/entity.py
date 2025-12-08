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
    
    # Sprite mapping: entity_class -> (sprite filename, frame_width, frame_count)
    _sprite_map: ClassVar[Dict[str, Tuple[str, int, int]]] = {
        'Crate': ('data/sprites/SpriteGfx091Anim000.png', 32, 1),
        'Chest': ('data/sprites/SpriteGfx036Anim000.png', 32, 5),
        'Small Yellow Platform': ('data/sprites/SpriteGfx049Anim000.png', 32, 1),
        'Large Grey Ball': ('data/sprites/SpriteGfx045Anim000.png', 64, 1),
        'Raft': ('data/sprites/SpriteGfx092Anim000.png', 64, 1),
    }
    
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
    def _get_hitbox_from_yaml(cls, entity_id: int, sprite_id: int) -> Tuple[float, float, float]:
        """Get hitbox properties from YAML file based on sprite ID
        
        Args:
            entity_id: ID of the entity (for logging purposes)
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
    
    def __init__(self, data: Dict[str, Any]) -> None:
        """Initialize entity from TMX object data
        
        Args:
            data: Dictionary containing entity properties from TMX
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
        
        # Position (in tile coordinates from TMX)
        self.x: float = data.get('X', 0.0)
        self.y: float = data.get('Y', 0.0)
        self.z: float = data.get('Z', 0.0)
        
        # World position (will be calculated based on tile size)
        self.world_pos: Optional[Vector3] = None
        self._screen_pos: Vector2 = Vector2()
        
        # Physical properties (size in tiles, height in tiles, volume)
        # Load from sprite properties using the sprite_id from entity properties
        hitbox_props = self._get_hitbox_from_yaml(self.entity_id, self.sprite_id)
        print(f"Hitbox for {self.name} (Entity ID: {self.entity_id}, Sprite ID: {self.sprite_id}): {hitbox_props}")
        
        self.size: float = hitbox_props[0]  # Width and length in tiles
        self.height: float = hitbox_props[1]  # Height in tiles
        self.volume: float = hitbox_props[2]  # Volume
        
        # Height in tiles (entities are 1 tile tall by default, but can be overridden)
        self.HEIGHT: int = int(self.height)
        
        # Bounding box for collision detection (initialized after world_pos is set)
        self.bbox: Optional[BoundingBox] = None
        
        # Visual properties
        self.palette: int = data.get('Palette', 0)
        self.orientation: str = data.get('Orientation', 'NE')
        
        # Sprite/animation
        self.sprite_sheet: Optional[pygame.Surface] = None  # Full sprite sheet
        self.frames: List[pygame.Surface] = []  # Individual frames
        self.frame_width: int = 32  # Width of each frame
        self.frame_count: int = 1  # Number of frames
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
        """Load sprite for this entity class and extract individual frames"""
        sprite_info = self._sprite_map.get(self.name)
        
        if sprite_info:
            sprite_file, frame_width, frame_count = sprite_info
            self.frame_width = frame_width
            self.frame_count = frame_count
            
            # Check if already in cache
            if sprite_file not in Entity._sprite_cache:
                try:
                    loaded_sprite = pygame.image.load(sprite_file).convert_alpha()
                    Entity._sprite_cache[sprite_file] = loaded_sprite
                    print(f"Loaded sprite sheet for {self.name}: {sprite_file}")
                except (pygame.error, FileNotFoundError) as e:
                    print(f"Warning: Could not load sprite {sprite_file}: {e}")
                    # Mark sprite as missing instead of creating placeholder
                    self.sprite_missing = True
                    Entity._sprite_cache[sprite_file] = None
                    return
            
            # Get the sprite sheet from cache
            self.sprite_sheet = Entity._sprite_cache[sprite_file]
            
            # Check if sprite was actually loaded
            if self.sprite_sheet is None:
                self.sprite_missing = True
                return
            
            # Extract individual frames from the sprite sheet
            self._extract_frames()
            
        else:
            # No sprite mapping for this entity class - mark as missing
            print(f"Warning: No sprite mapping for entity: {self.name}")
            self.sprite_missing = True
    
    def _extract_frames(self) -> None:
        """Extract individual frames from the sprite sheet"""
        if self.sprite_sheet is None:
            return
        
        sprite_height = self.sprite_sheet.get_height()
        
        # Extract each frame
        for i in range(self.frame_count):
            x = i * self.frame_width
            frame = self.sprite_sheet.subsurface(
                pygame.Rect(x, 0, self.frame_width, sprite_height)
            )
            self.frames.append(frame)
        
        # Set initial frame
        if self.frames:
            self.image = self.frames[0]
    
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
    
    def set_world_pos(self, tile_h: int) -> None:
        """Calculate world position from tile coordinates
        
        Args:
            tile_h: Tile height in pixels
        """
        self.world_pos = Vector3(
            self.x * tile_h,
            self.y * tile_h,
            self.z * tile_h
        )
        # Initialize bounding box after world position is set
        # Use the entity's size property for the bounding box
        self.bbox = BoundingBox(self.world_pos, self.height, self.size)
    
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
        if self.world_pos is None:
            return
        
        offset_x: float = (heightmap_left_offset - 12 + 4) * tile_h
        offset_y: float = (heightmap_top_offset - 11 + 4) * tile_h
        
        iso_x: float
        iso_y: float
        iso_x, iso_y = cartesian_to_iso(
            self.world_pos.x - offset_x,
            self.world_pos.y - offset_y
        )
        
        ENTITY_HEIGHT: int = 32  # Adjust based on sprite
        
        self._screen_pos.x = iso_x - 16 - camera_x
        self._screen_pos.y = iso_y - self.world_pos.z + 12 - camera_y + ENTITY_HEIGHT
    
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
        if self.bbox is None:
            raise RuntimeError("Bounding box not initialized. Call set_world_pos() first.")
        return self.bbox.get_bounding_box(tile_h)
    
    def get_bbox_corners_world(self, tile_h: int) -> Tuple[Tuple[float, float], ...]:
        """Get the four corners of the entity's bounding box in world coordinates
        
        Args:
            tile_h: Tile height in pixels
            
        Returns:
            Tuple of 4 corner positions: (left, bottom, right, top)
            Each corner is (x, y) in world coordinates
        """
        if self.bbox is None:
            raise RuntimeError("Bounding box not initialized. Call set_world_pos() first.")
        return self.bbox.get_corners_world(tile_h)
    
    def get_bbox_corners_iso(self, tile_h: int, left_offset: int, top_offset: int, 
                              camera_x: float, camera_y: float) -> List[Tuple[float, float]]:
        """Get the four corners of the entity's bounding box in isometric screen coordinates
        
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
        if self.bbox is None:
            raise RuntimeError("Bounding box not initialized. Call set_world_pos() first.")
        return self.bbox.get_corners_iso(tile_h, left_offset, top_offset, camera_x, camera_y)
        
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
                f"sprite_id={self.sprite_id}, pos=({self.x}, {self.y}, {self.z}), "
                f"size={self.size}, height={self.height}, volume={self.volume}, "
                f"behaviour={self.behaviour}, solid={self.solid} visible={self.visible})")