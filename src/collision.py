from typing import List, Tuple, Optional
from pygame.math import Vector3
from hero import Hero
from entity import Entity
from heightmap import Heightmap, HeightmapCell

MARGIN: float = 2.0 / 16.0  # 2 pixels = 2/16 tiles


def check_entity_collision_3d(moving_bbox, target_bbox) -> bool:
    """Check if two entities collide in 3D space
    
    All coordinates are in tiles.
    """
    # Calculate bounds in tiles
    me_x = moving_bbox.world_pos.x + MARGIN
    me_y = moving_bbox.world_pos.y + MARGIN
    me_w = moving_bbox.size_in_tiles - (MARGIN * 2)
    me_h = moving_bbox.size_in_tiles - (MARGIN * 2)
    
    te_x = target_bbox.world_pos.x + MARGIN - 12
    te_y = target_bbox.world_pos.y + MARGIN - 12
    te_w = target_bbox.size_in_tiles - (MARGIN * 2)
    te_h = target_bbox.size_in_tiles - (MARGIN * 2)
    
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
    moving_z_height = moving_bbox.height_in_tiles
    target_z_height = target_bbox.height_in_tiles
    
    z_collision = (moving_z < target_z + target_z_height and
                   moving_z + moving_z_height > target_z)
    
    return z_collision


def check_collids_entity(hero: Hero, x: float, y: float, entities: List[Entity]) -> Optional[Entity]:
    """Check if hero collides with any entity at the given position
    
    Args:
        hero: The hero object
        x: X position to check (in tiles)
        y: Y position to check (in tiles)
        entities: List of entities to check collision against
    """
    from boundingbox import BoundingBox
    
    hero_pos = hero.get_world_pos()
    
    # Create temporary bounding box at new position
    temp_bbox = BoundingBox(
        Vector3(x, y, hero_pos.z),
        hero.bbox.height_in_tiles,
        hero.bbox.size_in_tiles
    )
    
    for i, entity in enumerate(entities):
        print(f"  Checking entity {i}: pos={entity.bbox.world_pos}")
        if check_entity_collision_3d(temp_bbox, entity.bbox):
            print(f"  COLLISION FOUND with entity {i}")
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
    touched_entity = check_collids_entity(hero, new_x, new_y, entities)
    if touched_entity is None:
        print(f"  No collision, allowing movement to ({new_x:.3f}, {new_y:.3f})")
        return new_x, new_y, touched_entity
     
    # Collision detected, try to slide along obstacles
    # Try X-only movement
    print("  Trying X-only movement...")
    touched_entity = check_collids_entity(hero, new_x, hero_pos.y, entities)
    if touched_entity is None:
        print(f"  X-only movement allowed to ({new_x:.3f}, {hero_pos.y:.3f})")
        return new_x, hero_pos.y, touched_entity
    
    # Try Y-only movement
    print("  Trying Y-only movement...")
    touched_entity = check_collids_entity(hero, hero_pos.x, new_y, entities)
    if touched_entity is None:
        print(f"  Y-only movement allowed to ({hero_pos.x:.3f}, {new_y:.3f})")
        return hero_pos.x, new_y, touched_entity
    
    print(f"  All movement blocked, staying at ({hero_pos.x:.3f}, {hero_pos.y:.3f})")
    return hero_pos.x, hero_pos.y, touched_entity


def get_entity_top_at_position(entities: List[Entity], check_x: float, check_y: float,
                               check_width: float, check_height: float,
                               hero_z: float) -> Optional[float]:
    """Get the highest entity surface under the given position
    
    Args:
        check_x, check_y: Position in tiles
        check_width, check_height: Size in tiles
        hero_z: Hero's current Z position in tiles
    
    Returns:
        Z position in tiles (or None if no entity found)
    """
    highest_top: Optional[float] = None
    
    for i, entity in enumerate(entities):
        if not entity.solid or not entity.visible:
            continue
        
        # Calculate entity bounds in tiles
        entity_x = entity.bbox.world_pos.x + MARGIN - 12
        entity_y = entity.bbox.world_pos.y + MARGIN - 12
        entity_w = entity.bbox.size_in_tiles - (MARGIN * 2)
        entity_h = entity.bbox.size_in_tiles - (MARGIN * 2)
        
        # Check XY overlap
        xy_overlap = (check_x < entity_x + entity_w and
                     check_x + check_width > entity_x and
                     check_y < entity_y + entity_h and
                     check_y + check_height > entity_y)
        
        if not xy_overlap:
            continue
        
        # Calculate entity top Z position (in tiles)
        entity_top_tiles = entity.bbox.world_pos.z + entity.bbox.height_in_tiles
        
        #print(f"    Entity top Z: {entity_top_tiles:.3f}, checking if <= {hero_z + 0.0625:.3f}")
        
        # Only consider entities below hero
        if entity_top_tiles <= hero_z + 0.0625:  # 1 pixel tolerance = 1/16 tiles
            if highest_top is None or entity_top_tiles > highest_top:
                highest_top = entity_top_tiles
                print(f"    New highest top: {highest_top:.3f}")
    
    return highest_top


