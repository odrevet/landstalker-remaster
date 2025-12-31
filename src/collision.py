# Updates needed for collision.py to work with new tile-based coordinate system

# Key changes:
# - World coordinates are now in TILES (not pixels)
# - x=1.0 means 1 tile, x=0.5 means half a tile
# - BoundingBox methods still work with pixels for size calculations
# - Conversion: world_tiles * tile_h = world_pixels

from typing import List, Tuple, Optional
from pygame.math import Vector3
from hero import Hero
from entity import Entity
from heightmap import Heightmap, HeightmapCell

MARGIN: int = 2


def check_entity_collision_3d(moving_bbox, target_bbox, tile_h: int) -> bool:
    """Check if two entities collide in 3D space
    
    World positions are in tiles, but bbox calculations use pixels.
    """
    # Convert world position (tiles) to pixels for bbox calculation
    me_x = moving_bbox.world_pos.x * tile_h + MARGIN
    me_y = moving_bbox.world_pos.y * tile_h + MARGIN
    me_w = (tile_h * moving_bbox.size_in_tiles) - (MARGIN * 2)
    me_h = (tile_h * moving_bbox.size_in_tiles) - (MARGIN * 2)
    
    te_x = target_bbox.world_pos.x * tile_h + MARGIN
    te_y = target_bbox.world_pos.y * tile_h + MARGIN
    te_w = (tile_h * target_bbox.size_in_tiles) - (MARGIN * 2)
    te_h = (tile_h * target_bbox.size_in_tiles) - (MARGIN * 2)
    
    # Check XY plane collision (AABB)
    xy_collision = (me_x < te_x + te_w and
                    me_x + me_w > te_x and
                    me_y < te_y + te_h and
                    me_y + me_h > te_y)
    
    if not xy_collision:
        return False
    
    # Check Z axis collision (Z is also in tiles)
    moving_z = moving_bbox.world_pos.z
    target_z = target_bbox.world_pos.z
    moving_z_height = moving_bbox.height_in_tiles
    target_z_height = target_bbox.height_in_tiles
    
    z_collision = (moving_z < target_z + target_z_height and
                   moving_z + moving_z_height > target_z)
    
    return z_collision


def check_collids_entity(hero: Hero, x: float, y: float, entities: List[Entity], tile_h: int) -> Optional[Entity]:
    """Check if hero collides with any entity at the given position
    
    Args:
        hero: The hero object
        x: X position to check (in tiles)
        y: Y position to check (in tiles)
        entities: List of entities to check collision against
        tile_h: Tile height in pixels
    """
    from boundingbox import BoundingBox
    
    hero_pos = hero.get_world_pos()
    
    # Create temporary bounding box at new position (positions in tiles)
    temp_bbox = BoundingBox(
        Vector3(x, y, hero_pos.z),
        hero.bbox.height_in_tiles,
        hero.bbox.size_in_tiles
    )
    
    for entity in entities:
        if check_entity_collision_3d(temp_bbox, entity.bbox, tile_h):
            return entity
    
    return None


def resolve_entity_collision(hero: Hero, entities: List[Entity], new_x: float, new_y: float,
                            tile_h: int, left_offset: int, top_offset: int,
                            camera_x: float, camera_y: float) -> Tuple[float, float, Optional[Entity]]:
    """Resolve collision between hero and entities when moving to new position
    
    Args:
        new_x: Proposed new X position (in tiles)
        new_y: Proposed new Y position (in tiles)
    
    Returns:
        Tuple of (final_x, final_y, touched_entity) where positions are in tiles
    """
    hero_pos = hero.get_world_pos()
    touched_entity: Entity
    
    # Check if new position would cause collision
    touched_entity = check_collids_entity(hero, new_x, new_y, entities, tile_h)
    if touched_entity is None:
        return new_x, new_y, touched_entity
    
    # Collision detected, try to slide along obstacles
    # Try X-only movement
    touched_entity = check_collids_entity(hero, new_x, hero_pos.y, entities, tile_h)
    if touched_entity is None:
        return new_x, hero_pos.y, touched_entity
    
    # Try Y-only movement
    touched_entity = check_collids_entity(hero, hero_pos.x, new_y, entities, tile_h)
    if touched_entity is None:
        return hero_pos.x, new_y, touched_entity
    
    return hero_pos.x, hero_pos.y, touched_entity


