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
             camera_x: float, camera_y: float, debug_slow: bool = False,
             screen: Optional[pygame.Surface] = None, display_width: int = DRAWING_WIDTH,
             display_height: int = DRAWING_HEIGHT) -> None:
        if self.screen_pos.x - camera_x + layer_offset_h + 16 > 0 and \
           self.screen_pos.y - camera_y + layer_offset_h + 16 > 0 and \
           self.screen_pos.x - camera_x < DRAWING_WIDTH and \
           self.screen_pos.y - camera_y < DRAWING_HEIGHT:
            for tile in self.tiles:
                tile.draw(surface, self.screen_pos, layer_offset_h, camera_x, camera_y)
            
            # Debug: pause after drawing this blockset
            if debug_slow and screen:
                # Scale and display immediately
                screen_w, screen_h = screen.get_size()
                scale = min(screen_w / display_width, screen_h / display_height)
                scaled_w = int(display_width * scale)
                scaled_h = int(display_height * scale)
                scaled_surface = pygame.transform.scale(surface, (scaled_w, scaled_h))
                
                offset_x = (screen_w - scaled_w) // 2
                offset_y = (screen_h - scaled_h) // 2
                screen.fill((0, 0, 0))
                screen.blit(scaled_surface, (offset_x, offset_y))


