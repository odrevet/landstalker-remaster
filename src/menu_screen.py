import pygame
import pygame_gui
from pygame_gui.elements.ui_text_box import UITextBox
from typing import Optional

class MenuScreen:
    """Menu screen with HUD, main area, and footer sections styled like game HUD"""
    
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
        self.footer_height = 60
        self.main_height = display_height - self.hud_height - self.footer_height
        
        # GUI Manager for menu
        self.manager = pygame_gui.UIManager((display_width, display_height), "ui.json")
        
        # === HUD SECTION (TOP) ===
        self.hud_textbox = UITextBox(
            "",
            pygame.Rect((0, 0), (display_width, self.hud_height)),
            manager=self.manager,
            object_id="#hud_textbox",
        )
        
        self.hud_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((10, 8), (-1, -1)),
            text="",
            manager=self.manager
        )
        
        # === MAIN SECTION (MIDDLE) ===
        main_y = self.hud_height
        
        self.main_textbox = UITextBox(
            "",
            pygame.Rect((0, main_y), (display_width, self.main_height)),
            manager=self.manager,
            object_id="#dialog_textbox",  # Reuse dialog style
        )
        
        # Menu content label
        menu_content = ("")
        
        self.main_content_label = pygame_gui.elements.UILabel(
            text=menu_content,
            relative_rect=pygame.Rect((10, main_y + 10), (display_width - 20, self.main_height - 20)),
            manager=self.manager,
            object_id="#menu_content"
        )
        
        # === FOOTER SECTION (BOTTOM) ===
        footer_y = display_height - self.footer_height
        
        self.footer_textbox = UITextBox(
            "",
            pygame.Rect((0, footer_y), (display_width, self.footer_height)),
            manager=self.manager,
            object_id="#dialog_textbox",  # Reuse dialog style
        )
        
        footer_text = (
            "USE    EQUIPE"
        )
        
        self.footer_label = pygame_gui.elements.UILabel(
            text=footer_text,
            relative_rect=pygame.Rect((10, footer_y + 10), (display_width - 20, self.footer_height - 20)),
            manager=self.manager,
            object_id="#menu_footer"
        )
    
    def handle_input(self, keys: pygame.key.ScancodeWrapper, prev_keys: dict) -> bool:
        """Handle menu input
        
        Args:
            keys: Current key states
            prev_keys: Previous frame key states
            
        Returns:
            True if menu should remain open, False to close
        """
        # Check if B key was just pressed (close menu)
        was_b_pressed = prev_keys.get(pygame.K_b, False)
        is_b_pressed = keys[pygame.K_b]
        
        if is_b_pressed and not was_b_pressed:
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
        # Fill background with dark color
        surface.fill((10, 10, 20))
        
        # Draw GUI elements (textboxes will render their backgrounds)
        self.manager.draw_ui(surface)
    
    def process_events(self, event: pygame.event.Event):
        """Process pygame events for the menu
        
        Args:
            event: Pygame event to process
        """
        self.manager.process_events(event)
    
    def recreate_for_resolution(self, display_width: int, display_height: int):
        """Recreate menu elements for new resolution
        
        Args:
            display_width: New display width
            display_height: New display height
        """
        self.display_width = display_width
        self.display_height = display_height
        
        # Recalculate heights
        self.main_height = display_height - self.hud_height - self.footer_height
        
        # Recreate manager
        self.manager = pygame_gui.UIManager((display_width, display_height), "ui.json")
        
        # Recreate all UI elements
        self.__init__(display_width, display_height)