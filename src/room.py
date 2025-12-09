import pygame
from typing import List, Tuple, Dict, Any, Optional

from pytmx.util_pygame import load_pygame, TiledMap
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
             camera_x: float, camera_y: float) -> None:
        if self.screen_pos.x - camera_x + layer_offset_h > -16 and \
           self.screen_pos.y - camera_y > -16 and \
           self.screen_pos.x - camera_x + layer_offset_h < 448 and \
           self.screen_pos.y - camera_y < 320:
            for tile in self.tiles:
                tile.draw(surface, self.screen_pos, layer_offset_h, camera_x, camera_y)


class Layer:
    def __init__(self) -> None:
        self.data: Optional[TiledTileLayer] = None
        self.blocksets: List[Blockset] = []

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float) -> None:
        for blockset in self.blocksets:
            blockset.draw(surface, self.data.offsetx, camera_x, camera_y)


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

        self.background_layer = Layer()
        self.background_layer.data = self.data.get_layer_by_name("Background")
        self.populate_layer(self.background_layer)
        
        self.foreground_layer = Layer()
        self.foreground_layer.data = self.data.get_layer_by_name("Foreground")
        self.populate_layer(self.foreground_layer)
        
        self.room_number = room_number

        # Load room properties
        self.room_properties = {}
        if hasattr(self.data, "properties") and self.data.properties:
            for key, value in self.data.properties.items():
                self.room_properties[key] = value

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

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, hero: Hero) -> None:
        self.background_layer.draw(surface, camera_x, camera_y)

        for blockset in self.foreground_layer.blocksets:
            for tile in blockset.tiles:
                if tile.has_priority == False:
                    tile.draw(surface, blockset.screen_pos, self.foreground_layer.data.offsetx, camera_x, camera_y)

        #hero.draw(surface)
        
        for blockset in self.background_layer.blocksets:
            for tile in blockset.tiles:
                if tile.has_priority == True:
                    tile.draw(surface, blockset.screen_pos, self.background_layer.data.offsetx, camera_x, camera_y)

    def populate_layer(self, layer: Layer) -> None:
        for y in range(layer.data.height):
            for x in range(layer.data.width):
                gid: int = layer.data.data[y][x]

                # Get the tile image
                tile_image: pygame.Surface = self.data.get_tile_image_by_gid(gid)
                
                # Get the tile dimensions
                tile_width: int
                tile_height: int
                tile_width, tile_height = tile_image.get_width(), tile_image.get_height()

                # Define sub-rects for each quadrant of the tile
                top_left_rect: pygame.Rect = pygame.Rect(0, 0, tile_width // 2, tile_height // 2)
                top_right_rect: pygame.Rect = pygame.Rect(tile_width // 2, 0, tile_width // 2, tile_height // 2)
                bottom_left_rect: pygame.Rect = pygame.Rect(0, tile_height // 2, tile_width // 2, tile_height // 2)
                bottom_right_rect: pygame.Rect = pygame.Rect(tile_width // 2, tile_height // 2, tile_width // 2, tile_height // 2)

                # Define offsets for the tiles inside a block
                offsets: List[Tuple[int, int]] = [(0, 0), (tile_width // 2, 0), (0, tile_height // 2), (tile_width // 2, tile_height // 2)]
                tiles_rect: List[pygame.Rect] = [top_left_rect, top_right_rect, bottom_left_rect, bottom_right_rect]

                # Calculate screen position of the block
                screen_x: float
                screen_y: float
                screen_x, screen_y = iso_to_cartesian(x, y)
                screen_x *= self.data.tilewidth // 2
                screen_y *= self.data.tileheight // 2

                # instanciate a new blockset
                blockset: Blockset = Blockset()
                blockset.grid_pos = Vector2(x, y)
                blockset.screen_pos = Vector2(screen_x, screen_y)
                blockset.gid = gid

                # Access the tile properties
                tile_properties: Optional[Dict[str, Any]] = self.data.get_tile_properties_by_gid(gid)

                for index, (sub_tile, offset) in enumerate(zip(tiles_rect, offsets)):
                    tile: Tile = Tile(offset)
                    tile.image = tile_image.subsurface(sub_tile)

                    # tile.is_hflipped = tile_properties.get(f"isHFlipped{index}", False)
                    # tile.is_vflipped = tile_properties.get(f"isVFlipped{index}", False)
                    # tile.has_priority = tile_properties.get(f"hasPriority{index}", False)

                    blockset.tiles.append(tile)
                layer.blocksets.append(blockset)
