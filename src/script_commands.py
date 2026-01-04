"""
Script command handlers for entity behaviors with smooth tile-based movement
"""
from typing import Dict, Any, Optional
import yaml


class ScriptCommands:
    """Handles execution of entity script commands"""
    
    def __init__(self, entity):
        """Initialize script command handler
        
        Args:
            entity: The entity that will execute these commands
        """
        self.entity = entity
        
        # Script execution state
        self.is_running = False
        self.current_command_index = 0
        self.current_command_state = None  # Stores state for ongoing commands
        self.script_commands = []
        self.paused = False
        self.pause_ticks_remaining = 0
        self.one_shot = False
        self.has_been_triggered = False  # Track if one-shot script has run
        
        # Command dispatcher - maps command names to handler methods
        self.command_handlers = {
            # Movement commands
            'MoveRelative': self.cmd_move_relative,
            'MoveAbsolute': self.cmd_move_absolute,
            'Jump': self.cmd_jump,
            
            # Rotation commands
            'TurnCW': self.cmd_turn_cw,
            'TurnCCW': self.cmd_turn_ccw,
            'TurnToFace': self.cmd_turn_to_face,
            'TurnSENoUpdate': self.TurnSENoUpdate,
            
            # Timing commands
            'Pause': self.cmd_pause,
            'Pause4s': self.cmd_pause_4s,
            
            # Speed commands
            'FastSpeed': self.cmd_fast_speed,
            
            # Action commands
            'PlayAnimation': self.cmd_play_animation,
            'PlaySound': self.cmd_play_sound,
            'SetVisible': self.cmd_set_visible,
            'SetSolid': self.cmd_set_solid,
            'EnableGravity': self.cmd_enable_gravity,
            
            # Dialog/Interaction commands
            'ShowDialog': self.cmd_show_dialog,
            'GiveItem': self.cmd_give_item,
            'TakeItem': self.cmd_take_item,
            
            # Conditional commands
            'IfHasItem': self.cmd_if_has_item,
            'IfFlagSet': self.cmd_if_flag_set,
            
            # Flow control
            'Goto': self.cmd_goto,
            'Loop': self.cmd_loop,
            'End': self.cmd_end,
        }
    
    # === Movement Commands ===
    
    def cmd_move_relative(self, params: Dict[str, Any]) -> bool:
        """Move entity relative to current position (smoothly over time)
        
        All coordinates are in tiles. Movement speed is in tiles per frame.
        
        Args:
            params: Dictionary containing 'Distance' parameter (in tiles)
            
        Returns:
            True if command is complete, False if still in progress
        """
        # Initialize command state on first call
        if self.current_command_state is None:
            distance = params.get('Distance', 0.0)  # Distance in tiles
            orientation = self.entity.orientation
            
            # Direction vectors for isometric movement
            direction_map = {
                'NE': (0, -1),  # Move north-east
                'SE': (1, 0),   # Move south-east
                'SW': (0, 1),   # Move south-west
                'NW': (-1, 0),  # Move north-west
            }
            
            dx, dy = direction_map.get(orientation, (0.0, 0.0))
            
            # Calculate target position in tiles
            current_pos = self.entity.get_world_pos()
            target_x = current_pos.x + (dx * distance)
            target_y = current_pos.y + (dy * distance)
            
            # Movement speed in tiles per frame
            speed_per_frame = self.entity.speed / 16  # Convert entity speed to block per frame
            
            self.current_command_state = {
                'target_x': target_x,
                'target_y': target_y,
                'dx': dx,
                'dy': dy,
                'speed': speed_per_frame
            }
            
            print(f"  [START] MoveRelative: distance={distance:.3f} tiles, "
                  f"target=({target_x:.3f}, {target_y:.3f}), speed={speed_per_frame:.3f} tiles/frame")
        
        # Continue moving toward target
        state = self.current_command_state
        current_pos = self.entity.get_world_pos()
        
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
    
    def TurnSENoUpdate(self, params: Dict[str, Any] = None) -> bool:
        """Turn entity to SE without updating position"""
        self.entity.orientation = 'SE'
        return True

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
    
    # === Speed Commands ===
    
    def cmd_fast_speed(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """Increase the movement speed for subsequent movement commands
        
        Returns:
            True (instant command)
        """
        if self.entity.speed < 3:   # Max speed
            self.entity.speed += 1
        print(f"  [EXEC] FastSpeed: entity speed set to {self.entity.speed} ({self.entity.speed/16:.1f} tiles/frame)")
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

    def cmd_enable_gravity(self, params: Dict[str, Any] = None) -> bool:
        """Set entity gravity state
        
        Returns:
            True (instant command)
        """
        self.entity.gravity = True
        print(f"  [EXEC] EnableGravity: gravity enabled")
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
    
    # === Flow Control Commands ===
    
    def cmd_goto(self, params: Dict[str, Any]) -> bool:
        """Jump to a specific command index
        
        Args:
            params: Dictionary containing 'Index' parameter
            
        Returns:
            True (instant command)
        """
        index = params.get('Index', 0)
        print(f"  [EXEC] Goto: index={index}")
        self.current_command_index = index - 1  # -1 because it will be incremented
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
    
    # === Script Execution ===
    
    def start_script(self, script_commands: list, one_shot: bool = False) -> None:
        """Start executing a script
        
        Args:
            script_commands: List of commands to execute
            one_shot: If True, script can only be triggered once
        """
        # Don't restart if already running
        if self.is_running:
            return
        
        # Don't restart if one-shot and already triggered
        if one_shot and self.has_been_triggered:
            return
        
        self.script_commands = script_commands
        self.current_command_index = 0
        self.current_command_state = None
        self.is_running = True
        self.one_shot = one_shot
        print(f"\n=== Starting Script with {len(script_commands)} commands ===")
    
    def update(self) -> None:
        """Update script execution (call this every frame)"""
        if not self.is_running or not self.script_commands:
            return
        
        # Check if we've finished all commands
        if self.current_command_index >= len(self.script_commands):
            print(f"=== Script Complete ===\n")
            self.is_running = False
            
            # Mark as triggered if one-shot
            if self.one_shot:
                self.has_been_triggered = True
            
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


def run_entity_script(entity, behaviour_id: int, one_shot: bool = True) -> None:
    """Load and start entity script execution from YAML file
    
    Args:
        entity: The entity executing the script
        behaviour_id: Behavior ID to load
        one_shot: If True, script can only be triggered once (default: True)
    """
    if not hasattr(entity, 'script_handler') or not entity.script_handler.is_running:
        filepath = f"data/scripts/behaviour{behaviour_id}.yaml"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                print(f"Warning: Empty script file at {filepath}")
                return
            
            script_commands = data.get('Script', [])
            
            if not script_commands:
                print(f"Warning: No 'Script' key found in {filepath}")
                return
            
            # Create command handler if entity doesn't have one
            if not hasattr(entity, 'script_handler'):
                entity.script_handler = ScriptCommands(entity)
            
            # Start the script with one-shot flag
            entity.script_handler.start_script(script_commands, one_shot=one_shot)
            
        except FileNotFoundError:
            print(f"Warning: entity script file not found at {filepath}")
        except Exception as e:
            print(f"Error loading script: {e}")
            import traceback
            traceback.print_exc()