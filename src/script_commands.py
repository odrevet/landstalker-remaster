"""
Script command handlers for entity behaviors with smooth tile-based movement
"""
from typing import Dict, Any, Optional
from collision import update_carried_positions
import yaml


class ScriptCommands:
    """Handles execution of entity script commands"""
    
    def __init__(self, entity):
        """Initialize script command handler
        
        Args:
            entity: The entity that will execute these commands
        """
        self.entity = entity

        # Reference to game instance
        self.game = None

        # Script execution state
        self.is_running = False
        self.current_command_index = 0
        self.current_command_state = None  # Stores state for ongoing commands
        self.script_commands = []
        self.paused = False
        self.pause_ticks_remaining = 0
        self.should_loop = True  # Default: scripts loop
        self.waiting_for_condition = False  # Flag for WaitForCondition state
        self.wait_condition_type = None  # Store which condition we're waiting for
        
        # Command dispatcher - maps command names to handler methods
        self.command_handlers = {
            # Movement commands
            'MoveRelative': self.cmd_move_relative,
            'MoveAbsolute': self.cmd_move_absolute,
            'MoveTimed': self.cmd_move_timed,
            'MoveRandomTimed': self.cmd_move_random_timed,
            'MoveNoClip': self.cmd_move_no_clip,
            'MoveUntilCollision': self.cmd_move_until_collision,
            'MoveUpRelative': self.cmd_move_up_relative,
            'MoveUpAbsolute': self.cmd_move_up_absolute,
            'MoveUpTimed': self.cmd_move_up_timed,
            'MoveUpToInitPos': self.cmd_move_up_to_init_pos,
            'MoveDownRelative': self.cmd_move_down_relative,
            'MoveDownAbsolute': self.cmd_move_down_absolute,
            'MoveDownTimed': self.cmd_move_down_timed,
            'MoveDownUntilCollision': self.cmd_move_down_until_collision,
            'MoveToXYPosImmedite': self.cmd_move_to_xy_pos_immediate,
            'MoveToZPosImmediate': self.cmd_move_to_z_pos_immediate,
            'MoveToTargetPosition': self.cmd_move_to_target_position,
            'SetTargetPosition': self.cmd_set_target_position,
            'NudgeUp': self.cmd_nudge_up,
            'ResetToInitialPos': self.cmd_reset_to_initial_pos,
            'Jump': self.cmd_jump,
            
            # Rotation commands
            'TurnCW': self.cmd_turn_cw,
            'TurnCWImmediate': self.cmd_turn_cw_immediate,
            'TurnCWNoUpdate': self.cmd_turn_cw_no_update,
            'TurnCCW': self.cmd_turn_ccw,
            'TurnCCWImmedate': self.cmd_turn_ccw_immediate,
            'TurnCCWNoUpdate': self.cmd_turn_ccw_no_update,
            'Turn180': self.cmd_turn_180,
            'Turn180Immediate': self.cmd_turn_180_immediate,
            'Turn180NoUpdate': self.cmd_turn_180_no_update,
            'TurnNE': self.cmd_turn_ne,
            'TurnNEImmediate': self.cmd_turn_ne_immediate,
            'TurnNENoUpdate': self.cmd_turn_ne_no_update,
            'TurnNW': self.cmd_turn_nw,
            'TurnNWImmediate': self.cmd_turn_nw_immediate,
            'TurnNWNoUpdate': self.cmd_turn_nw_no_update,
            'TurnSE': self.cmd_turn_se,
            'TurnSEImmediate': self.cmd_turn_se_immediate,
            'TurnSENoUpdate': self.cmd_turn_se_no_update,
            'TurnSW': self.cmd_turn_sw,
            'TurnSWImmediate': self.cmd_turn_sw_immediate,
            'TurnSWNoUpdate': self.cmd_turn_sw_no_update,
            'TurnRandom': self.cmd_turn_random,
            'TurnRandomImmediate': self.cmd_turn_random_immediate,
            'TurnToFace': self.cmd_turn_to_face,
            'RotatePlayer': self.cmd_rotate_player,
            'UpdateSpriteOrientation': self.cmd_update_sprite_orientation,
            
            # Timing commands
            'Pause': self.cmd_pause,
            'Pause4s': self.cmd_pause_4s,
            'Freeze': self.cmd_freeze,
            
            # Speed commands
            'SlowSpeed': self.cmd_slow_speed,
            'NormalSpeed': self.cmd_normal_speed,
            'FastSpeed': self.cmd_fast_speed,
            'XFastSpeed': self.cmd_xfast_speed,
            'SetObjectSpeed': self.cmd_set_object_speed,
            
            # Action commands
            'PlayAnimation': self.cmd_play_animation,
            'PlaySound': self.cmd_play_sound,
            'SetVisible': self.cmd_set_visible,
            'SetSolid': self.cmd_set_solid,
            'MakeVisible': self.cmd_make_visible,
            'MakeInvisible': self.cmd_make_invisible,
            'Hide': self.cmd_hide,
            'RemoveSprite': self.cmd_remove_sprite,
            'ShowWhenCollisionClear': self.cmd_show_when_collision_clear,
            
            # Physics commands
            'EnableGravity': self.cmd_enable_gravity,
            'DisableGravity': self.cmd_disable_gravity,
            'EnableBackwardsMovement': self.cmd_enable_backwards_movement,
            'DisableBackwardsMovement': self.cmd_disable_backwards_movement,
            'EnableFrameUpdate': self.cmd_enable_frame_update,
            'DisableFrameUpdate': self.cmd_disable_frame_update,
            
            # Visual effects
            'FlashSpinAppear': self.cmd_flash_spin_appear,
            'FlashSpinDisappear': self.cmd_flash_spin_disappear,
            'DecayFlash': self.cmd_decay_flash,
            
            # Dialog/Interaction commands
            #'ShowDialog': self.cmd_show_dialog,
            #'PrintText': self.cmd_print_text,
            #'GiveItem': self.cmd_give_item,
            #'TakeItem': self.cmd_take_item,
            #'ShopItem': self.cmd_shop_item,
            
            # AI/Behavior commands
            #'LoadSpecialAI': self.cmd_load_special_ai,
            #'MakeHostile': self.cmd_make_hostile,
            #'MakeNonHostile': self.cmd_make_non_hostile,
            
            # Conditional commands
            'IfHasItem': self.cmd_if_has_item,
            'IfFlagSet': self.cmd_if_flag_set,
            'WaitForCondition': self.cmd_wait_for_condition,
            'WaitForFlagSet': self.cmd_wait_for_flag_set,
            'WaitForFlagClear': self.cmd_wait_for_flag_clear,
            
            # Flag commands
            'SetFlag': self.cmd_set_flag,
            'ClearFlag': self.cmd_clear_flag,
            
            # Switch commands
            'ActivateSwitch': self.cmd_activate_switch,
            'ResetSwitch': self.cmd_reset_switch,
            
            # Cutscene commands
            'StartCutscene': self.cmd_start_cutscene,
            'StartHiCutscene': self.cmd_start_hi_cutscene,
            
            # Level manipulation
            'TriggerTileSwap': self.cmd_trigger_tile_swap,
            
            # Player control
            'FollowPlayerNoJump': self.cmd_follow_player_no_jump,
            'FollowPlayerWithJump': self.cmd_follow_player_with_jump,
            'PlaybackInput': self.cmd_playback_input,
            'ResetPlayback': self.cmd_reset_playback,
            
            # Flow control
            'GotoCommand': self.cmd_goto_command,
            'RepeatBegin': self.cmd_repeat_begin,
            'RepeatEnd': self.cmd_repeat_end,
            'Loop': self.cmd_loop,
            'End': self.cmd_end,
            
            # Unknown commands (stubs)
            'Unknown5A': self.cmd_unknown_5a,
            'UnknownB33': self.cmd_unknown_b33,
            'UnknownB47': self.cmd_unknown_b47,
            'UnknownB63': self.cmd_unknown_b63,
            'UnknownB65': self.cmd_unknown_b65,
            'UnknownB66': self.cmd_unknown_b66,
            'UnknownB67': self.cmd_unknown_b67,
        }
    
    # === Movement Commands ===
        
    def cmd_move_relative(self, params: Dict[str, Any]) -> bool:
        """Move entity relative to current position (smoothly over time)
        
        All coordinates are in tiles. Movement speed is in tiles per frame.
        The actual distance traveled = Distance parameter × entity.speed
        
        Args:
            params: Dictionary containing 'Distance' parameter (scale factor)
            
        Returns:
            True if command is complete, False if still in progress
        """
        # Initialize command state on first call
        if self.current_command_state is None:
            distance_scale = params.get('Distance', 0.0)  # Scale factor
            
            # Actual distance in tiles = distance × 2^(speed-1)
            # Examples: speed=1,dist=8 → 8×1=8; speed=2,dist=6 → 6×2=12; speed=3,dist=4 → 4×4=16
            speed_multiplier = 2 ** (self.entity.speed - 1)
            actual_distance = distance_scale * speed_multiplier
            
            orientation = self.entity.orientation
            
            # Direction vectors for isometric movement
            direction_map = {
                'NE': (0, -1),  # Move north-east
                'SE': (1, 0),   # Move south-east
                'SW': (0, 1),   # Move south-west
                'NW': (-1, 0),  # Move north-west
            }
            
            dx, dy = direction_map.get(orientation, (0.0, 0.0))
            
            print(f"{orientation} {dx} {dy}")

            # Calculate target position in tiles
            current_pos = self.entity.get_world_pos()
            target_x = current_pos.x + (dx * actual_distance)
            target_y = current_pos.y + (dy * actual_distance)
            
            # Movement speed in tiles per frame
            speed_per_frame = self.entity.speed / 16  # Convert entity speed to tiles per frame
            
            self.current_command_state = {
                'target_x': target_x,
                'target_y': target_y,
                'dx': dx,
                'dy': dy,
                'speed': speed_per_frame
            }
            
            print(f"  [START] MoveRelative: distance_scale={distance_scale:.3f}, "
                f"entity_speed={self.entity.speed}, actual_distance={actual_distance:.3f} tiles, "
                f"from=({current_pos.x} {current_pos.y}) target=({target_x:.3f}, {target_y:.3f}), "
                f"speed={speed_per_frame:.3f} tiles/frame")

        # Continue moving toward target
        state = self.current_command_state
        current_pos = self.entity.get_world_pos()

        print(f"from=({current_pos.x} {current_pos.y}) target=({state['target_x']:.3f}, {state['target_y']:.3f})")

        # Calculate distance to target (in tiles)
        dist_x = state['target_x'] - current_pos.x
        dist_y = state['target_y'] - current_pos.y
        distance_remaining = (dist_x**2 + dist_y**2)**0.5
        
        # Check if we've reached the target
        if distance_remaining < state['speed']:
            # Snap to exact target position
            self.entity.set_world_pos(
                state['target_x'],
                state['target_y'],
                current_pos.z,
                0, 0, 0, 0, 0  # These will be updated by game loop
            )
            print(f"  [COMPLETE] MoveRelative: reached target ({state['target_x']:.3f}, {state['target_y']:.3f})")
            self.current_command_state = None
            return True  # Command complete
        
        # Move one step toward target (in tiles)
        move_x = state['dx'] * state['speed']
        move_y = state['dy'] * state['speed']
        
        new_x = current_pos.x + move_x
        new_y = current_pos.y + move_y
        
        self.entity.set_world_pos(
            new_x,
            new_y,
            current_pos.z,
            0, 0, 0, 0, 0
        )

        update_carried_positions(
            self.game.hero,
            self.game.room.entities,
            self.game.room.heightmap.left_offset,
            self.game.room.heightmap.top_offset,
            self.game.camera_x,
            self.game.camera_y,
            self.game.get_tilemap_height()
        )
        
        return False  # Command still in progress
    
    def cmd_move_absolute(self, params: Dict[str, Any]) -> bool:
        """Move entity to absolute position in tiles
        
        Args:
            params: Dictionary containing 'X', 'Y', 'Z' coordinates (in tiles)
            
        Returns:
            True (instant command)
        """
        x = params.get('X', 0.0)  # In tiles
        y = params.get('Y', 0.0)  # In tiles
        z = params.get('Z', 0.0)  # In tiles
        print(f"  [EXEC] MoveAbsolute: x={x:.3f}, y={y:.3f}, z={z:.3f} tiles")
        
        self.entity.set_world_pos(x, y, z, 0, 0, 0, 0, 0)
        return True
    
    def cmd_move_timed(self, params: Dict[str, Any]) -> bool:
        """Move entity in current direction for specified ticks
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            ticks = params.get('Ticks', 0)
            speed_per_frame = self.entity.speed / 16
            
            orientation = self.entity.orientation
            direction_map = {
                'NE': (0, -1),
                'SE': (1, 0),
                'SW': (0, 1),
                'NW': (-1, 0),
            }
            dx, dy = direction_map.get(orientation, (0.0, 0.0))
            
            self.current_command_state = {
                'ticks_remaining': ticks,
                'dx': dx,
                'dy': dy,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveTimed: ticks={ticks}, orientation={orientation}")
        
        state = self.current_command_state
        state['ticks_remaining'] -= 1
        
        if state['ticks_remaining'] <= 0:
            print(f"  [COMPLETE] MoveTimed")
            self.current_command_state = None
            return True
        
        # Move one step
        current_pos = self.entity.get_world_pos()
        move_x = state['dx'] * state['speed']
        move_y = state['dy'] * state['speed']
        
        new_x = current_pos.x + move_x
        new_y = current_pos.y + move_y
        
        self.entity.set_world_pos(new_x, new_y, current_pos.z, 0, 0, 0, 0, 0)
        
        update_carried_positions(
            self.game.hero,
            self.game.room.entities,
            self.game.room.heightmap.left_offset,
            self.game.room.heightmap.top_offset,
            self.game.camera_x,
            self.game.camera_y,
            self.game.get_tilemap_height()
        )
        
        return False
    
    def cmd_move_random_timed(self, params: Dict[str, Any]) -> bool:
        """Move entity in random direction for specified ticks
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            import random
            ticks = params.get('Ticks', 0)
            speed_per_frame = self.entity.speed / 16
            
            # Pick random direction
            directions = ['NE', 'SE', 'SW', 'NW']
            random_orientation = random.choice(directions)
            
            direction_map = {
                'NE': (0, -1),
                'SE': (1, 0),
                'SW': (0, 1),
                'NW': (-1, 0),
            }
            dx, dy = direction_map.get(random_orientation, (0.0, 0.0))
            
            self.current_command_state = {
                'ticks_remaining': ticks,
                'dx': dx,
                'dy': dy,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveRandomTimed: ticks={ticks}, direction={random_orientation}")
        
        state = self.current_command_state
        state['ticks_remaining'] -= 1
        
        if state['ticks_remaining'] <= 0:
            print(f"  [COMPLETE] MoveRandomTimed")
            self.current_command_state = None
            return True
        
        # Move one step
        current_pos = self.entity.get_world_pos()
        move_x = state['dx'] * state['speed']
        move_y = state['dy'] * state['speed']
        
        new_x = current_pos.x + move_x
        new_y = current_pos.y + move_y
        
        self.entity.set_world_pos(new_x, new_y, current_pos.z, 0, 0, 0, 0, 0)
        
        update_carried_positions(
            self.game.hero,
            self.game.room.entities,
            self.game.room.heightmap.left_offset,
            self.game.room.heightmap.top_offset,
            self.game.camera_x,
            self.game.camera_y,
            self.game.get_tilemap_height()
        )
        
        return False
    
    def cmd_move_no_clip(self, params: Dict[str, Any]) -> bool:
        """Move entity without collision detection
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] MoveNoClip: unknown={unknown}")
        return True
    
    def cmd_move_until_collision(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Move entity in current direction until collision
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] MoveUntilCollision")
        return True
    
    def cmd_move_up_relative(self, params: Dict[str, Any]) -> bool:
        """Move entity up (increase Z) by relative distance
        
        Args:
            params: Dictionary containing 'Distance' parameter (in tiles)
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            distance = params.get('Distance', 0.0)
            current_pos = self.entity.get_world_pos()
            target_z = current_pos.z + distance
            speed_per_frame = self.entity.speed / 16
            
            self.current_command_state = {
                'target_z': target_z,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveUpRelative: distance={distance:.3f}, from={current_pos.z:.3f} to={target_z:.3f}")
        
        state = self.current_command_state
        current_pos = self.entity.get_world_pos()
        
        distance_remaining = state['target_z'] - current_pos.z
        
        if abs(distance_remaining) < state['speed']:
            self.entity.set_world_pos(
                current_pos.x, current_pos.y, state['target_z'],
                0, 0, 0, 0, 0
            )
            print(f"  [COMPLETE] MoveUpRelative: reached z={state['target_z']:.3f}")
            self.current_command_state = None
            return True
        
        new_z = current_pos.z + state['speed']
        self.entity.set_world_pos(current_pos.x, current_pos.y, new_z, 0, 0, 0, 0, 0)
        
        return False
    
    def cmd_move_up_absolute(self, params: Dict[str, Any]) -> bool:
        """Move entity up to absolute Z position
        
        Args:
            params: Dictionary containing 'Distance' parameter (absolute Z in tiles)
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            target_z = params.get('Distance', 0.0)
            current_pos = self.entity.get_world_pos()
            speed_per_frame = self.entity.speed / 16
            
            self.current_command_state = {
                'target_z': target_z,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveUpAbsolute: from={current_pos.z:.3f} to={target_z:.3f}")
        
        state = self.current_command_state
        current_pos = self.entity.get_world_pos()
        
        distance_remaining = state['target_z'] - current_pos.z
        
        if abs(distance_remaining) < state['speed']:
            self.entity.set_world_pos(
                current_pos.x, current_pos.y, state['target_z'],
                0, 0, 0, 0, 0
            )
            print(f"  [COMPLETE] MoveUpAbsolute: reached z={state['target_z']:.3f}")
            self.current_command_state = None
            return True
        
        new_z = current_pos.z + state['speed']
        self.entity.set_world_pos(current_pos.x, current_pos.y, new_z, 0, 0, 0, 0, 0)
        
        return False
    
    def cmd_move_up_timed(self, params: Dict[str, Any]) -> bool:
        """Move entity up for specified ticks
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            ticks = params.get('Ticks', 0)
            speed_per_frame = self.entity.speed / 16
            
            self.current_command_state = {
                'ticks_remaining': ticks,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveUpTimed: ticks={ticks}")
        
        state = self.current_command_state
        state['ticks_remaining'] -= 1
        
        if state['ticks_remaining'] <= 0:
            print(f"  [COMPLETE] MoveUpTimed")
            self.current_command_state = None
            return True
        
        current_pos = self.entity.get_world_pos()
        new_z = current_pos.z + state['speed']
        self.entity.set_world_pos(current_pos.x, current_pos.y, new_z, 0, 0, 0, 0, 0)
        
        return False
    
    def cmd_move_up_to_init_pos(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Move entity up to initial position
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] MoveUpToInitPos")
        return True
    
    def cmd_move_down_relative(self, params: Dict[str, Any]) -> bool:
        """Move entity down (decrease Z) by relative distance
        
        Args:
            params: Dictionary containing 'Distance' parameter (in tiles)
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            distance = params.get('Distance', 0.0)
            current_pos = self.entity.get_world_pos()
            target_z = current_pos.z - distance
            speed_per_frame = self.entity.speed / 16
            
            self.current_command_state = {
                'target_z': target_z,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveDownRelative: distance={distance:.3f}, from={current_pos.z:.3f} to={target_z:.3f}")
        
        state = self.current_command_state
        current_pos = self.entity.get_world_pos()
        
        distance_remaining = current_pos.z - state['target_z']
        
        if abs(distance_remaining) < state['speed']:
            self.entity.set_world_pos(
                current_pos.x, current_pos.y, state['target_z'],
                0, 0, 0, 0, 0
            )
            print(f"  [COMPLETE] MoveDownRelative: reached z={state['target_z']:.3f}")
            self.current_command_state = None
            return True
        
        new_z = current_pos.z - state['speed']
        self.entity.set_world_pos(current_pos.x, current_pos.y, new_z, 0, 0, 0, 0, 0)
        
        return False
    
    def cmd_move_down_absolute(self, params: Dict[str, Any]) -> bool:
        """Move entity down to absolute Z position
        
        Args:
            params: Dictionary containing 'Distance' parameter (absolute Z in tiles)
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            target_z = params.get('Distance', 0.0)
            current_pos = self.entity.get_world_pos()
            speed_per_frame = self.entity.speed / 16
            
            self.current_command_state = {
                'target_z': target_z,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveDownAbsolute: from={current_pos.z:.3f} to={target_z:.3f}")
        
        state = self.current_command_state
        current_pos = self.entity.get_world_pos()
        
        distance_remaining = current_pos.z - state['target_z']
        
        if abs(distance_remaining) < state['speed']:
            self.entity.set_world_pos(
                current_pos.x, current_pos.y, state['target_z'],
                0, 0, 0, 0, 0
            )
            print(f"  [COMPLETE] MoveDownAbsolute: reached z={state['target_z']:.3f}")
            self.current_command_state = None
            return True
        
        new_z = current_pos.z - state['speed']
        self.entity.set_world_pos(current_pos.x, current_pos.y, new_z, 0, 0, 0, 0, 0)
        
        return False
    
    def cmd_move_down_timed(self, params: Dict[str, Any]) -> bool:
        """Move entity down for specified ticks
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True if movement complete, False if still moving
        """
        if self.current_command_state is None:
            ticks = params.get('Ticks', 0)
            speed_per_frame = self.entity.speed / 16
            
            self.current_command_state = {
                'ticks_remaining': ticks,
                'speed': speed_per_frame
            }
            print(f"  [START] MoveDownTimed: ticks={ticks}")
        
        state = self.current_command_state
        state['ticks_remaining'] -= 1
        
        if state['ticks_remaining'] <= 0:
            print(f"  [COMPLETE] MoveDownTimed")
            self.current_command_state = None
            return True
        
        current_pos = self.entity.get_world_pos()
        new_z = current_pos.z - state['speed']
        self.entity.set_world_pos(current_pos.x, current_pos.y, new_z, 0, 0, 0, 0, 0)
        
        return False
    
    def cmd_move_down_until_collision(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Move entity down until collision
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] MoveDownUntilCollision")
        return True
    
    def cmd_move_to_xy_pos_immediate(self, params: Dict[str, Any]) -> bool:
        """Move entity to XY position immediately (teleport)
        
        Args:
            params: Dictionary containing 'X' and 'Y' coordinates (in tiles)
            
        Returns:
            True (instant command)
        """
        x = params.get('X', 0.0)
        y = params.get('Y', 0.0)
        current_pos = self.entity.get_world_pos()
        
        print(f"  [EXEC] MoveToXYPosImmedite: x={x:.3f}, y={y:.3f}")
        self.entity.set_world_pos(x, y, current_pos.z, 0, 0, 0, 0, 0)
        return True
    
    def cmd_move_to_z_pos_immediate(self, params: Dict[str, Any]) -> bool:
        """Move entity to Z position immediately (teleport)
        
        Args:
            params: Dictionary containing 'Z' coordinate (in tiles)
            
        Returns:
            True (instant command)
        """
        z = params.get('Z', 0.0)
        current_pos = self.entity.get_world_pos()
        
        print(f"  [EXEC] MoveToZPosImmediate: z={z:.3f}")
        self.entity.set_world_pos(current_pos.x, current_pos.y, z, 0, 0, 0, 0, 0)
        return True
    
    def cmd_set_target_position(self, params: Dict[str, Any]) -> bool:
        """Set target position for entity movement
        
        Args:
            params: Dictionary containing 'X', 'Y', 'Z' coordinates
            
        Returns:
            True (stub)
        """
        x = params.get('X', 0.0)
        y = params.get('Y', 0.0)
        z = params.get('Z', 0.0)
        print(f"  [STUB] SetTargetPosition: x={x:.3f}, y={y:.3f}, z={z:.3f}")
        return True
    
    def cmd_move_to_target_position(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Move entity to previously set target position
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] MoveToTargetPosition")
        return True
    
    def cmd_nudge_up(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Nudge entity up slightly
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] NudgeUp")
        return True
    
    def cmd_reset_to_initial_pos(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Reset entity to initial position
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] ResetToInitialPos")
        return True
    
    def cmd_jump(self, params: Dict[str, Any]) -> bool:
        """Make entity jump
        
        Args:
            params: Dictionary containing jump parameters
            
        Returns:
            True (instant command for now)
        """
        height = params.get('Height', 1.0)  # Height in tiles
        print(f"  [STUB] Jump: height={height:.3f} tiles")
        # TODO: Implement jump with physics
        return True
    
    # === Rotation Commands ===
    
    def cmd_turn_cw(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity clockwise (90 degrees)
        
        Returns:
            True (instant command)
        """
        rotation = {
            "NE": "SE",
            "SE": "SW",
            "SW": "NW",
            "NW": "NE",
        }

        print(f"  [EXEC] TurnCW: {self.entity.orientation} -> {rotation.get(self.entity.orientation)}")
        current = self.entity.orientation
        self.entity.orientation = rotation.get(current, current)
        return True
    
    def cmd_turn_cw_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity clockwise immediately (no animation)
        
        Returns:
            True (instant command)
        """
        return self.cmd_turn_cw(params)
    
    def cmd_turn_cw_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity clockwise without updating sprite
        
        Returns:
            True (instant command)
        """
        rotation = {
            "NE": "SE",
            "SE": "SW",
            "SW": "NW",
            "NW": "NE",
        }
        print(f"  [EXEC] TurnCWNoUpdate: {self.entity.orientation} -> {rotation.get(self.entity.orientation)}")
        current = self.entity.orientation
        self.entity.orientation = rotation.get(current, current)
        return True
    
    def cmd_turn_ccw(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity counter-clockwise (90 degrees)
        
        Returns:
            True (instant command)
        """
        rotation = {
            "NE": "NW",
            "NW": "SW",
            "SW": "SE",
            "SE": "NE",
        }

        print(f"  [EXEC] TurnCCW: {self.entity.orientation} -> {rotation.get(self.entity.orientation)}")
        current = self.entity.orientation
        self.entity.orientation = rotation.get(current, current)
        return True
    
    def cmd_turn_ccw_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity counter-clockwise immediately (no animation)
        
        Returns:
            True (instant command)
        """
        return self.cmd_turn_ccw(params)
    
    def cmd_turn_ccw_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity counter-clockwise without updating sprite
        
        Returns:
            True (instant command)
        """
        rotation = {
            "NE": "NW",
            "NW": "SW",
            "SW": "SE",
            "SE": "NE",
        }
        print(f"  [EXEC] TurnCCWNoUpdate: {self.entity.orientation} -> {rotation.get(self.entity.orientation)}")
        current = self.entity.orientation
        self.entity.orientation = rotation.get(current, current)
        return True
    
    def cmd_turn_180(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity 180 degrees (opposite direction)
        
        Returns:
            True (instant command)
        """
        rotation = {
            "NE": "SW",
            "SE": "NW",
            "SW": "NE",
            "NW": "SE",
        }

        print(f"  [EXEC] Turn180: {self.entity.orientation} -> {rotation.get(self.entity.orientation)}")
        current = self.entity.orientation
        self.entity.orientation = rotation.get(current, current)
        return True
    
    def cmd_turn_180_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity 180 degrees immediately (no animation)
        
        Returns:
            True (instant command)
        """
        return self.cmd_turn_180(params)
    
    def cmd_turn_180_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity 180 degrees without updating sprite
        
        Returns:
            True (instant command)
        """
        rotation = {
            "NE": "SW",
            "SE": "NW",
            "SW": "NE",
            "NW": "SE",
        }
        print(f"  [EXEC] Turn180NoUpdate: {self.entity.orientation} -> {rotation.get(self.entity.orientation)}")
        current = self.entity.orientation
        self.entity.orientation = rotation.get(current, current)
        return True
    
    def cmd_turn_ne(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face NE"""
        print(f"  [EXEC] TurnNE: {self.entity.orientation} -> NE")
        self.entity.orientation = 'NE'
        return True
    
    def cmd_turn_ne_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face NE immediately"""
        return self.cmd_turn_ne(params)
    
    def cmd_turn_ne_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face NE without updating sprite"""
        print(f"  [EXEC] TurnNENoUpdate: -> NE")
        self.entity.orientation = 'NE'
        return True
    
    def cmd_turn_nw(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face NW"""
        print(f"  [EXEC] TurnNW: {self.entity.orientation} -> NW")
        self.entity.orientation = 'NW'
        return True
    
    def cmd_turn_nw_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face NW immediately"""
        return self.cmd_turn_nw(params)
    
    def cmd_turn_nw_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face NW without updating sprite"""
        print(f"  [EXEC] TurnNWNoUpdate: -> NW")
        self.entity.orientation = 'NW'
        return True
    
    def cmd_turn_se(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face SE"""
        print(f"  [EXEC] TurnSE: {self.entity.orientation} -> SE")
        self.entity.orientation = 'SE'
        return True
    
    def cmd_turn_se_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face SE immediately"""
        return self.cmd_turn_se(params)
    
    def cmd_turn_se_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face SE without updating sprite"""
        print(f"  [EXEC] TurnSENoUpdate: -> SE")
        self.entity.orientation = 'SE'
        return True
    
    def cmd_turn_sw(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face SW"""
        print(f"  [EXEC] TurnSW: {self.entity.orientation} -> SW")
        self.entity.orientation = 'SW'
        return True
    
    def cmd_turn_sw_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face SW immediately"""
        return self.cmd_turn_sw(params)
    
    def cmd_turn_sw_no_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to face SW without updating sprite"""
        print(f"  [EXEC] TurnSWNoUpdate: -> SW")
        self.entity.orientation = 'SW'
        return True
    
    def cmd_turn_random(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to random direction"""
        import random
        directions = ['NE', 'SE', 'SW', 'NW']
        new_dir = random.choice(directions)
        print(f"  [EXEC] TurnRandom: {self.entity.orientation} -> {new_dir}")
        self.entity.orientation = new_dir
        return True
    
    def cmd_turn_random_immediate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Turn entity to random direction immediately"""
        return self.cmd_turn_random(params)
    
    def TurnSENoUpdate(self, params: Dict[str, Any] = None) -> bool:
        """Legacy: Turn entity to SE without updating position"""
        return self.cmd_turn_se_no_update(params)

    def cmd_turn_to_face(self, params: Dict[str, Any]) -> bool:
        """Turn entity to face a specific direction or target
        
        Args:
            params: Dictionary containing target or direction
            
        Returns:
            True (instant command for now)
        """
        target = params.get('Target', 'Player')
        print(f"  [STUB] TurnToFace: target={target}")
        return True
    
    def cmd_rotate_player(self, params: Dict[str, Any]) -> bool:
        """Rotate the player character
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] RotatePlayer: unknown={unknown}")
        return True
    
    def cmd_update_sprite_orientation(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Update sprite to match current orientation
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] UpdateSpriteOrientation")
        return True
    
    # === Timing Commands ===
    
    def cmd_pause(self, params: Dict[str, Any]) -> bool:
        """Pause script execution for specified ticks
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True if pause complete, False if still pausing
        """
        if self.current_command_state is None:
            ticks = params.get('Ticks', 0)
            self.current_command_state = {'ticks_remaining': ticks}
            print(f"  [START] Pause: {ticks} ticks")
        
        self.current_command_state['ticks_remaining'] -= 1
        
        if self.current_command_state['ticks_remaining'] <= 0:
            print(f"  [COMPLETE] Pause")
            self.current_command_state = None
            return True
        
        return False
    
    def cmd_pause_4s(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Pause script execution for 4 seconds
        
        Returns:
            True if pause complete, False if still pausing
        """
        # Assuming 60 FPS
        return self.cmd_pause({'Ticks': 240})
    
    def cmd_freeze(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Freeze entity (stop all movement/animation)
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] Freeze")
        return True
    
    # === Speed Commands ===
    
    def cmd_slow_speed(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Set entity speed to slow
        
        Returns:
            True (instant command)
        """
        self.entity.speed = 1
        print(f"  [EXEC] SlowSpeed: entity speed set to 1")
        return True
    
    def cmd_normal_speed(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Set entity speed to normal
        
        Returns:
            True (instant command)
        """
        self.entity.speed = 2
        print(f"  [EXEC] NormalSpeed: entity speed set to 2")
        return True
    
    def cmd_fast_speed(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Increase the movement speed for subsequent movement commands
        
        Returns:
            True (instant command)
        """
        if self.entity.speed < 3:   # Max speed
            self.entity.speed += 1
        print(f"  [EXEC] FastSpeed: entity speed set to {self.entity.speed} ({self.entity.speed/16:.1f} tiles/frame)")
        return True
    
    def cmd_xfast_speed(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Set entity speed to extra fast
        
        Returns:
            True (instant command)
        """
        self.entity.speed = 4
        print(f"  [EXEC] XFastSpeed: entity speed set to 4")
        return True
    
    def cmd_set_object_speed(self, params: Dict[str, Any]) -> bool:
        """Set the movement speed for the entity
        
        Args:
            params: Dictionary containing 'Unknown1' parameter (speed value)
            
        Returns:
            True (instant command)
        """
        speed = params.get('Unknown1', 1)
        self.entity.speed = speed
        print(f"  [EXEC] SetObjectSpeed: entity speed set to {speed}")
        return True
    
    # === Action Commands ===
    
    def cmd_play_animation(self, params: Dict[str, Any]) -> bool:
        """Play an animation on the entity
        
        Args:
            params: Dictionary containing animation parameters
            
        Returns:
            True (instant command)
        """
        anim_name = params.get('Name', 'Idle')
        print(f"  [STUB] PlayAnimation: animation={anim_name}")
        return True
    
    def cmd_play_sound(self, params: Dict[str, Any]) -> bool:
        """Play a sound effect
        
        Args:
            params: Dictionary containing sound parameters
            
        Returns:
            True (instant command)
        """
        sound_id = params.get('SoundID', 0)
        print(f"  [STUB] PlaySound: sound_id={sound_id}")
        return True
    
    def cmd_set_visible(self, params: Dict[str, Any]) -> bool:
        """Set entity visibility
        
        Args:
            params: Dictionary containing 'Visible' boolean
            
        Returns:
            True (instant command)
        """
        self.entity.visible = params.get('Visible', True)
        print(f"  [EXEC] SetVisible: visible={self.entity.visible}")
        return True
    
    def cmd_set_solid(self, params: Dict[str, Any]) -> bool:
        """Set entity collision state
        
        Args:
            params: Dictionary containing 'Solid' boolean
            
        Returns:
            True (instant command)
        """
        self.entity.solid = params.get('Solid', True)
        print(f"  [EXEC] SetSolid: solid={self.entity.solid}")
        return True
    
    def cmd_make_visible(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Make entity visible
        
        Returns:
            True (instant command)
        """
        self.entity.visible = True
        print(f"  [EXEC] MakeVisible: visible=True")
        return True
    
    def cmd_make_invisible(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Make entity invisible
        
        Returns:
            True (instant command)
        """
        self.entity.visible = False
        print(f"  [EXEC] MakeInvisible: visible=False")
        return True
    
    def cmd_hide(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Hide entity (same as make invisible)
        
        Returns:
            True (instant command)
        """
        self.entity.visible = False
        print(f"  [EXEC] Hide: visible=False")
        return True
    
    def cmd_remove_sprite(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Remove entity sprite
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] RemoveSprite")
        return True
    
    def cmd_show_when_collision_clear(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Show entity when collision is cleared
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] ShowWhenCollisionClear")
        return True
    
    # === Physics Commands ===
    
    def cmd_enable_gravity(self, params: Dict[str, Any] = None) -> bool:
        """Set entity gravity state
        
        Returns:
            True (instant command)
        """
        self.entity.gravity = True
        print(f"  [EXEC] EnableGravity: gravity enabled")
        return True
    
    def cmd_disable_gravity(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Disable entity gravity
        
        Returns:
            True (instant command)
        """
        self.entity.gravity = False
        print(f"  [EXEC] DisableGravity: gravity disabled")
        return True
    
    def cmd_enable_backwards_movement(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Enable backwards movement for entity
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] EnableBackwardsMovement")
        return True
    
    def cmd_disable_backwards_movement(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Disable backwards movement for entity
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] DisableBackwardsMovement")
        return True
    
    def cmd_enable_frame_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Enable frame updates for entity
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] EnableFrameUpdate")
        return True
    
    def cmd_disable_frame_update(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Disable frame updates for entity
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] DisableFrameUpdate")
        return True
    
    # === Visual Effects ===
    
    def cmd_flash_spin_appear(self, params: Dict[str, Any]) -> bool:
        """Flash and spin entity into view
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True (stub)
        """
        ticks = params.get('Ticks', 0)
        print(f"  [STUB] FlashSpinAppear: ticks={ticks}")
        return True
    
    def cmd_flash_spin_disappear(self, params: Dict[str, Any]) -> bool:
        """Flash and spin entity out of view
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True (stub)
        """
        ticks = params.get('Ticks', 0)
        print(f"  [STUB] FlashSpinDisappear: ticks={ticks}")
        return True
    
    def cmd_decay_flash(self, params: Dict[str, Any]) -> bool:
        """Create decaying flash effect
        
        Args:
            params: Dictionary containing 'Ticks' parameter
            
        Returns:
            True (stub)
        """
        ticks = params.get('Ticks', 0)
        print(f"  [STUB] DecayFlash: ticks={ticks}")
        return True
    
    # === Dialog/Interaction Commands ===
    
    def cmd_show_dialog(self, params: Dict[str, Any]) -> bool:
        """Display dialog text
        
        Args:
            params: Dictionary containing dialog parameters
            
        Returns:
            True (instant command)
        """
        dialog_id = params.get('DialogID', 0)
        text = params.get('Text', '')
        print(f"  [STUB] ShowDialog: dialog_id={dialog_id}, text='{text}'")
        return True
    
    def cmd_print_text(self, params: Dict[str, Any]) -> bool:
        """Print text string to screen
        
        Args:
            params: Dictionary containing 'String' parameter (string ID)
            
        Returns:
            True (stub)
        """
        string_id = params.get('String', 0)
        print(f"  [STUB] PrintText: string_id={string_id}")
        return True
    
    def cmd_give_item(self, params: Dict[str, Any]) -> bool:
        """Give item to player
        
        Args:
            params: Dictionary containing item parameters
            
        Returns:
            True (instant command)
        """
        item_id = params.get('ItemID', 0)
        quantity = params.get('Quantity', 1)
        print(f"  [STUB] GiveItem: item_id={item_id}, quantity={quantity}")
        return True
    
    def cmd_take_item(self, params: Dict[str, Any]) -> bool:
        """Take item from player
        
        Args:
            params: Dictionary containing item parameters
            
        Returns:
            True (instant command)
        """
        item_id = params.get('ItemID', 0)
        quantity = params.get('Quantity', 1)
        print(f"  [STUB] TakeItem: item_id={item_id}, quantity={quantity}")
        return True
    
    # === Conditional Commands ===
    
    def cmd_if_has_item(self, params: Dict[str, Any]) -> bool:
        """Check if player has specific item
        
        Args:
            params: Dictionary containing item check parameters
            
        Returns:
            True (instant command)
        """
        item_id = params.get('ItemID', 0)
        print(f"  [STUB] IfHasItem: item_id={item_id}")
        # TODO: Implement conditional logic
        return True
    
    def cmd_if_flag_set(self, params: Dict[str, Any]) -> bool:
        """Check if game flag is set
        
        Args:
            params: Dictionary containing flag parameters
            
        Returns:
            True (instant command)
        """
        flag_id = params.get('FlagID', 0)
        print(f"  [STUB] IfFlagSet: flag_id={flag_id}")
        return True
    
    def cmd_wait_for_flag_set(self, params: Dict[str, Any]) -> bool:
        """Wait for a flag to be set before continuing
        
        Args:
            params: Dictionary containing 'Flag' parameter
            
        Returns:
            False (stub - always waiting)
        """
        flag_id = params.get('Flag', 0)
        print(f"  [STUB] WaitForFlagSet: flag={flag_id}")
        return True
    
    def cmd_wait_for_flag_clear(self, params: Dict[str, Any]) -> bool:
        """Wait for a flag to be cleared before continuing
        
        Args:
            params: Dictionary containing 'Flag' parameter
            
        Returns:
            False (stub - always waiting)
        """
        flag_id = params.get('Flag', 0)
        print(f"  [STUB] WaitForFlagClear: flag={flag_id}")
        return True
    
    # === Flag Commands ===
    
    def cmd_set_flag(self, params: Dict[str, Any]) -> bool:
        """Set a game flag
        
        Args:
            params: Dictionary containing 'Flag' parameter
            
        Returns:
            True (stub)
        """
        flag_id = params.get('Flag', 0)
        print(f"  [STUB] SetFlag: flag={flag_id}")
        return True
    
    def cmd_clear_flag(self, params: Dict[str, Any]) -> bool:
        """Clear a game flag
        
        Args:
            params: Dictionary containing 'Flag' parameter
            
        Returns:
            True (stub)
        """
        flag_id = params.get('Flag', 0)
        print(f"  [STUB] ClearFlag: flag={flag_id}")
        return True
    
    # === Switch Commands ===
    
    def cmd_activate_switch(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Activate a switch in the level
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] ActivateSwitch")
        return True
    
    def cmd_reset_switch(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Reset a switch in the level
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] ResetSwitch")
        return True
    
    # === Cutscene Commands ===
    
    def cmd_start_cutscene(self, params: Dict[str, Any]) -> bool:
        """Start a cutscene
        
        Args:
            params: Dictionary containing 'Cutscene' parameter
            
        Returns:
            True (stub)
        """
        cutscene_id = params.get('Cutscene', 0)
        print(f"  [STUB] StartCutscene: cutscene={cutscene_id}")
        return True
    
    def cmd_start_hi_cutscene(self, params: Dict[str, Any]) -> bool:
        """Start a high-quality cutscene
        
        Args:
            params: Dictionary containing 'Cutscene' parameter
            
        Returns:
            True (stub)
        """
        cutscene_id = params.get('Cutscene', 0)
        print(f"  [STUB] StartHiCutscene: cutscene={cutscene_id}")
        return True
    
    # === Level Manipulation ===
    
    def cmd_trigger_tile_swap(self, params: Dict[str, Any]) -> bool:
        """Trigger a tile swap in the level
        
        Args:
            params: Dictionary containing 'Swap' parameter
            
        Returns:
            True (stub)
        """
        swap_id = params.get('Swap', 0)
        print(f"  [STUB] TriggerTileSwap: swap={swap_id}")
        return True
    
    # === Player Control ===
    
    def cmd_follow_player_no_jump(self, params: Dict[str, Any]) -> bool:
        """Make entity follow player without jumping
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] FollowPlayerNoJump: unknown={unknown}")
        return True
    
    def cmd_follow_player_with_jump(self, params: Dict[str, Any]) -> bool:
        """Make entity follow player with jumping
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] FollowPlayerWithJump: unknown={unknown}")
        return True
    
    def cmd_playback_input(self, params: Dict[str, Any]) -> bool:
        """Playback recorded input script
        
        Args:
            params: Dictionary containing 'InputScript' parameter
            
        Returns:
            True (stub)
        """
        script_id = params.get('InputScript', 0)
        print(f"  [STUB] PlaybackInput: script={script_id}")
        return True
    
    def cmd_reset_playback(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Reset input playback to start
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] ResetPlayback")
        return True
    
    def cmd_wait_for_condition(self, params: Dict[str, Any]) -> bool:
        """Wait for a specific condition to be met before continuing
        
        Condition types:
        1 - Wait for hero to stand on this entity
        
        Args:
            params: Dictionary containing 'Condition' parameter
            
        Returns:
            False until condition is met, then True
        """
        condition = params.get('Condition', 0)
        
        # First time this command is executed
        if self.current_command_state is None:
            self.waiting_for_condition = True
            self.wait_condition_type = condition
            self.should_loop = False  # Disable looping when waiting for condition
            self.current_command_state = {'condition': condition}
            print(f"  [START] WaitForCondition: condition={condition} (script paused)")
            return False  # Don't advance to next command
        
        # Check if condition is met (this will be called from game.py)
        # For now, just return False to keep waiting
        return False
    
    def trigger_condition(self, condition_type: int) -> None:
        """External trigger for conditions (called from game.py)
        
        Args:
            condition_type: The condition type that was triggered
        """
        if self.waiting_for_condition and self.wait_condition_type == condition_type:
            print(f"  [COMPLETE] WaitForCondition: condition={condition_type} met")
            self.waiting_for_condition = False
            self.wait_condition_type = None
            self.current_command_state = None  # Clear command state
            # Move to next command
            self.current_command_index += 1
    
    # === Flow Control Commands ===
    
    def cmd_goto_command(self, params: Dict[str, Any]) -> bool:
        """Jump to a specific command index
        
        Args:
            params: Dictionary containing 'Command' parameter
            
        Returns:
            True (instant command)
        """
        index = params.get('Command', 0)
        print(f"  [EXEC] GotoCommand: command={index}")
        self.current_command_index = index - 1  # -1 because it will be incremented
        return True
    
    def cmd_repeat_begin(self, params: Dict[str, Any]) -> bool:
        """Begin a repeat loop
        
        Args:
            params: Dictionary containing 'Repetitions' parameter
            
        Returns:
            True (stub)
        """
        repetitions = params.get('Repetitions', 1)
        print(f"  [STUB] RepeatBegin: repetitions={repetitions}")
        return True
    
    def cmd_repeat_end(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """End a repeat loop
        
        Returns:
            True (stub)
        """
        print(f"  [STUB] RepeatEnd")
        return True
    
    def cmd_loop(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Loop back to beginning of script
        
        Returns:
            True (instant command)
        """
        print(f"  [EXEC] Loop: restarting script")
        self.current_command_index = -1  # Will be incremented to 0
        return True
    
    def cmd_end(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """End script execution
        
        Returns:
            True (instant command)
        """
        print(f"  [EXEC] End: terminating script")
        self.is_running = False
        return True
    
    # === Unknown Commands (Stubs) ===
    
    def cmd_unknown_5a(self, params: Dict[str, Any]) -> bool:
        """Unknown command 5A
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] Unknown5A: unknown={unknown}")
        return True
    
    def cmd_unknown_b33(self, params: Dict[str, Any]) -> bool:
        """Unknown command B33
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] UnknownB33: unknown={unknown}")
        return True
    
    def cmd_unknown_b47(self, params: Dict[str, Any]) -> bool:
        """Unknown command B47
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] UnknownB47: unknown={unknown}")
        return True
    
    def cmd_unknown_b63(self, params: Dict[str, Any]) -> bool:
        """Unknown command B63
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] UnknownB63: unknown={unknown}")
        return True
    
    def cmd_unknown_b65(self, params: Dict[str, Any]) -> bool:
        """Unknown command B65
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] UnknownB65: unknown={unknown}")
        return True
    
    def cmd_unknown_b66(self, params: Dict[str, Any]) -> bool:
        """Unknown command B66
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] UnknownB66: unknown={unknown}")
        return True
    
    def cmd_unknown_b67(self, params: Dict[str, Any]) -> bool:
        """Unknown command B67
        
        Args:
            params: Dictionary containing 'Unknown' parameter
            
        Returns:
            True (stub)
        """
        unknown = params.get('Unknown', 0)
        print(f"  [STUB] UnknownB67: unknown={unknown}")
        return True
    
    # === Script Execution ===
    
    def start_script(self, script_commands: list, should_loop: bool = True) -> None:
        """Start executing a script
        
        Args:
            script_commands: List of commands to execute
            should_loop: If True, script will loop when it reaches the end (default: True)
        """
        # Don't restart if already running
        if self.is_running:
            return
        
        self.script_commands = script_commands
        self.current_command_index = 0
        self.current_command_state = None
        self.is_running = True
        self.should_loop = should_loop
        self.waiting_for_condition = False
        self.wait_condition_type = None
        print(f"\n=== Starting Script with {len(script_commands)} commands (loop={should_loop}) ===")
    
    def update(self) -> None:
        """Update script execution (call this every frame)"""
        if not self.is_running or not self.script_commands:
            return
        
        # Don't advance if waiting for condition
        if self.waiting_for_condition:
            return
        
        # Check if we've finished all commands
        if self.current_command_index >= len(self.script_commands):
            if self.should_loop:
                print(f"=== Script Loop: Restarting ===\n")
                self.current_command_index = 0
                self.current_command_state = None
            else:
                print(f"=== Script Complete ===\n")
                self.is_running = False
            return
        
        # Get current command
        command = self.script_commands[self.current_command_index]
        
        # Execute command
        command_complete = self.execute_command(command)
        
        # Move to next command if current one is complete
        if command_complete:
            self.current_command_index += 1
            self.current_command_state = None
    
    def execute_command(self, command: Any) -> bool:
        """Execute a single script command
        
        Args:
            command: Command string or dictionary from script
            
        Returns:
            True if command is complete, False if it needs more frames
        """
        if isinstance(command, str):
            # Simple command without parameters
            handler = self.command_handlers.get(command)
            if handler:
                return handler()
            else:
                print(f"  [WARNING] Unknown command: {command}")
                return True  # Skip unknown commands
        
        elif isinstance(command, dict):
            # Complex command with parameters
            for cmd_name, cmd_params in command.items():
                handler = self.command_handlers.get(cmd_name)
                if handler:
                    return handler(cmd_params)
                else:
                    print(f"  [WARNING] Unknown command: {cmd_name}")
                    return True  # Skip unknown commands
        
        return True  # Default: command complete