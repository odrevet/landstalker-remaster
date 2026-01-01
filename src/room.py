import pygame
from typing import List, Tuple, Dict, Any, Optional

from pytmx.util_pygame import load_pygame
from pygame.math import Vector2

from hero import Hero
from utils import cartesian_to_iso, iso_to_cartesian
from warp import Warp
from entity import Entity
from heightmap import Heightmap


class Tile:
    def __init__(self, offset: Tuple[int, int]) -> None:
        self.image: Optional[pygame.Surface] = None
        self.has_priority: bool = False
        self.is_hflipped: bool = False
        self.is_vflipped: bool = False
        self.offset: Vector2 = Vector2(offset[0], offset[1])

    def draw(self, surface: pygame.Surface, screen_pos: Vector2, 
             layer_offset_h: float, camera_x: float, camera_y: float) -> None:
        surface.blit(self.image, 
                    (screen_pos.x - camera_x + self.offset.x + layer_offset_h, 
                     screen_pos.y - camera_y + self.offset.y))


class Blockset:
    def __init__(self) -> None:
        self.tiles: List[Tile] = []
        self.grid_pos: Optional[Vector2] = None
        self.screen_pos: Optional[Vector2] = None
        self.gid: Optional[int] = None

    def draw(self, surface: pygame.Surface, layer_offset_h: float, 
             camera_x: float, camera_y: float, 
             display_width: int, display_height: int) -> None:
        # Culling check - only draw if visible on screen
        if self.screen_pos.x - camera_x + layer_offset_h + 16 > 0 and \
           self.screen_pos.y - camera_y + 16 > 0 and \
           self.screen_pos.x - camera_x + layer_offset_h < display_width and \
           self.screen_pos.y - camera_y < display_height:
            for tile in self.tiles:
                tile.draw(surface, self.screen_pos, layer_offset_h, camera_x, camera_y)