def get_entity_top_at_position(entities: List[Entity], check_x: float, check_y: float,
                               check_width: float, check_height: float,
                               hero_z: float, tile_h: int) -> Optional[float]:
    """Get the highest entity surface under the given position
    
    Args:
        check_x, check_y, check_width, check_height: Position and size in PIXELS
        hero_z: Hero's current Z position in TILES
    
    Returns:
        Z position in PIXELS (for backward compatibility with existing code)
    """
    highest_top: Optional[float] = None
    
    for entity in entities:
        if not entity.solid or not entity.visible:
            continue
        
        # Convert entity position (tiles) to pixels for collision check
        entity_x = entity.bbox.world_pos.x * tile_h + MARGIN
        entity_y = entity.bbox.world_pos.y * tile_h + MARGIN
        entity_w = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        entity_h = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        
        # Check XY overlap
        xy_overlap = (check_x < entity_x + entity_w and
                     check_x + check_width > entity_x and
                     check_y < entity_y + entity_h and
                     check_y + check_height > entity_y)
        
        if not xy_overlap:
            continue
        
        # Calculate entity top Z position (in tiles, then convert to pixels)
        entity_top_tiles = entity.bbox.world_pos.z + entity.bbox.height_in_tiles
        entity_top_pixels = entity_top_tiles * tile_h
        
        # Only consider entities below hero (hero_z is in tiles, convert for comparison)
        if entity_top_pixels <= hero_z * tile_h + 1.0:
            if highest_top is None or entity_top_pixels > highest_top:
                highest_top = entity_top_pixels
    
    return highest_top


def get_entity_hero_is_standing_on(hero: Hero, entities: List[Entity], tile_h: int) -> Optional[Entity]:
    """Get the entity that the hero is currently standing on"""
    hero_pos = hero.get_world_pos()  # In tiles
    hero_bbox = hero.get_bounding_box(tile_h)  # In pixels
    check_x, check_y, check_width, check_height = hero_bbox
    
    highest_entity: Optional[Entity] = None
    highest_top: Optional[float] = None
    
    for entity in entities:
        if not entity.solid or not entity.visible or entity is hero.grabbed_entity:
            continue
        
        # Convert entity position (tiles) to pixels
        entity_x = entity.bbox.world_pos.x * tile_h + MARGIN
        entity_y = entity.bbox.world_pos.y * tile_h + MARGIN
        entity_w = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        entity_h = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        
        # Check XY overlap
        xy_overlap = (check_x < entity_x + entity_w and
                     check_x + check_width > entity_x and
                     check_y < entity_y + entity_h and
                     check_y + check_height > entity_y)
        
        if not xy_overlap:
            continue
        
        # Calculate entity top Z position (in tiles)
        entity_top = entity.bbox.world_pos.z + entity.bbox.height_in_tiles
        
        # Check if hero is standing on this entity (both in tiles)
        if abs(hero_pos.z - entity_top) <= 0.0625:  # 1 pixel tolerance = 1/16 tiles
            if highest_top is None or entity_top > highest_top:
                highest_top = entity_top
                highest_entity = entity
    
    return highest_entity


def get_position_in_front_of_hero(hero: Hero, tile_h: int) -> Tuple[float, float]:
    """Get the position one tile in front of the hero
    
    Returns:
        Tuple of (x, y) position in PIXELS (for backward compatibility)
    """
    hero_pos = hero.get_world_pos()  # In tiles
    front_x = hero_pos.x  # In tiles
    front_y = hero_pos.y
    
    if hero.facing_direction == "UP":
        front_y -= 1.0  # 1 tile
    elif hero.facing_direction == "DOWN":
        front_y += 1.0
    elif hero.facing_direction == "LEFT":
        front_x -= 1.0
    elif hero.facing_direction == "RIGHT":
        front_x += 1.0
    
    # Convert to pixels for return
    return front_x * tile_h, front_y * tile_h


def get_entity_in_front_of_hero(hero: Hero, entities: List[Entity], tile_h: int) -> Optional[Entity]:
    """Get the entity directly in front of the hero"""
    front_x, front_y = get_position_in_front_of_hero(hero, tile_h)  # In pixels
    hero_pos = hero.get_world_pos()  # In tiles
    
    check_size = tile_h * 0.8
    
    for entity in entities:
        if not entity.visible or entity is hero.grabbed_entity:
            continue
        
        # Convert entity position (tiles) to pixels
        entity_x = entity.bbox.world_pos.x * tile_h + MARGIN
        entity_y = entity.bbox.world_pos.y * tile_h + MARGIN
        entity_w = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        entity_h = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        
        # Check if position in front overlaps with entity
        overlap = (front_x < entity_x + entity_w and
                  front_x + check_size > entity_x and
                  front_y < entity_y + entity_h and
                  front_y + check_size > entity_y)
        
        if not overlap:
            continue
        
        # Check Z overlap (all in tiles now)
        entity_z = entity.bbox.world_pos.z
        entity_height = entity.bbox.height_in_tiles
        hero_height = hero.bbox.height_in_tiles
        
        z_overlap = (hero_pos.z < entity_z + entity_height and
                    hero_pos.z + hero_height > entity_z)
        
        if z_overlap:
            return entity
    
    return None