def get_entity_hero_is_standing_on(hero: Hero, entities: List[Entity]) -> Optional[Entity]:
    """Get the entity that the hero is currently standing on"""
    hero_pos = hero.get_world_pos()  # In tiles
    
    # Get hero bounding box in tiles
    check_x = hero_pos.x + MARGIN
    check_y = hero_pos.y + MARGIN
    check_width = hero.bbox.size_in_tiles - (MARGIN * 2)
    check_height = hero.bbox.size_in_tiles - (MARGIN * 2)
    
    highest_entity: Optional[Entity] = None
    highest_top: Optional[float] = None
    
    for i, entity in enumerate(entities):
        if not entity.solid or not entity.visible or entity is hero.grabbed_entity:
            continue
        
        # Calculate entity bounds in tiles
        entity_x = entity.bbox.world_pos.x + MARGIN - 12
        entity_y = entity.bbox.world_pos.y + MARGIN - 12
        entity_w = entity.bbox.size_in_tiles - (MARGIN * 2)
        entity_h = entity.bbox.size_in_tiles - (MARGIN * 2)
        
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
                print(f"Hero is standing on {entity.name}")
    
    return highest_entity


def get_position_in_front_of_hero(hero: Hero) -> Tuple[float, float]:
    """Get the position one tile in front of the hero
    
    Returns:
        Tuple of (x, y) position in tiles
    """
    print("=" * 80)
    print("get_position_in_front_of_hero")
    
    hero_pos = hero.get_world_pos()  # In tiles
    print(f"  Hero pos: ({hero_pos.x:.3f}, {hero_pos.y:.3f}), facing: {hero.orientation}")
    
    front_x = hero_pos.x  # In tiles
    front_y = hero_pos.y
    
    if hero.orientation == "UP":
        front_y -= 1.0  # 1 tile
    elif hero.orientation == "DOWN":
        front_y += 1.0
    elif hero.orientation == "LEFT":
        front_x -= 1.0
    elif hero.orientation == "RIGHT":
        front_x += 1.0
    
    print(f"  Position in front: ({front_x:.3f}, {front_y:.3f})")
    return front_x, front_y


def get_entity_in_front_of_hero(hero: Hero, entities: List[Entity]) -> Optional[Entity]:
    """Get the entity directly in front of the hero"""
    print("=" * 80)
    print("get_entity_in_front_of_hero")
    
    front_x, front_y = get_position_in_front_of_hero(hero)  # In tiles
    hero_pos = hero.get_world_pos()  # In tiles
    
    check_size = 0.8  # 0.8 tiles
    
    print(f"  Checking area: ({front_x:.3f}, {front_y:.3f}) size={check_size:.3f}")
    print(f"  Number of entities: {len(entities)}")
    
    for i, entity in enumerate(entities):
        if not entity.visible or entity is hero.grabbed_entity:
            continue
        
        # Calculate entity bounds in tiles
        entity_x = entity.bbox.world_pos.x + MARGIN - 12
        entity_y = entity.bbox.world_pos.y + MARGIN - 12
        entity_w = entity.bbox.size_in_tiles - (MARGIN * 2)
        entity_h = entity.bbox.size_in_tiles - (MARGIN * 2)
        
        # Check if position in front overlaps with entity
        overlap = (front_x < entity_x + entity_w and
                  front_x + check_size > entity_x and
                  front_y < entity_y + entity_h and
                  front_y + check_size > entity_y)
        
        print(f"  Entity {i}: pos={entity.bbox.world_pos}, bounds=({entity_x:.3f}, {entity_y:.3f}, {entity_w:.3f}, {entity_h:.3f}), xy_overlap={overlap}")
        
        if not overlap:
            continue
        
        # Check Z overlap (all in tiles)
        entity_z = entity.bbox.world_pos.z
        entity_height = entity.bbox.height_in_tiles
        hero_height = hero.bbox.height_in_tiles
        
        z_overlap = (hero_pos.z < entity_z + entity_height and
                    hero_pos.z + hero_height > entity_z)
        
        print(f"    Hero Z: {hero_pos.z:.3f}-{hero_pos.z + hero_height:.3f}, Entity Z: {entity_z:.3f}-{entity_z + entity_height:.3f}, z_overlap={z_overlap}")
        
        if z_overlap:
            print(f"  Found entity in front!")
            return entity
    
    print("  No entity in front")
    return None


