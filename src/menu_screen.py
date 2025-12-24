import pygame
import pygame_gui
from pygame_gui.elements.ui_text_box import UITextBox


class MenuScreen:
    """Menu screen with HUD, main area, and footer sections"""
    
    def __init__(self, display_width: int, display_height: int):
        """Initialize the menu screen
        
        Args:
            display_width: Width of the display
            display_height: Height of the display
        """
        self.display_width = display_width
        self.display_height = display_height
        
        # Calculate section heights
        self.hud_height = 36  # Same as game HUD
        self.footer_height = self.hud_height * 3  # 3 times HUD height
        self.main_height = display_height - self.hud_height - self.footer_height
        
        # GUI Manager for menu
        self.manager = pygame_gui.UIManager((display_width, display_height), "ui.json")
        
        # HUD section (top) - same as in game
        self.hud_textbox = UITextBox(
            "",
            pygame.Rect((0, 0), (display_width, self.hud_height)),
            manager=self.manager,
            object_id="#hud_textbox",
        )
        
        # Coordinate label in HUD
        self.coord_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 2), (-1, -1)),
            text="MENU",
            manager=self.manager
        )
        
        # Main section (middle) - empty for now
        # Future: add inventory, stats, etc.
        
        # Footer section (bottom) - empty for now
        # Future: add controls, messages, etc.
    
    def handle_input(self, keys: pygame.key.ScancodeWrapper, prev_keys: dict) -> bool:
        """Handle menu input
        
        Args:
            keys: Current key states
            prev_keys: Previous frame key states
            
        Returns:
            True if menu should remain open, False to close
        """
        # Check if B key was just pressed
        was_pressed = prev_keys.get(pygame.K_b, False)
        is_pressed = keys[pygame.K_b]
        
        if is_pressed and not was_pressed:
            return False  # Close menu
        
        return True  # Keep menu open
    
    def update(self, time_delta: float):
        """Update menu GUI
        
        Args:
            time_delta: Time since last frame in seconds
        """
        self.manager.update(time_delta)
    
    def render(self, surface: pygame.Surface):
        """Render the menu
        
        Args:
            surface: Surface to render to
        """
        # Fill background
        surface.fill((20, 20, 40))  # Dark blue background
        
        # Draw section dividers (for debugging/visibility)
        # HUD bottom border
        pygame.draw.line(
            surface,
            (100, 100, 100),
            (0, self.hud_height),
            (self.display_width, self.hud_height),
            2
        )
        
        # Footer top border
        footer_y = self.display_height - self.footer_height
        pygame.draw.line(
            surface,
            (100, 100, 100),
            (0, footer_y),
            (self.display_width, footer_y),
            2
        )
        
        # Draw GUI elements
        self.manager.draw_ui(surface)
    
    def process_events(self, event: pygame.event.Event):
        """Process pygame events for the menu
        
        Args:
            event: Pygame event to process
        """
        self.manager.process_events(event)