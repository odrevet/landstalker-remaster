import pygame
from typing import List, Tuple, Dict, Any, Optional

from pytmx.util_pygame import load_pygame
from pygame.math import Vector2

from hero import Hero
from utils import cartesian_to_iso, iso_to_cartesian
from warp import Warp
from entity import Entity
from heightmap import Heightmap

DRAWING_HEIGHT: int = 224
DRAWING_WIDTH: int = 320

class Tile:
    __slots__ = ('image', 'has_priority', 'is_hflipped', 'is_vflipped', 'offset')
    
    def __init__(self, offset: Tuple[int, int]) -> None:
        self.image: Optional[pygame.Surface] = None
        self.has_priority: bool = False
        self.is_hflipped: bool = False
        self.is_vflipped: bool = False
        self.offset: Tuple[int, int] = offset

    def draw(self, surface: pygame.Surface, x: float, y: float) -> None:
        surface.blit(self.image, (x + self.offset[0], y + self.offset[1]))


class Blockset:
    __slots__ = ('tiles', 'grid_pos', 'screen_pos', 'gid')
    
    def __init__(self) -> None:
        self.tiles: List[Tile] = []
        self.grid_pos: Optional[Tuple[float, float]] = None
        self.screen_pos: Optional[Tuple[float, float]] = None
        self.gid: Optional[int] = None

    def draw(self, surface: pygame.Surface, layer_offset_h: float, 
             camera_x: float, camera_y: float) -> None:
        x = self.screen_pos[0] - camera_x + layer_offset_h
        y = self.screen_pos[1] - camera_y
        
        # Early rejection with expanded bounds check
        if x + 16 <= 0 or y <= 0 or x >= DRAWING_WIDTH or y >= DRAWING_HEIGHT:
            return
            
        for tile in self.tiles:
            tile.draw(surface, x, y)


class Layer:
    __slots__ = ('data', 'blocksets', 'offset_h')
    
    def __init__(self) -> None:
        self.data: Optional[TiledTileLayer] = None
        self.blocksets: List[Blockset] = []
        self.offset_h: float = 0.0

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float) -> None:
        # Cache offset to avoid repeated attribute lookups
        offset_h = self.offset_h
        
        # Only draw blocksets that could be visible
        for blockset in self.blocksets:
            blockset.draw(surface, offset_h, camera_x, camera_y)


class Room:
    def __init__(self) -> None:
        self.data: Optional[TiledMap] = None
        self.background_layer: Optional[Layer] = None
        self.foreground_layer: Optional[Layer] = None
        self.room_number: Optional[int] = None
        self.warps: List[Warp] = []
        self.entities: List[Entity] = []
        self.heightmap: Heightmap = Heightmap()
        self.room_properties: Dict[str, Any] = {}
        
        # Cache for tile processing
        self._tile_cache: Dict[int, List[pygame.Surface]] = {}

    def load(self, room_number: int) -> None:
        tmx_filename: str = f"data/rooms/Room{room_number:03d}.tmx"
        print(f"loading {tmx_filename}")
        self.data = load_pygame(tmx_filename)

        self.background_layer = Layer()
        self.background_layer.data = self.data.get_layer_by_name("Background")
        self.background_layer.offset_h = self.background_layer.data.offsetx
        self.populate_layer(self.background_layer)
        
        self.foreground_layer = Layer()
        self.foreground_layer.data = self.data.get_layer_by_name("Foreground")
        self.foreground_layer.offset_h = self.foreground_layer.data.offsetx
        self.populate_layer(self.foreground_layer)
        
        self.room_number = room_number

        # Load room properties
        self.room_properties = {}
        if hasattr(self.data, "properties") and self.data.properties:
            self.room_properties.update(self.data.properties)

        print("Room properties loaded:")
        for k, v in self.room_properties.items():
            print(f"  {k}: {v}")

        # Load heightmap from properties
        self.heightmap.load_from_properties(self.room_properties)

        # Load warps as Warp objects
        self.warps = []
        warp_layer = self.data.get_layer_by_name('Warps')
        if warp_layer:
            for warp in warp_layer:
                warp_data: Dict[str, Any] = {
                    'room1': int(warp.properties['room1']),
                    'room2': int(warp.properties['room2']),
                    'x': int(warp.x),
                    'y': int(warp.y),
                    'x2': int(warp.properties['x2']),
                    'y2': int(warp.properties['y2']),
                    'width': warp.width,
                    'height': warp.height,
                    'type': warp.properties['warpType']
                }
                self.warps.append(Warp(warp_data))
        
        # Load entities
        self.entities = []
        entity_layer = self.data.get_layer_by_name('Entities')
        if entity_layer:
            for entity_obj in entity_layer:
                entity_data: Dict[str, Any] = {'name': entity_obj.name}
                
                if hasattr(entity_obj, 'properties') and entity_obj.properties:
                    entity_data.update(entity_obj.properties)
                
                entity = Entity(entity_data, 16)
                self.entities.append(entity)

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, hero: Hero) -> None:
        self.background_layer.draw(surface, camera_x, camera_y)
        self.foreground_layer.draw(surface, camera_x, camera_y)

    def _get_split_tiles(self, gid: int, tile_image: pygame.Surface) -> List[pygame.Surface]:
        """Cache split tiles to avoid repeated subsurface operations"""
        if gid in self._tile_cache:
            return self._tile_cache[gid]
        
        tile_width = tile_image.get_width()
        tile_height = tile_image.get_height()
        half_w = tile_width // 2
        half_h = tile_height // 2
        
        # Create subsurfaces once and cache them
        split_tiles = [
            tile_image.subsurface(pygame.Rect(0, 0, half_w, half_h)),
            tile_image.subsurface(pygame.Rect(half_w, 0, half_w, half_h)),
            tile_image.subsurface(pygame.Rect(0, half_h, half_w, half_h)),
            tile_image.subsurface(pygame.Rect(half_w, half_h, half_w, half_h))
        ]
        
        self._tile_cache[gid] = split_tiles
        return split_tiles

    def populate_layer(self, layer: Layer) -> None:
        for y in range(layer.data.height):
            for x in range(layer.data.width):
                gid = layer.data.data[y][x]

                # Get the tile image
                tile_image = self.data.get_tile_image_by_gid(gid)
                
                # Get the tile dimensions (per tile, as they may vary)
                tile_width = tile_image.get_width()
                tile_height = tile_image.get_height()
                
                # Use cached split tiles
                split_tiles = self._get_split_tiles(gid, tile_image)

                # Define offsets for the tiles inside a block (using actual tile dimensions)
                offsets = [(0, 0), (tile_width // 2, 0), (0, tile_height // 2), (tile_width // 2, tile_height // 2)]

                # Calculate screen position of the block (using original logic)
                screen_x, screen_y = iso_to_cartesian(x, y)
                screen_x *= self.data.tilewidth // 2
                screen_y *= self.data.tileheight // 2

                # Create blockset
                blockset = Blockset()
                blockset.grid_pos = (x, y)
                blockset.screen_pos = (screen_x, screen_y)
                blockset.gid = gid

                # Create tiles with pre-split images
                for sub_tile_img, offset in zip(split_tiles, offsets):
                    tile = Tile(offset)
                    tile.image = sub_tile_img
                    blockset.tiles.append(tile)
                    
                layer.blocksets.append(blockset)