from typing import Dict, Any, Optional, Tuple, List, ClassVar
import pygame
from pygame.math import Vector2, Vector3
from boundingbox import BoundingBox
from utils import cartesian_to_iso
from drawable import Drawable
import yaml
import os


class Entity(Drawable):
    """Represents a game entity (NPC, chest, crate, etc.)"""
    
    # Class-level sprite cache - shared across all instances
    _sprite_cache: ClassVar[Dict[str, pygame.Surface]] = {}
    
    # Sprite properties cache - loaded from YAML files
    _sprite_properties_cache: ClassVar[Dict[int, Dict[str, Any]]] = {}
    
    # Entity properties cache - loaded from EntityXXXProperties.yaml files
    _entity_properties_cache: ClassVar[Dict[int, Dict[str, Any]]] = {}
    
    # Animation YAML cache - loaded from SpriteGfxXXXAnimXX.yaml files
    _animation_yaml_cache: ClassVar[Dict[str, Dict[str, Any]]] = {}
    
    # Default hitbox values if YAML properties are not available
    _default_hitbox: ClassVar[Tuple[float, float, float]] = (1.0, 1.0, 1.0)
    
    # Specific item frame mappings (entity_id -> (frame_index, animation_number))
    # Items always use 8 frames (indices 0-7) from the sprite sheet
    _item_frame_map: ClassVar[Dict[int, Tuple[int, str]]] = {
        230: (6, "04"),  # Island Map - frame 6, animation 04
        229: (5, "04"),  # Hotel Register - frame 5, animation 04
    }
    
    @classmethod
    def _load_animation_yaml(cls, label: str, anim_num: str) -> Optional[Dict[str, Any]]:
        """Load animation YAML file for frame and subsprite information
        
        Args:
            label: The sprite label (e.g., "SpriteGfx000")
            anim_num: The animation number (e.g., "00")
            
        Returns:
            Dictionary containing complete animation data including frames and subsprites, or None if not found
        """
        yaml_key = f"{label}Anim{anim_num}"
        
        # Check cache first
        if yaml_key in cls._animation_yaml_cache:
            return cls._animation_yaml_cache[yaml_key]
        
        # Construct YAML filename
        yaml_file = f"data/sprites/{yaml_key}.yaml"
        
        if not os.path.exists(yaml_file):
            print(f"Warning: Animation YAML file not found: {yaml_file}")
            cls._animation_yaml_cache[yaml_key] = None
            return None
        
        try:
            with open(yaml_file, 'r') as f:
                anim_data = yaml.safe_load(f)
                cls._animation_yaml_cache[yaml_key] = anim_data
                print(f"Loaded animation YAML: {yaml_file}")
                if anim_data:
                    print(f"  Animation data keys: {anim_data.keys()}")
                    if 'frames' in anim_data:
                        print(f"  Number of frames: {len(anim_data['frames'])}")
                return anim_data
        except Exception as e:
            print(f"Error loading animation YAML from {yaml_file}: {e}")
            cls._animation_yaml_cache[yaml_key] = None
            return None
    
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
    
    def _get_sprite_info(self, sprite_id: int) -> Optional[Tuple[str, int, int, str]]:
        """Get sprite file path, frame width, frame count, and label from sprite properties
        
        Args:
            sprite_id: The sprite ID to get info for
            
        Returns:
            Tuple of (sprite_file_path, frame_width, frame_count, label) or None if not found
        """
        sprite_props = self._load_sprite_properties(sprite_id)
        if sprite_props is None:
            print(f"  _get_sprite_info: Could not load sprite properties for sprite ID {sprite_id}")
            return None
        
        # Get the label to construct the sprite file path
        label = sprite_props.get('Label')
        if label is None:
            print(f"  _get_sprite_info: No Label found in sprite properties for sprite ID {sprite_id}")
            return None
        
        # Check if this entity is an item with specific animation mapping
        if self.entity_id in self._item_frame_map:
            # Items use their specific animation number
            _, anim_num = self._item_frame_map[self.entity_id]
            print(f"  _get_sprite_info: Entity is a mapped item, using animation {anim_num}")
        else:
            # Determine animation number based on orientation
            # NW and NE use Anim00, SE and SW use Anim01
            anim_num = "00"
            if self.orientation in ["SE", "SW"]:
                anim_num = "01"
            print(f"  _get_sprite_info: Using animation {anim_num} for orientation {self.orientation}")
        
        # Construct sprite file path: data/sprites/SpriteGfxXXXAnimXXX.png
        # Note: PNG files use 3-digit animation numbers, YAML files use 2-digit
        sprite_file = f"data/sprites/{label}Anim{anim_num.zfill(3)}.png"
        
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
        
        # Check if this entity is an item with specific frame mapping
        if self.entity_id in self._item_frame_map:
            # Items always have 8 frames (indices 0-7)
            frame_count = 8
            print(f"  _get_sprite_info: Entity is a mapped item, hardcoding frame_count to 8")
        else:
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
        return (sprite_file, frame_width, frame_count, label)
    
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
        # Initialize world position from TMX coordinates
        x: float = data.get('X', 0.0)
        y: float = data.get('Y', 0.0)
        z: float = data.get('Z', 0.0)

        # Call parent constructor with world position
        super().__init__(x, y, z)
        
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
        self.bbox: BoundingBox = BoundingBox(self._world_pos, self.height, self.size)
        
        # Visual properties
        self.palette: int = data.get('Palette', 0)
        self.orientation: str = data.get('Orientation', 'NE')

        # Sprite/animation (using base class animation support)
        self.frame_width: int = 32  # Width of each frame (will be set by sprite properties)
        self.frame_count: int = 1  # Number of frames (will be set by sprite properties)
        self.sprite_missing: bool = False  # Flag to indicate missing sprite
        self.fixed_frame_index: Optional[int] = None  # For items that use a specific frame
        
        # Complete animation YAML data for screen position calculations
        self.animation_yaml: Optional[Dict[str, Any]] = None  # Full animation YAML data
        self.animation_label: Optional[str] = None  # Sprite label (e.g., "SpriteGfx000")
        self.animation_num: Optional[str] = None  # Animation number (e.g., "00")
        
        # Animation timing (Entity-specific speed)
        self.animation_speed = 0.1  # Seconds per frame
        
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
        
        # Check if this is an item with a specific frame mapping (by entity_id)
        if self.entity_id in self._item_frame_map:
            self.fixed_frame_index, _ = self._item_frame_map[self.entity_id]
            print(f"  Item entity {self.entity_id} ('{self.name}') uses fixed frame index: {self.fixed_frame_index}")
        
        # Get sprite information from sprite properties
        sprite_info = self._get_sprite_info(self.sprite_id)
        
        if sprite_info is None:
            print(f"Warning: Could not get sprite info for sprite ID {self.sprite_id} (entity: {self.name})")
            self.sprite_missing = True
            return
        
        sprite_file, frame_width, frame_count, label = sprite_info
        self.frame_width = frame_width
        self.frame_count = frame_count
        print(f"  Sprite info: file={sprite_file}, frame_width={frame_width}, frame_count={frame_count}")
        
        # Store animation label and number for later use
        self.animation_label = label
        
        # Determine animation number for loading the animation YAML
        if self.entity_id in self._item_frame_map:
            _, anim_num = self._item_frame_map[self.entity_id]
            self.animation_num = anim_num
        else:
            self.animation_num = "00" if self.orientation in ["NW", "NE"] else "01"
        
        # Load complete animation YAML to get frame and subsprite data
        self.animation_yaml = self._load_animation_yaml(label, self.animation_num)
        if self.animation_yaml:
            print(f"  Loaded animation YAML for {label}Anim{self.animation_num}")
            if 'frames' in self.animation_yaml:
                print(f"  Animation has {len(self.animation_yaml['frames'])} frame entries")
        
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
        
        # Extract frames using base class method
        sprite_height = self.sprite_sheet.get_height()
        self.frames = self.extract_frames(self.sprite_sheet, frame_width, sprite_height, frame_count)
        
        # Store frames in animation dictionary (using "idle" as default animation)
        self.animations["idle"] = self.frames
        
        # Set initial image based on whether this item has a fixed frame
        if self.frames:
            self.current_animation = "idle"
            
            # Use fixed frame index for specific items, otherwise use frame 0
            if self.fixed_frame_index is not None and self.fixed_frame_index < len(self.frames):
                self.image = self.frames[self.fixed_frame_index]
                self.current_frame = self.fixed_frame_index
                print(f"  Set initial image to fixed frame {self.fixed_frame_index}: {self.image}")
            else:
                if self.fixed_frame_index is not None and self.fixed_frame_index >= len(self.frames):
                    print(f"  WARNING: Fixed frame index {self.fixed_frame_index} is out of range (only {len(self.frames)} frames), using frame 0")
                self.image = self.frames[0]
                print(f"  Set initial image to frame 0: {self.image}")
        else:
            print(f"  ERROR: No frames were extracted!")
    
    def update(self, dt: float) -> None:
        """Update entity animation
        
        Args:
            dt: Delta time in seconds
        """
        # Only animate if this entity doesn't have a fixed frame
        if self.fixed_frame_index is None and len(self.frames) > 1:
            self.update_animation_frame(advance=True)
    
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
                f"sprite_id={self.sprite_id}, world_pos={self._world_pos}, "
                f"hitbox={self.hitbox}, behaviour={self.behaviour}, "
                f"solid={self.solid}, visible={self.visible})")