class Layer:
    def __init__(self) -> None:
        self.data: Optional[TiledTileLayer] = None
        self.blocksets: List[Blockset] = []

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float,
             debug_slow: bool = False, screen: Optional[pygame.Surface] = None) -> None:
        for blockset in self.blocksets:
            blockset.draw(surface, self.data.offsetx, camera_x, camera_y, 
                         debug_slow, screen)


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

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, hero: Hero,
                debug_slow: bool = False, screen: Optional[pygame.Surface] = None) -> None:
        # Prepare entities for drawing (update their screen positions)
        tile_h = self.data.tileheight
        for entity in self.entities:
            entity._update_screen_pos(
                self.heightmap.left_offset,
                self.heightmap.top_offset,
                camera_x,
                camera_y
            )
        
        # Create a list of all drawable objects (entities + hero)
        drawable_objects = []
        
        # Add all entities
        for entity in self.entities:
            # Use bottom corner for sort key calculation
            x = entity.get_world_pos().x
            y = entity.get_world_pos().y
            z = entity.get_world_pos().z
            sort_key = x / tile_h + y / tile_h + z / tile_h
            drawable_objects.append((sort_key, 'entity', entity))
            #print(f"add entity bottom corner {x} {y} sort key {sort_key}")
        
        # Add hero
        # Use bottom corner for sort key calculation
        x = hero.get_world_pos().x
        y = hero.get_world_pos().y
        z = hero.get_world_pos().z
        sort_key = x / tile_h + y / tile_h + z / tile_h
        drawable_objects.append((sort_key, 'entity', hero))
        #print(f"add hero bottom corner {x} {y} sort key {sort_key}")
        
        # Add heightmap cells with their sort keys
        offset_x = (self.heightmap.left_offset - 12) * tile_h - 12
        offset_y = (self.heightmap.top_offset - 11) * tile_h - 12
        for y, row in enumerate(self.heightmap.cells):
            for x, cell in enumerate(row):
                sort_key = x + y
                drawable_objects.append((sort_key, 'heightmap', (x, y, cell)))
                #print(f"add heightmap {x} {y} sort key {sort_key}")
        
        # Sort all objects by sort key only
        drawable_objects.sort(key=lambda obj: obj[0])
        
        # Draw all objects in sorted order with masking
        for sort_key, obj_type, obj in drawable_objects:
            if obj_type == 'entity':
                #print(f"{obj_type} pos {obj.get_world_pos()} key {sort_key}")
                obj.draw(surface)
            elif obj_type == 'heightmap':
                x, y, cell = obj
                #print(f"{obj_type} pos {x} {y} key {sort_key}")
                self._draw_heightmap_cell_mask(surface, x, y, cell, tile_h, camera_x, camera_y, offset_x, offset_y)
            
            # Debug: pause after drawing each object
            if debug_slow and screen:
                screen_w, screen_h = screen.get_size()
                scale = min(screen_w / DRAWING_WIDTH, screen_h / DRAWING_HEIGHT)
                scaled_w = int(DRAWING_WIDTH * scale)
                scaled_h = int(DRAWING_HEIGHT * scale)
                scaled_surface = pygame.transform.scale(surface, (scaled_w, scaled_h))
                offset_x_screen = (screen_w - scaled_w) // 2
                offset_y_screen = (screen_h - scaled_h) // 2
                screen.fill((0, 0, 0))
                screen.blit(scaled_surface, (offset_x_screen, offset_y_screen))
                pygame.display.flip()
                pygame.time.delay(150)

    def _draw_heightmap_cell_mask(self, screen: pygame.Surface, 
                                x: int, y: int, cell, tile_height: int, 
                                camera_x: float, camera_y: float, 
                                offset_x: float, offset_y: float) -> None:
        """Draw a heightmap cell as a solid mask to occlude entities behind it."""
        
        height = cell.height
        
        # Skip cells at ground level (height 0) as they don't occlude
        if height == 0:
            return
        
        # Compute four corners of tile
        left_x, left_y = cartesian_to_iso(
            x * tile_height - offset_x,
            y * tile_height + tile_height - offset_y
        )
        bottom_x, bottom_y = cartesian_to_iso(
            x * tile_height + tile_height - offset_x,
            y * tile_height + tile_height - offset_y,
        )
        top_x, top_y = cartesian_to_iso(
            x * tile_height - offset_x, 
            y * tile_height - offset_y
        )
        right_x, right_y = cartesian_to_iso(
            x * tile_height + tile_height - offset_x,
            y * tile_height - offset_y
        )
        
        # Choose base color by conditions
        if cell.walkable >= 4:
            base_color = (255, 80, 80)
        elif height >= 20:
            base_color = (255, 120, 120)
        else:
            base_color = (200, 200, 255)
        
        # Draw the top face as a solid polygon
        top_points = [
            (left_x - camera_x,  left_y  - camera_y - height * tile_height),
            (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
            (right_x - camera_x, right_y - camera_y - height * tile_height),
            (top_x - camera_x,   top_y   - camera_y - height * tile_height),
        ]
        
        if len(top_points) >= 3:
            pygame.draw.polygon(screen, base_color, top_points)
        
        # Draw vertical faces if neighboring tiles are lower
        heightmap = self.heightmap
        
        # Right face (when right neighbor is lower)
        if x < len(heightmap.cells[0]) - 1:
            neighbor_h = heightmap.cells[y][x + 1].height
            if neighbor_h < height:
                # Darken color for side face
                side_color = (base_color[0] * 0.7, base_color[1] * 0.7, base_color[2] * 0.7)
                
                front_points = [
                    (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                    (bottom_x - camera_x, bottom_y - camera_y - neighbor_h * tile_height),
                    (right_x - camera_x, right_y - camera_y - neighbor_h * tile_height),
                    (right_x - camera_x, right_y - camera_y - height * tile_height),
                ]
                
                pygame.draw.polygon(screen, side_color, front_points)
        
        # Left face (when bottom neighbor is lower)
        if y < len(heightmap.cells) - 1:
            neighbor_h = heightmap.cells[y + 1][x].height
            if neighbor_h < height:
                # Darken color more for left face (different angle)
                side_color = (base_color[0] * 0.5, base_color[1] * 0.5, base_color[2] * 0.5)
                
                side_points = [
                    (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                    (bottom_x - camera_x, bottom_y - camera_y - neighbor_h * tile_height),
                    (left_x - camera_x, left_y - camera_y - neighbor_h * tile_height),
                    (left_x - camera_x, left_y - camera_y - height * tile_height),
                ]
                
                pygame.draw.polygon(screen, side_color, side_points)

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