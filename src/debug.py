import pygame
from typing import List, Tuple, Optional
from utils import cartesian_to_iso
from boundingbox import BoundingBox

def draw_heightmap(screen: pygame.Surface, heightmap, tile_height: int, camera_x: float, camera_y: float) -> None:
    """Draw the isometric heightmap with semi-transparent fills and wireframe."""

    offset_x = (heightmap.left_offset - 12) * tile_height - 12
    offset_y = (heightmap.top_offset - 11) * tile_height - 12

    # Create a temporary surface for transparency
    temp_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

    for y, row in enumerate(heightmap.cells):
        for x, cell in enumerate(row):

            height = cell.height

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

            # Height-shifted (top face)
            points = [
                (left_x - camera_x,  left_y  - camera_y - height * tile_height),
                (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                (right_x - camera_x, right_y - camera_y - height * tile_height),
                (top_x - camera_x,   top_y   - camera_y - height * tile_height),
            ]

            # Choose color by conditions
            if cell.walkable >= 4:
                # Non-walkable - red
                outline_color = (255, 80, 80)
                fill_color = (255, 80, 80, 80)
            elif height == 0:
                # Ground level - yellow
                outline_color = (255, 255, 120)
                fill_color = (255, 255, 120, 60)
            elif height >= 20:
                # Very high - light red
                outline_color = (255, 120, 120)
                fill_color = (255, 120, 120, 70)
            else:
                # Normal walkable - white/blue
                outline_color = (255, 255, 255)
                fill_color = (200, 200, 255, 50)

            # Draw filled polygon with transparency
            if len(points) >= 3:
                pygame.draw.polygon(temp_surface, fill_color, points)
            
            # Draw outline
            pygame.draw.lines(screen, outline_color, True, points, 1)

            # Draw vertical edges if tile in front or below is lower
            if x < len(heightmap.cells[0]) - 1:
                neighbor_h = heightmap.cells[y][x + 1].height
                if neighbor_h < height:
                    hdiff = neighbor_h - height
                    
                    # Front face points
                    front_points = [
                        (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                        (bottom_x - camera_x, bottom_y - camera_y - neighbor_h * tile_height),
                        (right_x - camera_x, right_y - camera_y - neighbor_h * tile_height),
                        (right_x - camera_x, right_y - camera_y - height * tile_height),
                    ]
                    
                    # Draw filled face
                    face_color = (outline_color[0], outline_color[1], outline_color[2], 40)
                    pygame.draw.polygon(temp_surface, face_color, front_points)
                    
                    # Draw edges
                    pygame.draw.line(screen, outline_color,
                        (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                        (bottom_x - camera_x, bottom_y - camera_y - neighbor_h * tile_height)
                    )
                    pygame.draw.line(screen, outline_color,
                        (right_x - camera_x, right_y - camera_y - height * tile_height),
                        (right_x - camera_x, right_y - camera_y - neighbor_h * tile_height)
                    )

            if y < len(heightmap.cells) - 1:
                neighbor_h = heightmap.cells[y + 1][x].height
                if neighbor_h < height:
                    hdiff = neighbor_h - height
                    
                    # Side face points
                    side_points = [
                        (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                        (bottom_x - camera_x, bottom_y - camera_y - neighbor_h * tile_height),
                        (left_x - camera_x, left_y - camera_y - neighbor_h * tile_height),
                        (left_x - camera_x, left_y - camera_y - height * tile_height),
                    ]
                    
                    # Draw filled face
                    face_color = (outline_color[0], outline_color[1], outline_color[2], 30)
                    pygame.draw.polygon(temp_surface, face_color, side_points)
                    
                    # Draw edge
                    pygame.draw.line(screen, outline_color,
                        (bottom_x - camera_x, bottom_y - camera_y - height * tile_height),
                        (bottom_x - camera_x, bottom_y - camera_y - neighbor_h * tile_height)
                    )
    
    # Blit the transparent surface onto the main screen
    screen.blit(temp_surface, (0, 0))


def draw_boundbox(bbox: BoundingBox, screen: pygame.Surface, tile_height: int, 
                  camera_x: float, camera_y: float, left_offset: int, top_offset: int, 
                  color: Tuple[int, int, int] = (250, 255, 250)) -> None:
    """Draw an isometric bounding box using BoundingBox object.
    
    Args:
        bbox: BoundingBox object to draw
        screen: Pygame surface to draw on
        tile_height: Height of tiles in pixels
        camera_x: Camera X position
        camera_y: Camera Y position
        left_offset: Heightmap left offset
        top_offset: Heightmap top offset
        color: RGB color tuple for the bounding box
        label: Optional text label to draw above the box
    """
    # Get corner positions in isometric screen space
    corners_iso = bbox.get_corners_iso(tile_height, left_offset, top_offset, camera_x, camera_y)
    
    # Get Z positions for top and bottom of bounding box
    z_bottom = bbox.world_pos.z
    z_top = bbox.world_pos.z - bbox.height_in_tiles * tile_height
    # Create points for top rectangle (with Z offset)
    top_points = [
        (corners_iso[0][0], corners_iso[0][1] - z_top),   # left
        (corners_iso[1][0], corners_iso[1][1] - z_top),   # bottom
        (corners_iso[2][0], corners_iso[2][1] - z_top),   # right
        (corners_iso[3][0], corners_iso[3][1] - z_top),   # top
    ]
    
    # Create points for bottom rectangle (with Z offset)
    bottom_points = [
        (corners_iso[0][0], corners_iso[0][1] - z_bottom),   # left
        (corners_iso[1][0], corners_iso[1][1] - z_bottom),   # bottom
        (corners_iso[2][0], corners_iso[2][1] - z_bottom),   # right
        (corners_iso[3][0], corners_iso[3][1] - z_bottom),   # top
    ]
    
    # Draw top rectangle
    pygame.draw.lines(screen, color, True, top_points)
    
    # Draw bottom rectangle
    pygame.draw.lines(screen, color, True, bottom_points)
    
    # Draw vertical edges connecting top and bottom
    for i in range(4):
        pygame.draw.line(screen, color, top_points[i], bottom_points[i], 1)

def draw_label(label: str, color: Tuple[int, int, int], screen: pygame.Surface, 
               draw_coords: bool = False, draw_size: bool = False) -> None:
    font = pygame.font.SysFont("Arial", 12)
    text_surf = font.render(label, True, color)

    # Position label above the top of the box
    label_x = top_points[3][0] + 14
    label_y = top_points[3][1] - 12
    screen.blit(text_surf, (label_x, label_y))
    
    if draw_size:
        # Show size and height properties
        props_text = f"size:{bbox.size_in_tiles:.1f} h:{bbox.height_in_tiles:.1f}"
        props_surf = font.render(props_text, True, color)
        screen.blit(props_surf, (label_x, label_y + 12))

    if draw_coords:
        # Draw coordinates below label
        tile_x = bbox.world_pos.x / tile_height
        tile_y = bbox.world_pos.y / tile_height
        tile_z = bbox.world_pos.z / tile_height
        # Show tile coordinates
        coord_text = f"({tile_x:.1f},{tile_y:.1f},{tile_z:.1f})"
        coord_surf = font.render(coord_text, True, color)
        screen.blit(coord_surf, (label_x, label_y + 24))

def draw_warps(screen: pygame.Surface, warps: List, heightmap, tile_h: int, 
               camera_x: float, camera_y: float, current_room: str) -> None:
    """Draw all warps for debugging"""
    # Precompute offsets
    off_x = (heightmap.left_offset) * tile_h
    off_y = (heightmap.top_offset) * tile_h
    
    def iso_point(wx: float, wy: float, z: float) -> Tuple[float, float]:
        """Convert world Cartesian → isometric pixel coords, accounting for height."""
        ix, iy = cartesian_to_iso(wx - off_x, wy - off_y)
        # Subtract z (height)
        return ix - camera_x, iy - camera_y - z
    
    font = pygame.font.SysFont("Arial", 10)
    
    for warp in warps:
        x = 0
        y = 0
        if warp.room1 == current_room:
            x = warp.x
            y = warp.y
        else:
            x = warp.x2
            y = warp.y2
        
        color = (0, 200, 255)
        
        # Get the height (z) at the warp position
        tile_x = int(x - 12)
        tile_y = int(y - 12)
        
        cell = heightmap.get_cell(tile_x, tile_y)
        z = cell.height * tile_h
        
        # Warp rectangle corners (already in tile coordinates from Tiled)
        p1 = iso_point(x * tile_h, y * tile_h, z)
        p2 = iso_point(x * tile_h + warp.width * tile_h, y * tile_h, z)
        p3 = iso_point(x * tile_h + warp.width * tile_h, y * tile_h + warp.height * tile_h, z)
        p4 = iso_point(x * tile_h, y * tile_h + warp.height * tile_h, z)
        
        # Draw warp zone rectangle
        pygame.draw.lines(screen, color, True, [p1, p2, p3, p4])
        
        # Main label
        label = f"{warp.room1}→{warp.room2}"
        text_surf = font.render(label, True, color)
        screen.blit(text_surf, (p1[0] + 2, p1[1] - 12))
        
        # Position and size info
        pos_label = f"({x},{y}) {warp.width}x{warp.height}"
        pos_surf = font.render(pos_label, True, (150, 150, 255))
        screen.blit(pos_surf, (p1[0] + 2, p1[1] + 2))