class Layer:
    def __init__(self) -> None:
        self.data: Optional[TiledTileLayer] = None
        self.blocksets: List[Blockset] = []

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float,
             display_width: int, display_height: int) -> None:
        for blockset in self.blocksets:
            blockset.draw(surface, self.data.offsetx, camera_x, camera_y, 
                         display_width, display_height)


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

    def load(self, room_number: int) -> None:
        tmx_filename: str = f"data/rooms/Room{room_number:03d}.tmx"
        print(f"loading {tmx_filename}")
        self.data = load_pygame(tmx_filename)

        # Load room properties FIRST
        self.room_properties = {}
        if hasattr(self.data, "properties") and self.data.properties:
            for key, value in self.data.properties.items():
                self.room_properties[key] = value

        print("Room properties loaded:")
        for k, v in self.room_properties.items():
            print(f"  {k}: {v}")

        # Load heightmap from properties BEFORE populating layers
        self.heightmap.load_from_properties(self.room_properties)
        
        print(f"Heightmap offsets: left={self.heightmap.left_offset}, top={self.heightmap.top_offset}")

        # Now populate layers with correct heightmap offsets
        self.background_layer = Layer()
        self.background_layer.data = self.data.get_layer_by_name("Background")
        self.populate_layer(self.background_layer, is_background=True)
        
        self.foreground_layer = Layer()
        self.foreground_layer.data = self.data.get_layer_by_name("Foreground")
        self.populate_layer(self.foreground_layer, is_background=False)
        
        self.room_number = room_number

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
                # Create a dictionary with all entity properties
                entity_data: Dict[str, Any] = {
                    'name': entity_obj.name,
                }
                
                # Copy all properties from the TMX object
                if hasattr(entity_obj, 'properties') and entity_obj.properties:
                    entity_data.update(entity_obj.properties)
                
                # Create Entity object
                entity = Entity(entity_data, 16)
                self.entities.append(entity)

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, 
             hero: Hero, display_width: int, display_height: int) -> None:
        self.background_layer.draw(surface, camera_x, camera_y, 
                                   display_width, display_height)
        self.foreground_layer.draw(surface, camera_x, camera_y, 
                                   display_width, display_height)
        
        # Prepare entities for drawing (update their screen positions)
        for entity in self.entities:
            entity._update_screen_pos(
                self.heightmap.left_offset,
                self.heightmap.top_offset,
                camera_x,
                camera_y,
                self.background_layer.data.height
            )
        
        # Create a list of all drawable objects (entities + hero)
        drawable_objects = []
        
        # Add all entities with their sort key
        for entity in self.entities:
            if entity.get_world_pos() is not None:
                # Sort key: Y + (Z + height)
                # The top of the object determines draw order in isometric view
                entity_height = entity.HEIGHT
                sort_key = entity.get_world_pos().y - 12 + entity.get_world_pos().z + entity_height
                drawable_objects.append((sort_key, entity))
        
        # Add hero with their sort key
        if hero.get_world_pos() is not None:
            # Hero is 2 tiles tall, so use their full height for sorting
            hero_height = hero.height
            sort_key = hero.get_world_pos().y + hero.get_world_pos().z + hero_height
            drawable_objects.append((sort_key, hero))
        
        # Sort by Y+Z position (ascending order - back to front)
        drawable_objects.sort(key=lambda x: x[0])
        
        # Draw all objects in sorted order
        for _, obj in drawable_objects:
            obj.draw(surface)

    def iso_to_pixel(self, iso_x: int, iso_y: int, is_background: bool, 
                     map_height: int, tile_width: int, tile_height: int, 
                     use_offset: bool = True) -> Tuple[int, int]:
        """
        Convert isometric coordinates to pixel coordinates.
        Matches editor IsoToPixel formula from Tilemap3D.cpp:
        """
        # Layer offset: BG layer has offset of 2, FG layer has offset of 0
        layer_offset = 0 #2 if use_offset else 0

        # Get offsets from heightmap (only if offset flag is true)
        left_offset = self.heightmap.left_offset if use_offset else 0
        top_offset = self.heightmap.top_offset if use_offset else 0
        
        # Apply the C++ formula exactly
        # X coordinate: ((iso.x - iso.y + (GetHeight() - 1)) * 2 + left_offset + layer_offset) * tile_width
        pixel_x = ((iso_x - iso_y + (map_height - 1)) * 2 + left_offset + layer_offset) * tile_width
        
        # Y coordinate: (iso.x + iso.y + top_offset) * tile_height
        pixel_y = (iso_x + iso_y + top_offset) * tile_height
        
        return pixel_x, pixel_y

    def populate_layer(self, layer: Layer, is_background: bool) -> None:
        # In Landstalker, tiles are 8x8 pixels
        # The full 16x16 block is split into 4 quadrants
        tile_width = 8   # Each sub-tile is 8 pixels wide
        tile_height = 8  # Each sub-tile is 8 pixels tall
        map_height = layer.data.height
        
        layer_name = "Background" if is_background else "Foreground"
        
        for y in range(layer.data.height):
            for x in range(layer.data.width):
                gid: int = layer.data.data[y][x]

                # Get the tile image (this should be a 16x16 block)
                tile_image: pygame.Surface = self.data.get_tile_image_by_gid(gid)
                
                if tile_image is None:
                    continue
                    
                tile_image = tile_image.convert_alpha()
                
                # Get the tile dimensions (should be 16x16)
                tile_w: int = tile_image.get_width()
                tile_h: int = tile_image.get_height()

                # Define sub-rects for each quadrant of the 16x16 tile
                # Split into 4 8x8 tiles
                top_left_rect: pygame.Rect = pygame.Rect(0, 0, tile_w // 2, tile_h // 2)
                top_right_rect: pygame.Rect = pygame.Rect(tile_w // 2, 0, tile_w // 2, tile_h // 2)
                bottom_left_rect: pygame.Rect = pygame.Rect(0, tile_h // 2, tile_w // 2, tile_h // 2)
                bottom_right_rect: pygame.Rect = pygame.Rect(tile_w // 2, tile_h // 2, tile_w // 2, tile_h // 2)

                # Define offsets for the 4 tiles inside the block
                # These position each 8x8 tile within the 16x16 block area
                offsets: List[Tuple[int, int]] = [
                    (0, 0),           # Top-left
                    (tile_w // 2, 0), # Top-right
                    (0, tile_h // 2), # Bottom-left
                    (tile_w // 2, tile_h // 2)  # Bottom-right
                ]
                tiles_rect: List[pygame.Rect] = [top_left_rect, top_right_rect, bottom_left_rect, bottom_right_rect]

                screen_x, screen_y = self.iso_to_pixel(x, y, is_background, map_height, tile_width, tile_height, True)

                print(
                    "[populate_layer]\n"
                    f"  Map XY        : ({x}, {y})\n"
                    f"  Layer         : {layer_name}\n"
                    f"  Background    : {is_background}\n"
                    f"  Offset        : True\n"
                    f"  GID           : 0x{gid:X}\n"
                    f"  Tile Size     : ({tile_w}, {tile_h})\n"
                    f"  SubTile Size  : ({tile_width}, {tile_height})\n"
                    f"  Map Height    : {map_height}\n"
                    f"  Left Offset   : {self.heightmap.left_offset}\n"
                    f"  Top Offset    : {self.heightmap.top_offset}\n"
                    f"  Pixel XY      : ({screen_x}, {screen_y})\n"
                    "----------------------------------------"
                )

                # Instantiate a new blockset
                blockset: Blockset = Blockset()
                blockset.grid_pos = Vector2(x, y)
                blockset.screen_pos = Vector2(screen_x, screen_y)
                blockset.gid = gid

                # Create 4 tiles from the block
                for index, (sub_tile, offset) in enumerate(zip(tiles_rect, offsets)):
                    tile: Tile = Tile(offset)
                    tile.image = tile_image.subsurface(sub_tile)
                    tile.image = tile.image.convert_alpha()
                    blockset.tiles.append(tile)
                    
                layer.blocksets.append(blockset)