def can_place_entity_at_position(hero_z: float, entity: Entity, x: float, y: float, z: float,
                                other_entities: List[Entity], heightmap: Heightmap,
                                tile_h: int) -> bool:
    """Check if an entity can be placed at the given position
    
    Args:
        hero_z: Hero Z position in TILES
        x, y: Position in PIXELS (from get_position_in_front_of_hero)
        z: Z position in PIXELS
    """
    from boundingbox import BoundingBox
    
    # Convert pixel coordinates to tiles
    tile_x = int(x // tile_h)
    tile_y = int(y // tile_h)
    
    if (tile_x < 0 or tile_y < 0 or
        tile_x >= heightmap.get_width() or
        tile_y >= heightmap.get_height()):
        return False
    
    cell: Optional[HeightmapCell] = heightmap.get_cell(tile_x, tile_y)
    if not cell or not cell.is_walkable():
        return False
    
    # Check if Z matches terrain height (cell.height is in tiles)
    terrain_z = cell.height
    if terrain_z - hero_z > 2.0:  # 2 tiles = 32 pixels
        return False
    
    # Create temporary bounding box for collision check
    # Convert pixel coordinates to tiles for bbox
    x_tiles = x / tile_h
    y_tiles = y / tile_h
    z_tiles = z / tile_h
    
    temp_bbox = BoundingBox(
        Vector3(x_tiles, y_tiles, z_tiles),
        entity.bbox.height_in_tiles,
        entity.bbox.size_in_tiles
    )
    
    # Check collision with other entities
    for other in other_entities:
        if other is entity or not other.solid or not other.visible:
            continue
        
        if check_entity_collision_3d(temp_bbox, other.bbox, tile_h):
            return False
    
    return True


def update_carried_positions(hero, entities, tile_h, heightmap_left_offset,
                            heightmap_top_offset, camera_x, camera_y, tilemap_height):
    """Move hero/entities that are standing on moving entities"""
    
    # Check if hero is standing on an entity
    standing_on = get_entity_hero_is_standing_on(hero, entities, tile_h)
    if standing_on:
        dx, dy, dz = standing_on.get_position_delta()  # Deltas in tiles
        if dx != 0 or dy != 0 or dz != 0:
            hero_pos = hero.get_world_pos()  # In tiles
            hero.set_world_pos(
                hero_pos.x + dx,
                hero_pos.y + dy,
                hero_pos.z + dz,
                heightmap_left_offset,
                heightmap_top_offset,
                camera_x,
                camera_y,
                tilemap_height
            )
            if hero.is_grabbing:
                hero.update_grabbed_entity_position(
                    heightmap_left_offset, heightmap_top_offset,
                    camera_x, camera_y, tile_h, tilemap_height
                )
    
    # Check each entity standing on other entities
    for entity in entities:
        standing_on = get_entity_top_at_position(
            [e for e in entities if e is not entity],
            *entity.get_bounding_box(tile_h),
            entity.get_world_pos().z,
            tile_h
        )
        if standing_on is not None:
            for other in entities:
                if other is entity:
                    continue
                other_pos = other.get_world_pos()  # In tiles
                other_height = other.height if hasattr(other, 'height') else 1.0  # In tiles
                # standing_on is in pixels, convert for comparison
                if abs((other_pos.z + other_height) * tile_h - standing_on) < 1.0:
                    dx, dy, dz = other.get_position_delta()
                    if dx != 0 or dy != 0 or dz != 0:
                        entity_pos = entity.get_world_pos()
                        entity.set_world_pos(
                            entity_pos.x + dx,
                            entity_pos.y + dy,
                            entity_pos.z + dz,
                            heightmap_left_offset,
                            heightmap_top_offset,
                            camera_x,
                            camera_y,
                            tilemap_height
                        )
                    break
    
    # Update all prev positions for next frame
    hero.update_prev_position()
    for entity in entities:
        entity.update_prev_position()


def get_touching_entities(hero: Hero, entities: List[Entity], tile_h: int) -> List[Entity]:
    """Get all entities currently touching the hero in 3D space"""
    touching_entities: List[Entity] = []
    
    for entity in entities:
        if entity is hero.grabbed_entity:
            continue
        
        if not entity.visible:
            continue
        
        if check_entity_collision_3d(hero.bbox, entity.bbox, tile_h):
            touching_entities.append(entity)
    
    return touching_entities