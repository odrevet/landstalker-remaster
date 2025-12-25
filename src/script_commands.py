"""
Script command handlers for entity behaviors
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
            
            # Timing commands
            'Pause': self.cmd_pause,
            'Pause4s': self.cmd_pause_4s,
            
            # Action commands
            'PlayAnimation': self.cmd_play_animation,
            'PlaySound': self.cmd_play_sound,
            'SetVisible': self.cmd_set_visible,
            'SetSolid': self.cmd_set_solid,
            
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
    
    def cmd_move_relative(self, params: Dict[str, Any]) -> None:
        """Move entity relative to current position
        
        Args:
            params: Dictionary containing 'Distance' parameter
        """
        distance = params.get('Distance', 0.0)
        print(f"  [EXEC] MoveRelative: distance={distance} tiles")
        
        # Get current orientation to determine movement direction
        # Orientations in isometric: NE, SE, SW, NW
        orientation = self.entity.orientation

        print(f"current orientation is {orientation}")
        
        # Calculate direction vector based on orientation
        # In tile coordinates (x, y)
        direction_map = {
            'NE': (0, -1), 
            'SE': (0, 1), 
            'SW': (1, 0),
            'NW': (-1, 0),
        }
        
        dx, dy = direction_map.get(orientation, (0.0, 0.0))
        
        print(f"move {dx} {dy}")

        # Update entity's tile position
        self.entity.add_world_x(dx * distance) 
        self.entity.add_world_y(dy * distance) 
    
    def cmd_move_absolute(self, params: Dict[str, Any]) -> None:
        """Move entity to absolute position
        
        Args:
            params: Dictionary containing 'X', 'Y', 'Z' coordinates
        """
        x = params.get('X', 0.0)
        y = params.get('Y', 0.0)
        z = params.get('Z', 0.0)
        print(f"  [STUB] MoveAbsolute: x={x}, y={y}, z={z}")
        # TODO: Implement absolute position movement
        # self.entity.set_position(x, y, z)
    
    def cmd_jump(self, params: Dict[str, Any]) -> None:
        """Make entity jump
        
        Args:
            params: Dictionary containing jump parameters
        """
        height = params.get('Height', 1.0)
        print(f"  [STUB] Jump: height={height}")
        # TODO: Implement jump with physics
        # self.entity.jump(height)
    
    # === Rotation Commands ===
    
    def cmd_turn_cw(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Turn entity clockwise (90 degrees)"""
        rotation = {
            "N":  "E",
            "NE": "SE",
            "E":  "S",
            "SE": "SW",
            "S":  "W",
            "SW": "NW",
            "W":  "N",
            "NW": "NE",
        }

        print("turn clockwise")

        current = self.entity.orientation
        self.entity.orientation = rotation.get(current)

    
    def cmd_turn_ccw(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Turn entity counter-clockwise (90 degrees)"""
        rotation = {
            "N":  "W",
            "NW": "SW",
            "W":  "S",
            "SW": "SE",
            "S":  "E",
            "SE": "NE",
            "E":  "N",
            "NE": "NW",
        }

        print("turn counter clockwise")

        current = self.entity.orientation
        self.entity.orientation = rotation.get(current)
    
    def cmd_turn_to_face(self, params: Dict[str, Any]) -> None:
        """Turn entity to face a specific direction or target
        
        Args:
            params: Dictionary containing target or direction
        """
        target = params.get('Target', 'Player')
        print(f"  [STUB] TurnToFace: target={target}")
        # TODO: Implement turning to face target
        # self.entity.face_target(target)
    
    # === Timing Commands ===
    
    def cmd_pause(self, params: Dict[str, Any]) -> None:
        """Pause script execution for specified ticks
        
        Args:
            params: Dictionary containing 'Ticks' parameter
        """
        ticks = params.get('Ticks', 0)
        print(f"  [STUB] Pause: ticks={ticks}")
        # TODO: Implement pause/wait mechanism
        # self.entity.pause(ticks)
    
    def cmd_pause_4s(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Pause script execution for 4 seconds
        
        Args:
            params: Optional parameters (not used)
        """
        print(f"  [STUB] Pause4s: pausing for 4 seconds")
        # TODO: Implement 4 second pause
        # self.entity.pause(240)  # Assuming 60 ticks per second
    
    # === Action Commands ===
    
    def cmd_play_animation(self, params: Dict[str, Any]) -> None:
        """Play an animation on the entity
        
        Args:
            params: Dictionary containing animation parameters
        """
        anim_name = params.get('Name', 'Idle')
        print(f"  [STUB] PlayAnimation: animation={anim_name}")
        # TODO: Implement animation playback
        # self.entity.play_animation(anim_name)
    
    def cmd_play_sound(self, params: Dict[str, Any]) -> None:
        """Play a sound effect
        
        Args:
            params: Dictionary containing sound parameters
        """
        sound_id = params.get('SoundID', 0)
        print(f"  [STUB] PlaySound: sound_id={sound_id}")
        # TODO: Implement sound playback
        # self.entity.play_sound(sound_id)
    
    def cmd_set_visible(self, params: Dict[str, Any]) -> None:
        """Set entity visibility
        
        Args:
            params: Dictionary containing 'Visible' boolean
        """
        visible = params.get('Visible', True)
        print(f"  [STUB] SetVisible: visible={visible}")
        # TODO: Implement visibility toggle
        # self.entity.visible = visible
    
    def cmd_set_solid(self, params: Dict[str, Any]) -> None:
        """Set entity collision state
        
        Args:
            params: Dictionary containing 'Solid' boolean
        """
        solid = params.get('Solid', True)
        print(f"  [STUB] SetSolid: solid={solid}")
        # TODO: Implement collision toggle
        # self.entity.solid = solid
    
    # === Dialog/Interaction Commands ===
    
    def cmd_show_dialog(self, params: Dict[str, Any]) -> None:
        """Display dialog text
        
        Args:
            params: Dictionary containing dialog parameters
        """
        dialog_id = params.get('DialogID', 0)
        text = params.get('Text', '')
        print(f"  [STUB] ShowDialog: dialog_id={dialog_id}, text='{text}'")
        # TODO: Implement dialog display
        # self.entity.show_dialog(dialog_id, text)
    
    def cmd_give_item(self, params: Dict[str, Any]) -> None:
        """Give item to player
        
        Args:
            params: Dictionary containing item parameters
        """
        item_id = params.get('ItemID', 0)
        quantity = params.get('Quantity', 1)
        print(f"  [STUB] GiveItem: item_id={item_id}, quantity={quantity}")
        # TODO: Implement item giving
        # player.inventory.add_item(item_id, quantity)
    
    def cmd_take_item(self, params: Dict[str, Any]) -> None:
        """Take item from player
        
        Args:
            params: Dictionary containing item parameters
        """
        item_id = params.get('ItemID', 0)
        quantity = params.get('Quantity', 1)
        print(f"  [STUB] TakeItem: item_id={item_id}, quantity={quantity}")
        # TODO: Implement item taking
        # player.inventory.remove_item(item_id, quantity)
    
    # === Conditional Commands ===
    
    def cmd_if_has_item(self, params: Dict[str, Any]) -> bool:
        """Check if player has specific item
        
        Args:
            params: Dictionary containing item check parameters
            
        Returns:
            True if player has item, False otherwise
        """
        item_id = params.get('ItemID', 0)
        print(f"  [STUB] IfHasItem: item_id={item_id}")
        # TODO: Implement item check
        # return player.inventory.has_item(item_id)
        return False
    
    def cmd_if_flag_set(self, params: Dict[str, Any]) -> bool:
        """Check if game flag is set
        
        Args:
            params: Dictionary containing flag parameters
            
        Returns:
            True if flag is set, False otherwise
        """
        flag_id = params.get('FlagID', 0)
        print(f"  [STUB] IfFlagSet: flag_id={flag_id}")
        # TODO: Implement flag check
        # return game_state.is_flag_set(flag_id)
        return False
    
    # === Flow Control Commands ===
    
    def cmd_goto(self, params: Dict[str, Any]) -> None:
        """Jump to a specific command index
        
        Args:
            params: Dictionary containing 'Index' parameter
        """
        index = params.get('Index', 0)
        print(f"  [STUB] Goto: index={index}")
        # TODO: Implement script jump
        # self.script_index = index
    
    def cmd_loop(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Loop back to beginning of script
        
        Args:
            params: Optional parameters
        """
        print(f"  [STUB] Loop: restarting script")
        # TODO: Implement script loop
        # self.script_index = 0
    
    def cmd_end(self, params: Optional[Dict[str, Any]] = None) -> None:
        """End script execution
        
        Args:
            params: Optional parameters
        """
        print(f"  [STUB] End: terminating script")
        # TODO: Implement script termination
        # self.script_running = False
    
    # === Command Execution ===
    
    def execute_command(self, command: Any) -> None:
        """Execute a single script command
        
        Args:
            command: Command string or dictionary from script
        """
        if isinstance(command, str):
            # Simple command without parameters
            handler = self.command_handlers.get(command)
            if handler:
                handler()
            else:
                print(f"  [WARNING] Unknown command: {command}")
        
        elif isinstance(command, dict):
            # Complex command with parameters
            for cmd_name, cmd_params in command.items():
                handler = self.command_handlers.get(cmd_name)
                if handler:
                    handler(cmd_params)
                else:
                    print(f"  [WARNING] Unknown command: {cmd_name}")


def run_entity_script(entity, behaviour_id: int) -> dict:
    """Load and execute entity script commands from YAML file
    
    Args:
        entity: The entity executing the script
        behaviour_id: Behavior ID to load
        
    Returns:
        Dictionary containing the parsed script data
    """
    filepath = f"data/scripts/behaviour{behaviour_id}.yaml"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            print(f"Warning: Empty script file at {filepath}")
            return {}
        
        script_commands = data.get('Script', [])
        
        if not script_commands:
            print(f"Warning: No 'Script' key found in {filepath}")
            return data
        
        print(f"\n=== Executing Behaviour {behaviour_id} ===")
        print(f"Name: {data.get('Name', 'Unknown')}")
        print(f"Total Commands: {len(script_commands)}\n")
        
        # Create command handler for this entity
        cmd_handler = ScriptCommands(entity)
        
        # Loop through and execute each command
        for cmd_index, command in enumerate(script_commands, start=1):
            print(f"Command #{cmd_index}:")
            cmd_handler.execute_command(command)
            print()  # Empty line between commands
        
        print(f"=== End of Behaviour {behaviour_id} ===\n")
        
        return data
        
    except FileNotFoundError:
        print(f"Warning: entity script file not found at {filepath}")
        return {}
    except Exception as e:
        print(f"Error loading script: {e}")
        import traceback
        traceback.print_exc()
        return {}