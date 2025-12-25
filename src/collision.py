from typing import List, Tuple, Optional
from pygame.math import Vector3
from hero import Hero
from entity import Entity
from heightmap import Heightmap, HeightmapCell

# Margin to reduce bounding box size for tighter collision detection
MARGIN: int = 2


def check_entity_collision_3d(moving_bbox,
                              target_bbox,
                              tile_h: int) -> bool:
    """Check if two entities collide in 3D space
    
    Args:
        moving_bbox: BoundingBox of moving entity
        target_bbox: BoundingBox of target entity
        tile_h: Tile height in pixels
        
    Returns:
        True if collision detected, False otherwise
    """
    # Calculate bounding boxes from world positions
    me_x = moving_bbox.world_pos.x + MARGIN
    me_y = moving_bbox.world_pos.y + MARGIN
    me_w = (tile_h * moving_bbox.size_in_tiles) - (MARGIN * 2)
    me_h = (tile_h * moving_bbox.size_in_tiles) - (MARGIN * 2)
    
    te_x = target_bbox.world_pos.x + MARGIN
    te_y = target_bbox.world_pos.y + MARGIN
    te_w = (tile_h * target_bbox.size_in_tiles) - (MARGIN * 2)
    te_h = (tile_h * target_bbox.size_in_tiles) - (MARGIN * 2)
    
    # Check XY plane collision (AABB)
    xy_collision = (me_x < te_x + te_w and
                    me_x + me_w > te_x and
                    me_y < te_y + te_h and
                    me_y + me_h > te_y)
    
    if not xy_collision:
        return False
    
    # Check Z axis collision
    moving_z = moving_bbox.world_pos.z
    target_z = target_bbox.world_pos.z
    moving_z_height = moving_bbox.height_in_tiles * tile_h
    target_z_height = target_bbox.height_in_tiles * tile_h
    
    z_collision = (moving_z < target_z + target_z_height and
                   moving_z + moving_z_height > target_z)
    
    return z_collision


def check_collids_entity(hero: Hero,
                        x: float,
                        y: float,
                        entities: List[Entity],
                        tile_h: int) -> Optional[Entity]:
    """Check if hero collides with any entity at the given position
    
    Args:
        hero: The hero object
        x: X position to check
        y: Y position to check
        entities: List of entities to check collision against
        tile_h: Tile height in pixels
        
    Returns:
        Entity that collides, or None if no collision
    """
    from boundingbox import BoundingBox
    
    hero_pos = hero.get_world_pos()
    
    # Create temporary bounding box at new position
    temp_bbox = BoundingBox(
        Vector3(x, y, hero_pos.z),
        hero.bbox.height_in_tiles,
        hero.bbox.size_in_tiles
    )
    
    for entity in entities:
        # Check 3D collision
        if check_entity_collision_3d(temp_bbox, entity.bbox, tile_h):
            return entity
    
    return None

def resolve_entity_collision(hero: Hero,
                            entities: List[Entity],
                            new_x: float,
                            new_y: float,
                            tile_h: int,
                            left_offset: int,
                            top_offset: int,
                            camera_x: float,
                            camera_y: float) -> Tuple[float, float, Optional[Entity]]:
    """Resolve collision between hero and entities when moving to new position
    
    This function checks if the hero would collide with any solid entities at the new position.
    If a collision is detected, it returns the hero's current position instead of the new position.
    
    Args:
        hero: The hero object
        entities: List of entities to check collision against
        new_x: Proposed new X position
        new_y: Proposed new Y position
        tile_h: Tile height in pixels
        left_offset: Heightmap left offset
        top_offset: Heightmap top offset
        camera_x: Camera X position
        camera_y: Camera Y position
        
    Returns:
        Tuple of (final_x, final_y, touched_entities)
        - final_x, final_y: Position after collision resolution
        - touched_entity: entity that were touched during movement
    """
    hero_pos = hero.get_world_pos()
    touched_entity: Entity
    
    # Check if new position would cause collision
    touched_entity = check_collids_entity(hero, new_x, new_y, entities, tile_h)
    if touched_entity is None:
        return new_x, new_y, touched_entity
    
    # Collision detected, try to slide along obstacles
    # Try X-only movement
    touched_entity =  check_collids_entity(hero, new_x, hero_pos.y, entities, tile_h)
    if touched_entity is None:
        return new_x, hero_pos.y, touched_entity
    
    # Try Y-only movement
    touched_entity = check_collids_entity(hero, hero_pos.x, new_y, entities, tile_h)
    if touched_entity is None:
        return hero_pos.x, new_y, touched_entity
    
    return hero_pos.x, hero_pos.y, touched_entity


