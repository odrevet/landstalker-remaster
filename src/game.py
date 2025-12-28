from pygame.math import Vector3
import sys
import os
import argparse
import math
import array

from typing import List, Tuple, Optional, Callable
import yaml
import pygame
import pygame_gui
from pygame_gui.elements.ui_text_box import UITextBox
from hero import Hero
from utils import *
from room import Room
from heightmap import Heightmap, HeightmapCell
from debug import draw_heightmap, draw_warps, draw_boundbox
from collision import (resolve_entity_collision, get_entity_top_at_position, check_collids_entity, get_entity_hero_is_standing_on, 
                      get_entity_in_front_of_hero, can_place_entity_at_position, get_position_in_front_of_hero, get_touching_entities,
                      update_carried_positions, check_entity_collision_3d)
from script_commands import run_entity_script
from menu_screen import MenuScreen

# Constants
CAMERA_SPEED: int = 5
GRAVITY: float = 3.0
HERO_SPEED: float = 2.00
HERO_MAX_JUMP: int = 24
FPS: int = 60

class Game:
    def __init__(self, args: argparse.Namespace) -> None:
        pygame.init()
        pygame.mixer.init()
        
        # Store display configuration
        self.is_fullscreen: bool = args.fullscreen
        self.is_resizable: bool = args.resizable
        self.display_scale: int = args.scale
        
        # Display resolution (internal rendering resolution) - controls zoom/view
        self.display_width: int = args.display_width
        self.display_height: int = args.display_height
        
        # Base resolution (for backward compatibility with scaling calculations)
        self.base_width: int = self.display_width
        self.base_height: int = self.display_height
        
        # Window resolution
        self.window_width: int = args.width * self.display_scale
        self.window_height: int = args.height * self.display_scale
        
        # Display setup
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            # Get actual fullscreen resolution
            info = pygame.display.Info()
            self.window_width = info.current_w
            self.window_height = info.current_h
        elif self.is_resizable:
            self.screen = pygame.display.set_mode(
                (self.window_width, self.window_height), 
                pygame.RESIZABLE
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.window_width, self.window_height)
            )
        
        # Surface for rendering (at display resolution for zoom control)
        self.surface: pygame.Surface = pygame.Surface(
            (self.display_width, self.display_height)
        )
        
        pygame.display.set_caption("LandStalker")
        
        # Calculate initial scaling
        self._update_scaling()
        
        # Game state
        self.room_number: int = args.room
        self.debug_mode: bool = args.debug
        self.display_dialog = False
        self.camera_x: float = 0
        self.camera_y: float = 0
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.main_scripts: dict = self.load_main_scripts("data/script.yaml")
        self.compressed_strings: list[str] = self.load_compressed_strings("data/compressed_strings.txt")

        # Dialog typing effect variables
        self.dialog_full_text: str = ""           # Full text to display
        self.dialog_current_text: str = ""        # Currently displayed text
        self.dialog_char_index: int = 0           # Current character position
        self.dialog_char_timer: float = 0.0       # Timer for next character
        self.dialog_char_delay: float = 0.05      # Delay between characters (seconds)
        self.dialog_finished: bool = False        # Whether typing is complete

        # Generate dialog bip sound procedurally
        self.dialog_bip_base_frequency = 800  # Base frequency in Hz
        self.dialog_bip_pitch = 1.0  # Pitch multiplier (1.0 = normal, 0.5 = lower, 2.0 = higher)
        self.dialog_bip_sound = self.generate_bip_sound(self.dialog_bip_base_frequency)
        self.dialog_bip_sound.set_volume(0.3)  # Adjust volume as needed

        # Debug flags
        self.is_height_map_displayed: bool = False
        self.is_boundbox_displayed: bool = False
        self.is_warps_displayed: bool = False
        self.camera_locked: bool = True  # Camera follows hero by default
        
        self.prev_hero_tile_x: int = -1
        self.prev_hero_tile_y: int = -1

        # Zoom control
        self.original_display_width: int = self.display_width
        self.original_display_height: int = self.display_height
        self.zoom_levels: List[float] = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
        self.current_zoom_index: int = self.zoom_levels.index(1.0)  # Start at 1.0x

        # Key state tracking for toggles
        self.prev_keys: dict = {}
        
        # GUI setup
        # HUD
        self.manager: pygame_gui.UIManager = pygame_gui.UIManager(
            (self.display_width, self.display_height), "ui.json"
        )
        self.hud_textbox: UITextBox = UITextBox(
            "",
            pygame.Rect((0, 0), (self.display_width, 36)),
            manager=self.manager,
            object_id="#hud_textbox",
        )
        self.coord_label: pygame_gui.elements.UILabel = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 2), (-1, -1)),
            text="",
            manager=self.manager
        )

        # Dialog
        self.dialog_textbox: UITextBox = UITextBox(
            "",
            pygame.Rect((0, self.display_height - 60), (self.display_width, 58)),
            manager=self.manager,
            object_id="#dialog_textbox",
        )
        self.coord_dialog: pygame_gui.elements.UILabel = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, self.display_height - 60), (-1, -1)),
            text="",
            manager=self.manager
        )

        self.menu_screen = MenuScreen(self.display_width, self.display_height)
        self.menu_active = False
        
        self.dialog_textbox.hide()
        self.coord_dialog.hide()
        
        # Fade (warp) variables
        self.fade_alpha: int = 0                # 0..255
        self.fade_mode: Optional[str] = None    # "out", "in", or None
        self.fade_speed: float = 600.0          # alpha units per second
        self.fade_callback: Optional[Callable[[], None]] = None
        self.fade_surface: pygame.Surface = pygame.Surface(
            (self.display_width, self.display_height)
        )
        self.fade_surface.fill((0, 0, 0))
        self.fade_surface.set_alpha(0)

        # Load initial room
        self.room: Room = Room()
        self.room.load(self.room_number)
        self.play_room_bgm()

        # Create hero
        self.hero: Hero = Hero(args.x, args.y, args.z)
        
        # Validate and fix hero spawn position
        self.fix_hero_spawn_position()
        
        self.check_initial_entity_collision()

        # Center camera on hero initially
        self.center_camera_on_hero()
    
    def generate_bip_sound(self, base_frequency: float, duration: float = 0.05) -> pygame.mixer.Sound:
        """Generate a procedural bip sound with adjustable pitch
        Args:
            base_frequency: Base frequency in Hz (e.g., 800)
            duration: Duration of the sound in seconds (default: 0.05)
        Returns:
            pygame.mixer.Sound object
        """       
        sample_rate = 22050
        frequency = base_frequency * self.dialog_bip_pitch
        
        # Calculate number of samples
        num_samples = int(sample_rate * duration)
        
        # Generate wave samples
        samples = array.array('h')  # 'h' = signed short (16-bit)
        
        for i in range(num_samples):
            t = i / sample_rate
            
            # Exponential envelope to avoid clicks
            envelope = math.exp(-t * 20)
            
            # Generate sine wave with envelope
            wave_value = math.sin(2 * math.pi * frequency * t) * envelope
            
            # Convert to 16-bit PCM format
            sample = int(wave_value * 32767)
            
            # Add stereo samples (left and right channels)
            samples.append(sample)
            samples.append(sample)
        
        # Create pygame Sound from array
        sound = pygame.mixer.Sound(buffer=samples)
        
        return sound
    
    def set_dialog_bip_pitch(self, pitch: float) -> None:
        """Set the pitch of the dialog bip sound
        
        Args:
            pitch: Pitch multiplier (1.0 = normal, 0.5 = lower, 2.0 = higher)
        """
        self.dialog_bip_pitch = pitch
        # Regenerate the sound with new pitch
        self.dialog_bip_sound = self.generate_bip_sound(self.dialog_bip_base_frequency)
        self.dialog_bip_sound.set_volume(0.3)
    
    def play_room_bgm(self):
        bgm_name = self.room.room_properties["RoomBGM"]
        bgm_path = os.path.join("data", "musics", f"{bgm_name}.mp3")

        if not os.path.isfile(bgm_path):
            print(f"BGM file not found: {bgm_path}")
            return

        # Stop current music if any
        pygame.mixer.music.stop()

        # Load and play
        pygame.mixer.music.load(bgm_path)
        pygame.mixer.music.play(-1)  # -1 = loop forever
        print(f"Playing BGM: {bgm_path}")

    def on_entity_collids(self, entity):
        print(f"On entity collids {entity.name} {entity.behaviour}")
        run_entity_script(entity, entity.behaviour)

    def fix_hero_spawn_position(self) -> None:
        """Fix hero position if spawned in invalid location"""
        tile_h: int = self.room.data.tileheight
        
        # Check if hero is out of bounds
        hero_pos = self.hero.get_world_pos()
        hero_tile_x: int = int(hero_pos.x // tile_h)
        hero_tile_y: int = int(hero_pos.y // tile_h)
        
        # If out of bounds or on unwalkable tile, find first walkable tile
        if (hero_tile_x < 0 or hero_tile_y < 0 or
            hero_tile_x >= self.room.heightmap.get_width() or
            hero_tile_y >= self.room.heightmap.get_height() or
            not self.room.heightmap.get_cell(hero_tile_x, hero_tile_y) or
            not self.room.heightmap.get_cell(hero_tile_x, hero_tile_y).is_walkable()):
            
            # Find first walkable tile
            for y in range(self.room.heightmap.get_height()):
                for x in range(self.room.heightmap.get_width()):
                    cell: Optional[HeightmapCell] = self.room.heightmap.get_cell(x, y)
                    if cell and cell.is_walkable():
                        # Move hero to center of this tile
                        new_x: float = x * tile_h + tile_h // 2
                        new_y: float = y * tile_h + tile_h // 2
                        new_z: float = cell.height * tile_h
                        self.hero.set_world_pos(
                            new_x, new_y, new_z,
                            self.room.heightmap.left_offset,
                            self.room.heightmap.top_offset,
                            self.camera_x,
                            self.camera_y
                        )
                        print(f"Hero spawned at invalid position, moved to first walkable tile: ({x}, {y})")
                        return
        
        # Hero is in bounds, check if Z is correct
        cell: Optional[HeightmapCell] = self.room.heightmap.get_cell(hero_tile_x, hero_tile_y)
        if cell:
            ground_height: float = cell.height * tile_h
            # If hero is below ground, place on ground
            if hero_pos.z < ground_height:
                self.hero.set_world_pos(
                    hero_pos.x, hero_pos.y, ground_height,
                    self.room.heightmap.left_offset,
                    self.room.heightmap.top_offset,
                    self.camera_x,
                    self.camera_y
                )
                print(f"Hero was below ground, moved to ground level: Z={ground_height}")
    
    def center_camera_on_hero(self) -> None:
        """Center the camera on the hero's position"""
        self.hero.update_camera(
            self.room.heightmap.left_offset,
            self.room.heightmap.top_offset,
            0,  # Use 0,0 for camera to get absolute screen position
            0
        )
        
        # Center camera on hero
        self.camera_x = self.hero._screen_pos.x - self.display_width // 2
        self.camera_y = self.hero._screen_pos.y - self.display_height // 2
        
        # Update hero screen position with new camera
        self.hero.update_camera(
            self.room.heightmap.left_offset,
            self.room.heightmap.top_offset,
            self.camera_x,
            self.camera_y
        )
    
    def is_key_just_pressed(self, key: int, keys: pygame.key.ScancodeWrapper) -> bool:
        """Check if a key was just pressed (not held)"""
        was_pressed: bool = self.prev_keys.get(key, False)
        is_pressed: bool = keys[key]
        return is_pressed and not was_pressed
    
    def handle_events(self) -> bool:
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.VIDEORESIZE:
                self.handle_window_resize(event)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    # Toggle fullscreen
                    self.toggle_fullscreen()
                elif event.key == pygame.K_RETURN and not self.display_dialog:
                    # Toggle menu (only if not in dialog)
                    # Use key-just-pressed check to prevent double-trigger
                    if not self.prev_keys.get(pygame.K_RETURN, False):
                        self.menu_active = not self.menu_active
                elif event.key == pygame.K_b and not self.display_dialog:
                    # Toggle menu with B key (only if not in dialog)
                    if not self.prev_keys.get(pygame.K_b, False):
                        self.menu_active = not self.menu_active
            
            # Process events for appropriate manager
            if self.menu_active:
                self.menu_screen.process_events(event)
            else:
                self.manager.process_events(event)
            
            self.manager.process_events(event)
        
        return True
    
    def handle_camera_movement(self, keys: pygame.key.ScancodeWrapper) -> None:
        """Handle manual camera movement with Shift + arrow keys (unlocks camera)"""
        if not keys[pygame.K_LSHIFT]:
            return
        
        # Manual camera control unlocks the camera
        self.camera_locked = False
        
        moved: bool = False
        if keys[pygame.K_LEFT]:
            self.camera_x -= CAMERA_SPEED
            moved = True
        if keys[pygame.K_RIGHT]:
            self.camera_x += CAMERA_SPEED
            moved = True
        if keys[pygame.K_UP]:
            self.camera_y -= CAMERA_SPEED
            moved = True
        if keys[pygame.K_DOWN]:
            self.camera_y += CAMERA_SPEED
            moved = True
        
        if moved:
            self.hero.update_camera(
                self.room.heightmap.left_offset,
                self.room.heightmap.top_offset,
                self.camera_x,
                self.camera_y
            )
    
    def start_fade(self, callback: Callable[[], None]) -> None:
        """Begin fade-out. Callback runs at full black, then auto fade-in."""
        # Prevent re-triggering while a fade is active
        if self.fade_mode is not None:
            return
        self.fade_mode = "out"
        self.fade_alpha = 0
        self.fade_callback = callback
        # Lock camera / input while fading
        self.camera_locked = True
    
    def update_fade(self, dt: float) -> None:
        """Update fade alpha using delta time (seconds)."""
        if self.fade_mode is None:
            return

        change = self.fade_speed * dt
        if self.fade_mode == "out":
            self.fade_alpha = min(255, int(self.fade_alpha + change))
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                # run callback at full black
                if self.fade_callback:
                    cb = self.fade_callback
                    self.fade_callback = None
                    # execute warp / room-change while screen is black
                    cb()
                # start fading in
                self.fade_mode = "in"
        elif self.fade_mode == "in":
            self.fade_alpha = max(0, int(self.fade_alpha - change))
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fade_mode = None
        self.fade_surface.set_alpha(self.fade_alpha)
    
    def _update_scaling(self) -> None:
        """Calculate optimal scaling to fit the window while maintaining aspect ratio."""
        window_width, window_height = self.screen.get_size()
        
        # Calculate scale factors for both dimensions
        scale_x = window_width / self.base_width
        scale_y = window_height / self.base_height
        
        # Use the smaller scale to maintain aspect ratio
        self.scale = min(scale_x, scale_y)
        
        # Calculate scaled dimensions
        self.scaled_width = int(self.base_width * self.scale)
        self.scaled_height = int(self.base_height * self.scale)
        
        # Calculate offsets to center the game
        self.offset_x = (window_width - self.scaled_width) // 2
        self.offset_y = (window_height - self.scaled_height) // 2
    
    def handle_window_resize(self, event: pygame.event.Event) -> None:
        """Handle window resize events."""
        if event.type == pygame.VIDEORESIZE:
            if not self.is_fullscreen:
                self.window_width = event.w
                self.window_height = event.h
                self._update_scaling()
    
    def toggle_fullscreen(self) -> None:
        """Toggle between fullscreen and windowed mode."""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            self.screen = pygame.display.set_mode(
                (self.window_width, self.window_height),
                pygame.RESIZABLE if self.is_resizable else 0
            )
        
        self._update_scaling()
    
    def render_to_screen(self) -> None:
        """Render the game surface to the screen with proper scaling."""
        # Fill screen with black bars if needed
        self.screen.fill((0, 0, 0))
        
        # Scale the surface and blit to screen
        scaled_surface = pygame.transform.scale(
            self.surface, 
            (self.scaled_width, self.scaled_height)
        )
        self.screen.blit(scaled_surface, (self.offset_x, self.offset_y))
        
        pygame.display.flip()

    def check_warp_collision(self) -> bool:
        """Check if hero is colliding with any warp and handle room transition."""
        tile_h: int = self.room.data.tileheight
        
        # Get hero's bounding box using helper function
        hero_x, hero_y, hero_width, hero_height = self.hero.get_bounding_box(tile_h)
        
        # Calculate current tile (using center of hero's bounding box)
        current_tile_x: int = int((hero_x + hero_width // 2) // tile_h)
        current_tile_y: int = int((hero_y + hero_height // 2) // tile_h)
        
        # Only check warps if hero has moved to a different tile
        if (current_tile_x == self.prev_hero_tile_x and 
            current_tile_y == self.prev_hero_tile_y):
            return False
        
        # Update previous tile position (pre-emptively to avoid re-trigger while fading)
        self.prev_hero_tile_x = current_tile_x
        self.prev_hero_tile_y = current_tile_y
        
        for warp in self.room.warps:
            if warp.check_collision(hero_x, hero_y, hero_width, hero_height, tile_h, self.room.room_number, self.room.heightmap):
                current_room_number = self.room_number
                target_room: int = warp.get_target_room(self.room_number)

                
                if target_room != self.room_number:
                    # define warp callback to execute while screen is black
                    def do_warp():
                        # PATCH FIXEME disable warp from 168 to 167
                        print(f"{current_room_number} {target_room}")
                        if current_room_number == 168 and target_room == 167:
                            print("raft: skip warp back to 167")
                            return False

                        # PATCH FIXEME disable warp from 169 to 168
                        if current_room_number == 169 and target_room == 168:
                            print("raft: skip warp back to 168")
                            return False

                        self.room_number = target_room
                        current_bgm = self.room.room_properties["RoomBGM"]
                        self.room.load(self.room_number)
                        self.hero.release_entity()
                        if current_bgm != self.room.room_properties["RoomBGM"]:
                            self.play_room_bgm()

                        dest_tile_x, dest_tile_y = warp.get_destination(self.room_number, self.room.heightmap)
                        dest_cell: Optional[HeightmapCell] = self.room.heightmap.get_cell(dest_tile_x, dest_tile_y)
                        dest_tile_z: int = dest_cell.height if dest_cell else 0

                        # PATCH FIXEME Adjust defination in raft sequance
                        if self.room_number == 168 or self.room_number == 169:
                            print("Warp: adjust warp")
                            dest_tile_x -= 1
                            dest_tile_y += 1

                        self.hero.set_world_pos(
                            dest_tile_x * tile_h, dest_tile_y * tile_h, dest_tile_z * tile_h,
                            self.room.heightmap.left_offset,
                            self.room.heightmap.top_offset,
                            self.camera_x,
                            self.camera_y
                        )

                        # Center camera on hero in new room
                        self.camera_locked = True
                        self.center_camera_on_hero()

                        # Reset previous tile tracking after warp to prevent immediate re-warp
                        self.prev_hero_tile_x = dest_tile_x
                        self.prev_hero_tile_y = dest_tile_y

                        self.check_hero_spawn_on_entity()
                        self.check_initial_entity_collision()

                    # start fade which will call do_warp at full-black
                    self.start_fade(do_warp)
                    return True
        
        return False
    
    def check_fall(self) -> bool:
        """Check if hero is falling and handle room transition"""
        tile_h: int = self.room.data.tileheight
        
        if self.hero.get_world_pos().z == 0 and self.room.room_properties["WarpFallDestination"] != 65535:
            target = self.room.room_properties["WarpFallDestination"]
            print(f"falling ! {target}")

            def do_fall_warp():
                self.room_number = target
                current_bgm = self.room.room_properties["RoomBGM"]
                self.room.load(self.room_number)
                self.hero.release_entity()
                if current_bgm != self.room.room_properties["RoomBGM"]:
                    self.play_room_bgm()
                self.camera_locked = True
                self.center_camera_on_hero()

            self.start_fade(do_fall_warp)
            self.hero._world_pos.z =  self.room.data.properties['RoomZEnd'] * tile_h

        return False

    def apply_gravity(self) -> None:
        """Apply gravity to hero using bounding box corners, considering both terrain and entities"""
        tile_h: int = self.room.data.tileheight
        
        # Get hero's foot height and bounding box
        hero_pos = self.hero.get_world_pos()
        height_at_foot: float = hero_pos.z
        corners = self.hero.get_bbox_corners_world(tile_h)
        hero_bbox = self.hero.get_bounding_box(tile_h)
        
        # Get tile coordinates for each corner
        # corners are: (left, bottom, right, top)
        left_x: int = int(corners[0][0] // tile_h)
        left_y: int = int(corners[0][1] // tile_h)
        bottom_x: int = int(corners[1][0] // tile_h)
        bottom_y: int = int(corners[1][1] // tile_h)
        right_x: int = int(corners[2][0] // tile_h)
        right_y: int = int(corners[2][1] // tile_h)
        top_x: int = int(corners[3][0] // tile_h)
        top_y: int = int(corners[3][1] // tile_h)
        
        # Get map dimensions for bounds checking
        map_width: int = self.room.heightmap.get_width()
        map_height: int = self.room.heightmap.get_height()
        
        # Clamp coordinates to valid range
        left_x = max(0, min(left_x, map_width - 1))
        left_y = max(0, min(left_y, map_height - 1))
        bottom_x = max(0, min(bottom_x, map_width - 1))
        bottom_y = max(0, min(bottom_y, map_height - 1))
        right_x = max(0, min(right_x, map_width - 1))
        right_y = max(0, min(right_y, map_height - 1))
        top_x = max(0, min(top_x, map_width - 1))
        top_y = max(0, min(top_y, map_height - 1))
        
        # Check if hero is above ground
        if not self.hero.is_jumping:
            cells = self.room.heightmap.cells
            
            # Find the highest ground level under the hero (terrain)
            max_ground_height: float = max(
                cells[top_y][top_x].height * tile_h,
                cells[bottom_y][bottom_x].height * tile_h,
                cells[right_y][right_x].height * tile_h,
                cells[left_y][left_x].height * tile_h
            )
            
            # Check for entity surfaces below the hero (excluding grabbed entity)
            hero_x, hero_y, hero_w, hero_h = hero_bbox
            entities_to_check = [e for e in self.room.entities 
                               if e is not self.hero.grabbed_entity]
            

            entity_standing_on = get_entity_hero_is_standing_on(
                                self.hero,
                                entities_to_check,
                                tile_h)
            if entity_standing_on is not None:
                self.on_entity_collids(entity_standing_on)

            entity_top = get_entity_top_at_position(
                entities_to_check,
                hero_x,
                hero_y,
                hero_w,
                hero_h,
                height_at_foot,
                tile_h
            )
            
            # Use the highest surface (terrain or entity)
            max_surface_height: float = max_ground_height
            if entity_top is not None:
                max_surface_height = max(max_ground_height, entity_top)
            
            # Check if hero is above the highest surface
            if max_surface_height < height_at_foot:
                # Hero is in the air, apply gravity
                new_z: float = hero_pos.z - GRAVITY
                
                # Check if gravity would push hero below surface
                if new_z <= max_surface_height:
                    # Snap to surface level
                    new_z = max_surface_height
                    self.hero.touch_ground = True
                else:
                    # Still falling
                    self.hero.touch_ground = False
                
                self.hero.set_world_pos(
                    hero_pos.x, hero_pos.y, new_z,
                    self.room.heightmap.left_offset,
                    self.room.heightmap.top_offset,
                    self.camera_x,
                    self.camera_y
                )
                
                # Update grabbed entity position if carrying something
                if self.hero.is_grabbing:
                    self.hero.update_grabbed_entity_position(
                        self.room.heightmap.left_offset,
                        self.room.heightmap.top_offset,
                        self.camera_x,
                        self.camera_y,
                        tile_h
                    )
                
                if self.camera_locked:
                    self.center_camera_on_hero()
            else:
                # Hero is on or below surface, snap to surface
                correct_z: float = max_surface_height
                
                if hero_pos.z != correct_z:
                    self.hero.set_world_pos(
                        hero_pos.x, hero_pos.y, correct_z,
                        self.room.heightmap.left_offset,
                        self.room.heightmap.top_offset,
                        self.camera_x,
                        self.camera_y
                    )
                    
                    # Update grabbed entity position if carrying something
                    if self.hero.is_grabbing:
                        self.hero.update_grabbed_entity_position(
                            self.room.heightmap.left_offset,
                            self.room.heightmap.top_offset,
                            self.camera_x,
                            self.camera_y,
                            tile_h
                        )
                    
                    if self.camera_locked:
                        self.center_camera_on_hero()
                
                self.hero.touch_ground = True
    
    def can_move_to(self, next_x: float, next_y: float, check_cells: List[Tuple[int, int]]) -> bool:
        """Check if hero can move to the given position (heightmap check only)"""
        tile_h: int = self.room.data.tileheight
        height_at_foot: float = self.hero.get_world_pos().z
        
        for cell_x, cell_y in check_cells:
            cell: Optional[HeightmapCell] = self.room.heightmap.get_cell(cell_x, cell_y)
            if not cell or not cell.is_walkable():
                return False
            if cell.height * tile_h > height_at_foot:
                return False
        
        return True
    
    def handle_hero_movement(self, keys: pygame.key.ScancodeWrapper) -> None:
            """Handle hero movement using bounding box helpers with 3D entity collision"""
            if keys[pygame.K_LSHIFT]:  # Camera mode
                return
            
            # Check if any movement key is pressed (for animation)
            is_moving: bool = keys[pygame.K_LEFT] or keys[pygame.K_RIGHT] or keys[pygame.K_UP] or keys[pygame.K_DOWN]
            
            # Update facing direction based on key presses (even if blocked)
            if keys[pygame.K_LEFT]:
                self.hero.facing_direction = "LEFT"
            elif keys[pygame.K_RIGHT]:
                self.hero.facing_direction = "RIGHT"
            elif keys[pygame.K_UP]:
                self.hero.facing_direction = "UP"
            elif keys[pygame.K_DOWN]:
                self.hero.facing_direction = "DOWN"
            
            # Re-lock camera when hero moves
            if is_moving:
                self.camera_locked = True
            
            hero_pos = self.hero.get_world_pos()
            tile_h: int = self.room.data.tileheight
            moved: bool = False
            
            # Get current bounding box corners
            corners = self.hero.get_bbox_corners_world(tile_h)
            # corners are: (left, bottom, right, top)
            
            new_x: float = hero_pos.x
            new_y: float = hero_pos.y
            
            if keys[pygame.K_LEFT]:
                next_x: float = hero_pos.x - HERO_SPEED
                
                # Calculate new corner positions after movement
                new_top_x: int = int((corners[3][0] - HERO_SPEED) // tile_h)
                new_top_y: int = int(corners[3][1] // tile_h)
                new_left_x: int = int((corners[0][0] - HERO_SPEED) // tile_h)
                new_left_y: int = int(corners[0][1] // tile_h)
                
                if next_x > 0 and self.can_move_to(next_x, hero_pos.y, [
                    (new_top_x, new_top_y), (new_left_x, new_left_y)
                ]):
                    new_x = next_x
                    moved = True
            
            elif keys[pygame.K_RIGHT]:
                next_x: float = hero_pos.x + HERO_SPEED
                
                # Calculate new corner positions after movement
                new_right_x: int = int((corners[2][0] + HERO_SPEED) // tile_h)
                new_right_y: int = int(corners[2][1] // tile_h)
                new_bottom_x: int = int((corners[1][0] + HERO_SPEED) // tile_h)
                new_bottom_y: int = int((corners[1][1]) // tile_h)
                
                if new_right_x < self.room.heightmap.get_width() and self.can_move_to(
                    next_x, hero_pos.y, [(new_right_x, new_right_y), (new_bottom_x, new_bottom_y)]
                ):
                    new_x = next_x
                    moved = True
            
            elif keys[pygame.K_UP]:
                next_y: float = hero_pos.y - HERO_SPEED
                
                # Calculate new corner positions after movement
                new_top_x: int = int(corners[3][0] // tile_h)
                new_top_y: int = int((corners[3][1] - HERO_SPEED) // tile_h)
                new_right_x: int = int(corners[2][0] // tile_h)
                new_right_y: int = int((corners[2][1] - HERO_SPEED) // tile_h)
                
                if next_y > 0 and self.can_move_to(hero_pos.x, next_y, [
                    (new_top_x, new_top_y), (new_right_x, new_right_y)
                ]):
                    new_y = next_y
                    moved = True
            
            elif keys[pygame.K_DOWN]:
                next_y: float = hero_pos.y + HERO_SPEED
                
                # Calculate new corner positions after movement
                new_left_x: int = int(corners[0][0] // tile_h)
                new_left_y: int = int((corners[0][1] + HERO_SPEED) // tile_h)
                new_bottom_x: int = int(corners[1][0] // tile_h)
                new_bottom_y: int = int((corners[1][1] + HERO_SPEED) // tile_h)
                
                if new_left_y < self.room.heightmap.get_height() and self.can_move_to(
                    hero_pos.x, next_y, [(new_left_x, new_left_y), (new_bottom_x, new_bottom_y)]
                ):
                    new_y = next_y
                    moved = True
            
            if moved:
                entity = check_collids_entity(self.hero, new_x, new_y, self.room.entities, 16)
                if entity is not None:
                    print(f"Hero at {self.hero.get_world_pos()} collids with {entity.name} at {entity.get_world_pos()}")

                # Resolve entity collisions in XY plane
                # This only handles horizontal collision, not Z-axis (gravity handles that)
                new_x, new_y, touched_entity = resolve_entity_collision(
                    self.hero,
                    self.room.entities,
                    new_x,
                    new_y,
                    tile_h,
                    self.room.heightmap.left_offset,
                    self.room.heightmap.top_offset,
                    self.camera_x,
                    self.camera_y
                )
                
                self.hero.set_world_pos(
                    new_x, new_y, hero_pos.z,
                    self.room.heightmap.left_offset,
                    self.room.heightmap.top_offset,
                    self.camera_x,
                    self.camera_y
                )
                
                # Update grabbed entity position if carrying something
                if self.hero.is_grabbing:
                    self.hero.update_grabbed_entity_position(
                        self.room.heightmap.left_offset,
                        self.room.heightmap.top_offset,
                        self.camera_x,
                        self.camera_y,
                        tile_h
                    )
                
                if self.camera_locked:
                    self.center_camera_on_hero()
            
            self.hero.update_z_velocity()
            self.hero.update_animation(is_moving)
    
    def handle_jump(self, keys: pygame.key.ScancodeWrapper) -> None:
        """Handle hero jumping"""
        if keys[pygame.K_SPACE] and self.hero.touch_ground and not self.hero.is_jumping:
            self.hero.is_jumping = True
        
        if self.hero.is_jumping:
            hero_pos = self.hero.get_world_pos()
            if self.hero.current_jump < HERO_MAX_JUMP:
                self.hero.current_jump += 2
                new_z: float = hero_pos.z + 2
                self.hero.set_world_pos(
                    hero_pos.x, hero_pos.y, new_z,
                    self.room.heightmap.left_offset,
                    self.room.heightmap.top_offset,
                    self.camera_x,
                    self.camera_y
                )
                
                # Update grabbed entity position if carrying something
                tile_h: int = self.room.data.tileheight
                if self.hero.is_grabbing:
                    self.hero.update_grabbed_entity_position(
                        self.room.heightmap.left_offset,
                        self.room.heightmap.top_offset,
                        self.camera_x,
                        self.camera_y,
                        tile_h
                    )
                
                if self.camera_locked:
                    self.center_camera_on_hero()
            else:
                self.hero.is_jumping = False
                self.hero.current_jump = 0
    

    def check_action(self, keys: pygame.key.ScancodeWrapper) -> None:
        """Handle action button (A key) - interact with entities or pickup/place"""
        tile_h: int = self.room.data.tileheight
        
        # Check if action button (A key) was just pressed
        if not self.is_key_just_pressed(pygame.K_a, keys):
            return
        
        # handle pickup/place
        if self.hero.is_grabbing:
            # Try to place the entity in front of hero
            hero_pos = self.hero.get_world_pos()
            
            # Get position in front of hero
            place_x, place_y = get_position_in_front_of_hero(self.hero, tile_h)
            
            # Get tile coordinates for terrain height check
            place_tile_x = int(place_x // tile_h)
            place_tile_y = int(place_y // tile_h)

            if (place_tile_x >= 0 and place_tile_y >= 0 and
                place_tile_x < self.room.heightmap.get_width() and
                place_tile_y < self.room.heightmap.get_height()):
                
                cell = self.room.heightmap.get_cell(place_tile_x, place_tile_y)
                if cell:
                    place_z = cell.height * tile_h
                    
                    if can_place_entity_at_position(
                        hero_pos.z,
                        self.hero.grabbed_entity,
                        place_x,
                        place_y,
                        place_z,
                        self.room.entities,
                        self.room.heightmap,
                        tile_h
                    ):
                        # Place the entity at exact pixel position
                        self.hero.grabbed_entity.set_world_pos(
                            place_x,
                            place_y,
                            place_z,
                            self.room.heightmap.left_offset,
                            self.room.heightmap.top_offset,
                            self.camera_x,
                            self.camera_y
                        )
                        if self.hero.grabbed_entity.bbox:
                            self.hero.grabbed_entity.bbox.update_position(self.hero.grabbed_entity._world_pos)
                        
                        print(f"Placed entity: {self.hero.grabbed_entity.name} at ({place_x:.1f}, {place_y:.1f}, {place_z:.1f})")
                        
                        # Release the entity
                        self.hero.release_entity()
                    else:
                        print("Cannot place entity here - position blocked")
                else:
                    print("Cannot place entity here - invalid terrain")
            else:
                print("Cannot place entity here - out of bounds")
        else:
            # Check for entity in front of hero
            entity = get_entity_in_front_of_hero(
                self.hero,
                self.room.entities,
                tile_h
            )

            if entity is not None: 
                # handle dialog
                if entity.has_dialogue == True:
                    self.show_dialog(entity.dialogue, entity)
                    return
                elif entity.no_pickup == False:
                    # Try to grab an entity
                    self.hero.grab_entity(entity)
                    
                    # Position entity above hero
                    self.hero.update_grabbed_entity_position(
                        self.room.heightmap.left_offset,
                        self.room.heightmap.top_offset,
                        self.camera_x,
                        self.camera_y,
                        tile_h
                    )
                    
                    print(f"Grabbed entity: {entity.name}")

    def handle_debug_toggles(self, keys: pygame.key.ScancodeWrapper) -> None:
        """Handle debug flag toggles"""
        if self.debug_mode:
            if self.is_key_just_pressed(pygame.K_F1, keys):
                self.is_boundbox_displayed = not self.is_boundbox_displayed

            if self.is_key_just_pressed(pygame.K_F2, keys):
                self.is_height_map_displayed = not self.is_height_map_displayed

            if self.is_key_just_pressed(pygame.K_F3, keys):
                self.is_warps_displayed = not self.is_warps_displayed
    
    def handle_zoom(self, keys: pygame.key.ScancodeWrapper) -> None:
        """Handle zoom in/out with Z key (Shift+Z to zoom out)"""
        # Check if Z key was just pressed
        if self.is_key_just_pressed(pygame.K_z, keys):
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                # Zoom out (decrease zoom index)
                if self.current_zoom_index > 0:
                    self.current_zoom_index -= 1
                    self.apply_zoom()
            else:
                # Zoom in (increase zoom index)
                if self.current_zoom_index < len(self.zoom_levels) - 1:
                    self.current_zoom_index += 1
                    self.apply_zoom()
    
    def apply_zoom(self) -> None:
        """Apply the current zoom level to display resolution"""
        zoom_factor = self.zoom_levels[self.current_zoom_index]
        
        # Calculate new display dimensions maintaining aspect ratio
        self.display_width = int(self.original_display_width / zoom_factor)
        self.display_height = int(self.original_display_height / zoom_factor)
        
        # Update base dimensions for scaling calculations
        self.base_width = self.display_width
        self.base_height = self.display_height
        
        # Recreate surface at new resolution
        self.surface = pygame.Surface((self.display_width, self.display_height))
        
        # Recreate fade surface
        self.fade_surface = pygame.Surface((self.display_width, self.display_height))
        self.fade_surface.fill((0, 0, 0))
        self.fade_surface.set_alpha(self.fade_alpha)
        
        # Recreate GUI manager with new dimensions
        self.manager = pygame_gui.UIManager((self.display_width, self.display_height), "ui.json")
        
        # Recreate HUD elements
        self.hud_textbox = UITextBox(
            "",
            pygame.Rect((0, 0), (self.display_width, 36)),
            manager=self.manager,
            object_id="#hud_textbox",
        )
        self.coord_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 2), (-1, -1)),
            text="",
            manager=self.manager
        )
        
        # Recreate dialog elements
        self.dialog_textbox = UITextBox(
            "",
            pygame.Rect((0, self.display_height - 60), (self.display_width, 58)),
            manager=self.manager,
            object_id="#dialog_textbox",
        )
        self.coord_dialog = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, self.display_height - 60), (-1, -1)),
            text="",
            manager=self.manager
        )
        
        # Hide dialog by default
        self.dialog_textbox.hide()
        self.coord_dialog.hide()
        
        # Recreate menu screen with new dimensions
        self.menu_screen.recreate_for_resolution(self.display_width, self.display_height)
        
        # Recalculate scaling
        self._update_scaling()
        
        # Recenter camera on hero
        self.center_camera_on_hero()
        
        print(f"Zoom: {zoom_factor}x ({self.display_width}x{self.display_height})")
    
    def update_hud(self) -> None:
        """Update HUD with debug information"""
        if self.debug_mode:
            hero_pos = self.hero.get_world_pos()
            tile_h: int = self.room.data.tileheight
            tile_x: float = hero_pos.x // tile_h
            tile_y: float = hero_pos.y // tile_h
            tile_z: float = hero_pos.z // tile_h
            
            self.coord_label.set_text(
                f"X: {hero_pos.x:.1f} ({tile_x:.0f}), Y: {hero_pos.y:.1f} ({tile_y:.0f}), Z: {hero_pos.z:.1f} ({tile_z:.0f})\n "
            )

    def load_compressed_strings(self, filepath: str) -> list[str]:
        """Load compressed strings from text file (one per line)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                strings = [line.rstrip('\n\r') for line in f]
            
            print(f"Loaded {len(strings)} compressed strings from {filepath}")
            return strings
            
        except FileNotFoundError:
            print(f"Warning: Compressed strings file not found at {filepath}")
            return []
        except Exception as e:
            print(f"Error loading compressed strings: {e}")
            import traceback
            traceback.print_exc()
            return []

    def load_main_scripts(self, filepath: str) -> dict:
        """Load dialog data from YAML file"""
        import re
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse script into a dictionary indexed by ID
            scripts = {}
            
            # Split by script sections (look for # ID: comments)
            sections = re.split(r'# ID:\s*(\d+)', content)
            
            # sections[0] is content before first ID (usually empty)
            # sections[1] is first ID, sections[2] is first script content
            # sections[3] is second ID, sections[4] is second script content, etc.
            for i in range(1, len(sections), 2):
                if i + 1 < len(sections):
                    script_id = int(sections[i].strip())
                    script_content = sections[i + 1]
                    
                    # Parse the YAML content for this script
                    try:
                        parsed = yaml.safe_load(script_content)
                        if parsed:
                            scripts[script_id] = parsed if isinstance(parsed, list) else [parsed]
                    except yaml.YAMLError:
                        # Skip malformed script sections
                        continue
            
            print(f"Loaded {len(scripts)} dialogs from {filepath}")
            return scripts
            
        except FileNotFoundError:
            print(f"Warning: Dialog file not found at {filepath}")
            return {}
        except Exception as e:
            print(f"Error loading dialogs: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def run_script(self, id: int) -> None:
        """Run main script by ID"""
        if id not in self.main_scripts:
            print(f"Warning: Dialog ID {id} not found")
            return
        
        # Get the first string entry for this dialog
        script = self.main_scripts[id]
        if script and "String" in script[0]:
            string_id = script[0]["String"]
            self.dialog_textbox.set_text(f"String ID: {string_id}")

    def show_dialog(self, dialog_id: int, entity = None) -> None:
        """Display a dialog by ID with typing effect
        
        Args:
            dialog_id: The dialog ID to display
            entity: The entity speaking (optional, used for voice pitch)
        """       
        self.current_dialog_id = dialog_id
        self.display_dialog = True
        
        # Set pitch based on entity's talk_sound_fx if available
        if entity and hasattr(entity, 'talk_sound_fx'):
            # Map talk_sound_fx (69-72) to pitch
            # 69 = highest pitch (1.5x)
            # 70 = high pitch (1.2x)
            # 71 = low pitch (0.8x)
            # 72 = lowest pitch (0.6x)
            pitch_map = {
                69: 1.5,   # Highest pitch
                70: 1.2,   # High pitch
                71: 0.8,   # Low pitch
                72: 0.6    # Lowest pitch
            }
            pitch = pitch_map.get(entity.talk_sound_fx, 1.0)
            self.set_dialog_bip_pitch(pitch)
            print(f"Entity {entity.name} talk_sound_fx={entity.talk_sound_fx}, pitch={pitch}")
        else:
            # Default pitch
            self.set_dialog_bip_pitch(1.0)
        
        # Set up typing effect
        self.dialog_full_text = "This is a work in progress"
        self.dialog_current_text = ""
        self.dialog_char_index = 0
        self.dialog_char_timer = 0.0
        self.dialog_finished = False
        
        self.dialog_textbox.set_text("")
    
    def update_dialog_typing(self, dt: float) -> None:
        """Update dialog typing effect"""
        if not self.display_dialog or self.dialog_finished:
            return
        
        # Update timer
        self.dialog_char_timer += dt
        
        # Check if it's time to add next character
        if self.dialog_char_timer >= self.dialog_char_delay:
            self.dialog_char_timer = 0.0
            
            if self.dialog_char_index < len(self.dialog_full_text):
                # Add next character
                self.dialog_current_text += self.dialog_full_text[self.dialog_char_index]
                self.dialog_char_index += 1
                
                # Play bip sound (but not for spaces)
                if self.dialog_bip_sound and self.dialog_full_text[self.dialog_char_index - 1] != ' ':
                    self.dialog_bip_sound.play()
                
                # Update textbox
                self.dialog_textbox.set_text(self.dialog_current_text)
            else:
                # Typing finished
                self.dialog_finished = True

    def render(self) -> None:
        self.surface.fill((0, 0, 0))
        
        # Draw map and debug (passing display dimensions to room.draw)
        self.room.draw(self.surface, self.camera_x, self.camera_y, self.hero,
                       self.display_width, self.display_height)

        if self.debug_mode:
            if self.is_height_map_displayed:
                draw_heightmap(self.surface, self.room.heightmap, self.room.data.tileheight, 
                            self.camera_x, self.camera_y)

            if self.is_boundbox_displayed:
                draw_boundbox(self.hero.bbox, self.surface, self.room.data.tileheight, 
                                self.camera_x, self.camera_y, self.room.heightmap.left_offset, 
                                self.room.heightmap.top_offset)
                for entity in self.room.entities:
                    draw_boundbox(entity.bbox, self.surface, self.room.data.tileheight, self.camera_x, 
                                  self.camera_y, self.room.heightmap.left_offset, self.room.heightmap.top_offset)

            if self.is_warps_displayed:
                draw_warps(self.surface, self.room.warps, self.room.heightmap, 
                        self.room.data.tileheight, self.camera_x, self.camera_y, 
                        self.room_number)

        # Draw UI on top of everything
        self.manager.draw_ui(self.surface)

        # Scale with aspect ratio
        screen_w, screen_h = self.screen.get_size()
        scale = min(screen_w / self.display_width, screen_h / self.display_height)
        scaled_w = int(self.display_width * scale)
        scaled_h = int(self.display_height * scale)
        scaled_surface = pygame.transform.scale(self.surface, (scaled_w, scaled_h))
        
        # Center the scaled surface
        offset_x = (screen_w - scaled_w) // 2
        offset_y = (screen_h - scaled_h) // 2
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled_surface, (offset_x, offset_y))

        # Draw fade overlay if active
        if self.fade_alpha > 0:
            scaled_fade = pygame.transform.scale(self.fade_surface, (scaled_w, scaled_h))
            self.screen.blit(scaled_fade, (offset_x, offset_y))
        
        pygame.display.flip()


    def check_hero_spawn_on_entity(self) -> None:
        """Fix hero Z position if spawned inside/below an entity
        
        When warping, hero may spawn at tile height but should be on top of entities.
        """
        tile_h: int = self.room.data.tileheight
        
        # Get hero's current position and bbox
        hero_pos = self.hero.get_world_pos()
        hero_bbox = self.hero.get_bounding_box(tile_h)
        hero_x, hero_y, hero_w, hero_h = hero_bbox
        

        for entity in self.room.entities:
            if check_entity_collision_3d(self.hero.bbox, entity.bbox, tile_h):
                print(f"Collids with entity {entity.name}")
                self.hero.set_world_z(8)
                
    def check_initial_entity_collision(self) -> None:
        """Check for entity collisions immediately after spawn/warp
        
        This handles the case where hero spawns already standing on an entity
        that should trigger a script (like a raft).
        """

        tile_h: int = self.room.data.tileheight
        
        # Get entities hero is currently standing on
        hero_bbox = self.hero.get_bounding_box(tile_h)
        hero_x, hero_y, hero_w, hero_h = hero_bbox
        hero_z = self.hero.get_world_pos().z
        
        entities_to_check = [e for e in self.room.entities 
                            if e is not self.hero.grabbed_entity]
        
        entity_standing_on = get_entity_hero_is_standing_on(
            self.hero,
            entities_to_check,
            tile_h
        )
        
        if entity_standing_on is not None:
            print(f"Hero spawned standing on {entity_standing_on.name}")
            self.on_entity_collids(entity_standing_on)

    def run(self) -> None:
        """Main game loop"""
        running: bool = True
        while running:
            time_delta: float = self.clock.tick(FPS) / 1000.0
            
            # Handle events
            running = self.handle_events()
            if not running:
                break
            
            # Get key states
            keys: pygame.key.ScancodeWrapper = pygame.key.get_pressed()
            
            # Exit on Escape
            if keys[pygame.K_ESCAPE]:
                break
  
            # === MENU MODE ===
            if self.menu_active:
                # Only handle menu input and updates
                self.menu_active = self.menu_screen.handle_input(keys, self.prev_keys)
                self.menu_screen.update(time_delta)
                
                # Render game in background (frozen state)
                self.surface.fill((0, 0, 0))
                self.room.draw(self.surface, self.camera_x, self.camera_y, self.hero,
                               self.display_width, self.display_height)
                
                # Darken the game background
                dark_overlay = pygame.Surface((self.display_width, self.display_height))
                dark_overlay.fill((0, 0, 0))
                dark_overlay.set_alpha(128)  # 50% transparent
                self.surface.blit(dark_overlay, (0, 0))
                
                # Render menu on top
                self.menu_screen.render(self.surface)
                
                # Scale and display
                screen_w, screen_h = self.screen.get_size()
                scale = min(screen_w / self.display_width, screen_h / self.display_height)
                scaled_w = int(self.display_width * scale)
                scaled_h = int(self.display_height * scale)
                scaled_surface = pygame.transform.scale(self.surface, (scaled_w, scaled_h))
                
                offset_x = (screen_w - scaled_w) // 2
                offset_y = (screen_h - scaled_h) // 2
                self.screen.fill((0, 0, 0))
                self.screen.blit(scaled_surface, (offset_x, offset_y))
                pygame.display.flip()
                
            # === DIALOG MODE ===
            elif self.display_dialog:
                # Show dialog elements
                self.dialog_textbox.show()
                self.coord_dialog.show()
                
                # Update typing effect
                self.update_dialog_typing(time_delta)
                
                # Wait for action key to dismiss dialog
                if keys[pygame.K_a] and not self.prev_keys.get(pygame.K_a, False):
                    # If typing not finished, skip to end
                    if not self.dialog_finished:
                        self.dialog_current_text = self.dialog_full_text
                        self.dialog_char_index = len(self.dialog_full_text)
                        self.dialog_finished = True
                        self.dialog_textbox.set_text(self.dialog_current_text)
                    else:
                        # Dismiss dialog
                        self.display_dialog = False
                        self.dialog_textbox.hide()
                        self.coord_dialog.hide()
                
                # Update and render
                self.update_hud()
                self.manager.update(time_delta)
                self.update_fade(time_delta)
                self.render()
                
            # === GAMEPLAY MODE ===
            else:
                # Hide dialog elements
                self.dialog_textbox.hide()
                self.coord_dialog.hide()

                # Normal gameplay controls
                self.handle_camera_movement(keys)
                self.handle_debug_toggles(keys)
                self.handle_zoom(keys)
                self.apply_gravity()
                self.handle_hero_movement(keys)
                self.handle_jump(keys)
                self.check_action(keys)
                
                # Check for warps and falls
                self.check_warp_collision()
                self.check_fall()
            
                # Update carried entities
                update_carried_positions(
                    self.hero,
                    self.room.entities,
                    16,
                    self.room.heightmap.left_offset,
                    self.room.heightmap.top_offset,
                    self.camera_x,
                    self.camera_y
                )
                
                # Auto-center camera if not in debug mode
                if not self.debug_mode:
                    self.center_camera_on_hero()

                # Update entity scripts
                for entity in self.room.entities:
                    if hasattr(entity, 'script_handler') and entity.script_handler.is_running:
                        entity.script_handler.update()

                        # Update entity's screen position based on world position changes
                        entity.update_camera(
                            self.room.heightmap.left_offset,
                            self.room.heightmap.top_offset,
                            self.camera_x,
                            self.camera_y
                        )

                # Update and render
                self.update_hud()
                self.manager.update(time_delta)
                self.update_fade(time_delta)
                self.render()

            # Store current key states for next frame
            self.prev_keys = {k: keys[k] for k in [pygame.K_RETURN, pygame.K_b, pygame.K_ESCAPE, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_z, pygame.K_F1, pygame.K_F2, pygame.K_F3]}
        
        pygame.quit()
        sys.exit()