def can_place_entity_at_position(hero_z: float, entity: Entity, x: float, y: float, z: float,
                                other_entities: List[Entity], heightmap: Heightmap) -> bool:
    """Check if an entity can be placed at the given position
    
    Args:
        hero_z: Hero Z position in tiles
        x, y: Position in tiles
        z: Z position in tiles
    """
    from boundingbox import BoundingBox
    
    # Get tile coordinates
    tile_x = int(x)
    tile_y = int(y)
    
    print(f"  Tile coords: ({tile_x}, {tile_y})")
    
    if (tile_x < 0 or tile_y < 0 or
        tile_x >= heightmap.get_width() or
        tile_y >= heightmap.get_height()):
        print(f"  Out of bounds!")
        return False
    
    cell: Optional[HeightmapCell] = heightmap.get_cell(tile_x, tile_y)
    if not cell or not cell.is_walkable():
        print(f"  Cell not walkable or doesn't exist")
        return False
    
    # Check if Z matches terrain height (cell.height is in tiles)
    terrain_z = cell.height
    print(f"  Terrain Z: {terrain_z:.3f}, height difference from hero: {terrain_z - hero_z:.3f}")
    
    if terrain_z - hero_z > 2.0:  # 2 tiles
        print(f"  Too high relative to hero!")
        return False
    
    # Create temporary bounding box for collision check (all in tiles)
    temp_bbox = BoundingBox(
        Vector3(x, y, z),
        entity.bbox.height_in_tiles,
        entity.bbox.size_in_tiles
    )
    
    # Check collision with other entities
    print(f"  Checking collision with {len(other_entities)} other entities")
    for i, other in enumerate(other_entities):
        if other is entity or not other.solid or not other.visible:
            continue
        
        print(f"    Checking entity {i}: pos={other.bbox.world_pos}")
        if check_entity_collision_3d(temp_bbox, other.bbox):
            print(f"  Collision with entity {i}!")
            return False
    
    print(f"  Can place entity!")
    return True


def update_carried_positions(hero, entities, tile_h, heightmap_left_offset,
                            heightmap_top_offset, camera_x, camera_y, tilemap_height):
    """Move hero/entities that are standing on moving entities"""
    # Check if hero is standing on an entity
    standing_on = get_entity_hero_is_standing_on(hero, entities)
    if standing_on:
        dx, dy, dz = standing_on.get_position_delta()  # Deltas in tiles
        
        if dx != 0 or dy != 0 or dz != 0:
            hero_pos = hero.get_world_pos()  # In tiles
            new_pos = (hero_pos.x + dx, hero_pos.y + dy, hero_pos.z + dz)
            print(f"  Moving hero from {hero_pos} to {new_pos}")
            
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
                    camera_x, camera_y, tilemap_height
                )
    
    # Check each entity standing on other entities
    for i, entity in enumerate(entities):
        entity_pos = entity.get_world_pos()
        check_x = entity_pos.x + MARGIN
        check_y = entity_pos.y + MARGIN
        check_width = entity.bbox.size_in_tiles - (MARGIN * 2)
        check_height = entity.bbox.size_in_tiles - (MARGIN * 2)
        
        standing_on = get_entity_top_at_position(
            [e for e in entities if e is not entity],
            check_x,
            check_y,
            check_width,
            check_height,
            entity_pos.z
        )
        
        if standing_on is not None:
            print(f"  Entity {i} is standing on something at Z={standing_on:.3f}")
            
            for j, other in enumerate(entities):
                if other is entity:
                    continue
                other_pos = other.get_world_pos()  # In tiles
                other_height = other.bbox.height_in_tiles  # In tiles
                # All comparisons in tiles now
                if abs((other_pos.z + other_height) - standing_on) < 0.0625:  # 1 pixel = 1/16 tiles
                    dx, dy, dz = other.get_position_delta()
                    print(f"    Entity {i} is standing on entity {j}, delta: ({dx:.3f}, {dy:.3f}, {dz:.3f})")
                    
                    if dx != 0 or dy != 0 or dz != 0:
                        new_pos = (entity_pos.x + dx, entity_pos.y + dy, entity_pos.z + dz)
                        print(f"    Moving entity {i} from {entity_pos} to {new_pos}")
                        
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


def get_touching_entities(hero: Hero, entities: List[Entity]) -> List[Entity]:
    """Get all entities currently touching the hero in 3D space"""
    touching_entities: List[Entity] = []
    
    for i, entity in enumerate(entities):
        if entity is hero.grabbed_entity:
            continue
        
        if not entity.visible:
            continue
        
        print(f"  Checking entity {i}: pos={entity.bbox.world_pos}")
        if check_entity_collision_3d(hero.bbox, entity.bbox):
            print(f"    Entity {i} is touching!")
            touching_entities.append(entity)
    
    print(f"  Total touching entities: {len(touching_entities)}")
    return touching_entities