def get_entity_top_at_position(entities: List[Entity],
                               check_x: float,
                               check_y: float,
                               check_width: float,
                               check_height: float,
                               hero_z: float,
                               tile_h: int) -> Optional[float]:
    """Get the highest entity surface under the given position
    
    This is used for gravity calculations to check if hero is standing on an entity.
    
    Args:
        entities: List of entities to check
        check_x: X position to check
        check_y: Y position to check
        check_width: Width of area to check
        check_height: Height of area to check
        hero_z: Hero's current Z position (feet level)
        tile_h: Tile height in pixels
        
    Returns:
        Z position of highest entity top, or None if no entity below
    """
    highest_top: Optional[float] = None
    
    for entity in entities:
        if not entity.solid or not entity.visible:
            continue
        
        # Get entity bounding box
        entity_x = entity.bbox.world_pos.x + MARGIN
        entity_y = entity.bbox.world_pos.y + MARGIN
        entity_w = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        entity_h = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        
        # Check XY overlap
        xy_overlap = (check_x < entity_x + entity_w and
                     check_x + check_width > entity_x and
                     check_y < entity_y + entity_h and
                     check_y + check_height > entity_y)
        
        if not xy_overlap:
            continue
        
        # Calculate entity top Z position
        entity_top = entity.bbox.world_pos.z + (entity.bbox.height_in_tiles * tile_h)
        
        # Only consider entities below hero (with small tolerance)
        if entity_top <= hero_z + 1.0:
            if highest_top is None or entity_top > highest_top:
                highest_top = entity_top
    
    return highest_top

def get_entity_hero_is_standing_on(hero: Hero,
                                   entities: List[Entity],
                                   tile_h: int) -> Optional[Entity]:
    """Get the entity that the hero is currently standing on
    
    This checks which entity surface the hero is directly on top of.
    
    Args:
        hero: The hero object
        entities: List of entities to check
        tile_h: Tile height in pixels
        
    Returns:
        Entity hero is standing on, or None if not on any entity
    """
    hero_pos = hero.get_world_pos()
    hero_bbox = hero.get_bounding_box(tile_h)
    check_x, check_y, check_width, check_height = hero_bbox
    
    highest_entity: Optional[Entity] = None
    highest_top: Optional[float] = None
    
    for entity in entities:
        # Skip non-solid, invisible, and grabbed entities
        if not entity.solid or not entity.visible or entity is hero.grabbed_entity:
            continue
        
        # Get entity bounding box
        entity_x = entity.bbox.world_pos.x + MARGIN
        entity_y = entity.bbox.world_pos.y + MARGIN
        entity_w = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        entity_h = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        
        # Check XY overlap
        xy_overlap = (check_x < entity_x + entity_w and
                     check_x + check_width > entity_x and
                     check_y < entity_y + entity_h and
                     check_y + check_height > entity_y)
        
        if not xy_overlap:
            continue
        
        # Calculate entity top Z position
        entity_top = entity.bbox.world_pos.z + (entity.bbox.height_in_tiles * tile_h)
        
        # Check if hero is standing on this entity (hero's feet are at entity's top)
        # Allow small tolerance for floating point precision
        if abs(hero_pos.z - entity_top) <= 1.0:
            if highest_top is None or entity_top > highest_top:
                highest_top = entity_top
                highest_entity = entity
    
    return highest_entity
    
def get_position_in_front_of_hero(hero: Hero, tile_h: int) -> Tuple[float, float]:
    """Get the position one tile in front of the hero based on facing direction
    
    Args:
        hero: The hero object
        tile_h: Tile height in pixels
        
    Returns:
        Tuple of (x, y) position in front of hero
    """
    hero_pos = hero.get_world_pos()
    front_x = hero_pos.x
    front_y = hero_pos.y
    
    if hero.facing_direction == "UP":
        front_y -= tile_h
    elif hero.facing_direction == "DOWN":
        front_y += tile_h
    elif hero.facing_direction == "LEFT":
        front_x -= tile_h
    elif hero.facing_direction == "RIGHT":
        front_x += tile_h
    
    return front_x, front_y


