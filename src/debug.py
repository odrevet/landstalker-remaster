import pygame
from typing import List, Tuple, Optional
from utils import cartesian_to_iso
from boundingbox import BoundingBox

import pygame
from typing import Tuple, Optional
from pygame.math import Vector2


import pygame
from typing import Tuple, Optional
from utils import cartesian_to_iso


def draw_heightmap_cell(surface: pygame.Surface, x: int, y: int, z: int,
                        tile_width: int, tile_height: int,
                        cell_props: int, cell_type: int,
                        draw_outline: bool = False,
                        wall_colour: Tuple[int, int, int] = (255, 255, 255),
                        opacity: int = 128) -> None:
    """
    Draw a single heightmap cell as a diamond shape.
    
    Args:
        surface: pygame Surface to draw on
        x: X pixel position (center of diamond)
        y: Y pixel position (center of diamond)
        z: Height value (affects vertical offset)
        tile_width: Width of a tile (typically 8)
        tile_height: Height of a tile (typically 8)
        cell_props: Cell properties (walkability, etc.)
        cell_type: Cell type value
        draw_outline: Whether to draw colored outline
        wall_colour: RGB color for the outline
        opacity: Alpha opacity (0-255)
    """
    # Calculate the diamond points
    # A diamond is drawn as 4 triangular faces in isometric view
    half_w = tile_width
    half_h = tile_height
    
    # Diamond vertices (top, right, bottom, left)
    points = [
        (x, y - half_h),           # Top
        (x + half_w, y),           # Right
        (x, y + half_h),           # Bottom
        (x - half_w, y)            # Left
    ]
    
    # Determine fill color based on cell properties
    # Cell props: 0x04 = completely restricted (don't draw)
    # Lower values = more walkable
    if cell_props == 0x00:
        # Fully walkable - light green
        fill_color = (100, 255, 100)
    elif cell_props == 0x01:
        # Partially walkable - yellow
        fill_color = (255, 255, 100)
    elif cell_props == 0x02:
        # Less walkable - orange
        fill_color = (255, 165, 100)
    elif cell_props == 0x03:
        # Nearly blocked - red
        fill_color = (255, 100, 100)
    else:
        # Blocked or unknown - dark gray
        fill_color = (100, 100, 100)
    
    # Create a temporary surface with alpha for blending
    temp_surface = pygame.Surface((half_w * 2, half_h * 2), pygame.SRCALPHA)
    temp_x = x - (x - half_w)
    temp_y = y - (y - half_h)
    
    # Draw the diamond with the fill color
    temp_points = [
        (temp_x, temp_y - half_h),
        (temp_x + half_w, temp_y),
        (temp_x, temp_y + half_h),
        (temp_x - half_w, temp_y)
    ]
    pygame.draw.polygon(temp_surface, (*fill_color, opacity), temp_points)
    
    # Draw outline
    if draw_outline:
        pygame.draw.polygon(temp_surface, (*wall_colour, 255), temp_points, 2)
    else:
        # Draw subtle white outline for all cells
        pygame.draw.polygon(temp_surface, (255, 255, 255, 128), temp_points, 1)
    
    # Draw height indicator - vertical line from center going up
    if z > 0:
        height_offset = z * tile_height
        pygame.draw.line(temp_surface, (255, 255, 255, 200),
                        (temp_x, temp_y),
                        (temp_x, temp_y - height_offset), 2)
        # Draw a small circle at the top to indicate height
        pygame.draw.circle(temp_surface, (255, 200, 0, 255),
                          (temp_x, temp_y - height_offset), 3)
    
    # Blit to main surface
    surface.blit(temp_surface, (x - half_w, y - half_h))


def draw_heightmap_visualization(surface: pygame.Surface,
                                 heightmap,  # Heightmap object
                                 room,       # Room object
                                 camera_x: float,
                                 camera_y: float,
                                 opacity: int = 128) -> None:
    """
    Draw the entire heightmap visualization over the tilemap.
    
    Args:
        surface: pygame Surface to draw on
        heightmap: Heightmap object with cells
        room: Room object with map dimensions
        camera_x: Camera X offset
        camera_y: Camera Y offset
        opacity: Alpha opacity for the heightmap (0-255)
    """
    if not heightmap.cells or not room.data:
        return
    
    tile_width = 8
    tile_height = 8
    
    # Iterate through all heightmap cells
    for y in range(heightmap.get_height()):
        for x in range(heightmap.get_width()):
            cell = heightmap.get_cell(x, y)
            if cell is None:
                continue
            
            # Only draw cells that are not completely restricted
            # or have height > 0
            if cell.height > 0 or cell.walkable != 0x04:
                # Convert heightmap position to isometric pixel coordinates
                # Using the same formula as in C++: Iso3DToPixel
                # Note: C++ adds 12 to x,y to center the heightmap
                iso_x = x + 12
                iso_y = y + 12
                z = cell.height
                
                # Apply the Iso3D to Pixel conversion
                # From C++:
                # int xx = iso.x - GetLeft();
                # int yy = iso.y - GetTop();
                # int ix = (xx - yy + (GetHeight() - 1)) * 2 + GetLeft();
                # int iy = (xx + yy - iso.z * 2) + GetTop();
                # return Point2D{ ix * tile_width, iy * tile_height };
                
                left = heightmap.left_offset
                top = heightmap.top_offset
                map_height = room.data.height
                
                xx = iso_x - left
                yy = iso_y - top
                ix = (xx - yy + (map_height - 1)) * 2 + left
                iy = (xx + yy - z * 2) + top
                
                pixel_x = ix * tile_width
                pixel_y = iy * tile_height
                
                # Adjust for camera
                screen_x = pixel_x - camera_x
                screen_y = pixel_y - camera_y
                
                # Determine if we should draw an outline
                # (For doors, swaps, etc. - simplified here)
                draw_outline = False
                wall_colour = (255, 255, 255)
                
                # Draw the cell
                draw_heightmap_cell(
                    surface,
                    int(screen_x),
                    int(screen_y),
                    z,
                    tile_width,
                    tile_height,
                    cell.walkable,
                    0,  # cell_type (not used yet)
                    draw_outline,
                    wall_colour,
                    opacity
                )


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
    z_bottom = bbox.world_pos.z - 32
    z_top = bbox.world_pos.z - bbox.height_in_tiles * tile_height - 32
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