def get_entity_in_front_of_hero(hero: Hero,
                                entities: List[Entity],
                                tile_h: int) -> Optional[Entity]:
    """Get the entity directly in front of the hero (for interactions)
    
    Args:
        hero: The hero object
        entities: List of entities to check
        tile_h: Tile height in pixels
        
    Returns:
        Entity in front of hero, or None if no entity found
    """
    front_x, front_y = get_position_in_front_of_hero(hero, tile_h)
    hero_pos = hero.get_world_pos()
    
    # Create a small bounding box at the position in front
    check_size = tile_h * 0.8  # Slightly smaller than full tile for better detection
    
    for entity in entities:
        if not entity.visible or entity is hero.grabbed_entity:
            continue
        
        # Get entity bounding box
        entity_x = entity.bbox.world_pos.x + MARGIN
        entity_y = entity.bbox.world_pos.y + MARGIN
        entity_w = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        entity_h = (tile_h * entity.bbox.size_in_tiles) - (MARGIN * 2)
        
        # Check if position in front overlaps with entity
        overlap = (front_x < entity_x + entity_w and
                  front_x + check_size > entity_x and
                  front_y < entity_y + entity_h and
                  front_y + check_size > entity_y)
        
        if not overlap:
            continue
        
        # Check Z overlap (hero should be at similar height to interact)
        entity_z = entity.bbox.world_pos.z
        entity_height = entity.bbox.height_in_tiles * tile_h
        hero_height = hero.bbox.height_in_tiles * tile_h
        
        # Allow interaction if hero and entity Z ranges overlap
        z_overlap = (hero_pos.z < entity_z + entity_height and
                    hero_pos.z + hero_height > entity_z)
        
        if z_overlap:
            return entity
    
    return None


def can_place_entity_at_position(hero_z: int,
                                entity: Entity,
                                 x: float,
                                 y: float,
                                 z: float,
                                 other_entities: List[Entity],
                                 heightmap: Heightmap,
                                 tile_h: int) -> bool:
    """Check if an entity can be placed at the given position
    
    Args:
        entity: Entity to place
        x: X position to check
        y: Y position to check
        z: Z position to check
        other_entities: List of other entities to check collision against
        heightmap: The heightmap for terrain checks
        tile_h: Tile height in pixels
        
    Returns:
        True if entity can be placed, False otherwise
    """
    from boundingbox import BoundingBox
    
    # Check if position is in bounds
    tile_x = int(x // tile_h)
    tile_y = int(y // tile_h)
    
    if (tile_x < 0 or tile_y < 0 or
        tile_x >= heightmap.get_width() or
        tile_y >= heightmap.get_height()):
        return False
    
    # Check if terrain is walkable
    cell: Optional[HeightmapCell] = heightmap.get_cell(tile_x, tile_y)
    if not cell or not cell.is_walkable():
        return False
    
    # Check if Z matches terrain height (entity should be on ground)
    terrain_z = cell.height * tile_h
    if terrain_z - hero_z > 32:
        return False
    
    # Create temporary bounding box for collision check
    temp_bbox = BoundingBox(
        Vector3(x, y, z),
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


def get_touching_entities(hero: Hero,
                         entities: List[Entity],
                         tile_h: int) -> List[Entity]:
    """Get all entities currently touching the hero in 3D space
    
    This checks collision at the hero's current position without any movement.
    Useful for detecting enemy attacks, trigger zones, etc.
    
    Args:
        hero: The hero object
        entities: List of entities to check collision against
        tile_h: Tile height in pixels
        
    Returns:
        List of entities currently in contact with the hero
    """
    touching_entities: List[Entity] = []
    
    for entity in entities:
        if entity is hero.grabbed_entity:
            # Skip grabbed entity (it's supposed to be touching)
            continue
        
        if not entity.visible:
            continue
        
        # Check 3D collision
        if check_entity_collision_3d(hero.bbox, entity.bbox, tile_h):
            touching_entities.append(entity)
    
    return touching_entities