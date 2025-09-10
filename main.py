import pygame
import json
import os
import random
import textwrap
import time
import re

# --- Constants ---
LOGICAL_WIDTH = 1920
LOGICAL_HEIGHT = 1080
CARD_PREVIEW_WIDTH = 300
CARD_PREVIEW_HEIGHT = 428
CARD_HAND_WIDTH = 120
CARD_HAND_HEIGHT = 170
FPS = 60

# --- Colors ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
PLAYER_ZONE_COLOR = (0, 70, 130, 150)
ENEMY_ZONE_COLOR = (130, 0, 30, 150)
REIRYOKU_ZONE_COLOR = (200, 200, 100, 150) # Yellowish color for the new zone
TRANSPARENT = (0, 0, 0, 0)
WINDOW_BG_COLOR = (30, 30, 40, 240)
TITLE_BAR_COLOR = (50, 50, 60)
CLOSE_BUTTON_COLOR = (180, 40, 40)
BUTTON_COLOR = (0, 100, 200)
BUTTON_HOVER_COLOR = (50, 150, 255)
HIGHLIGHT_COLOR = (255, 255, 0, 100) # Semi-transparent yellow for highlighting


# --- File Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(SCRIPT_DIR, "cards")
SAVE_FILE_PATH = os.path.join(SCRIPT_DIR, "savegame.json")
CARD_DATA_PATH = os.path.join(CARDS_DIR, "card_data.json")
CARD_IMAGES_DIR = os.path.join(CARDS_DIR, "generated_cards")
CARD_BACK_PATH = os.path.join(CARD_IMAGES_DIR, "card_back.png")
UI_DIR = os.path.join(SCRIPT_DIR, "Images", "UI")
ENERGY_ICON_DIR = os.path.join(UI_DIR, "Energy")
PHASE_STATE_IMG_PATH = os.path.join(UI_DIR, "phase_State.png")

ENERGY_MAPPING = {
    "W": "energy_white.png",
    "B": "energy_black.png",
    "U": "energy_blue.png",
    "G": "energy_gray.png",
    "N": "energy_neutral.png"
}


# --- Game Logic Imports ---
from game_logic.card import Card
from game_logic.player import Player
from game_logic.gamestate import GameStateManager

# --- UI Component Classes ---
class ConfirmationDialog:
    """A modal dialog for Yes/No confirmations."""
    def __init__(self, question_text):
        self.visible = False
        self.question = question_text
        self.width, self.height = 400, 150
        self.rect = pygame.Rect((LOGICAL_WIDTH - self.width) / 2, (LOGICAL_HEIGHT - self.height) / 2, self.width, self.height)
        self.font = pygame.font.Font(None, 36)
        self.yes_button = pygame.Rect(self.rect.x + 50, self.rect.y + 80, 100, 50)
        self.no_button = pygame.Rect(self.rect.x + self.width - 150, self.rect.y + 80, 100, 50)

    def ask(self, question=None):
        if question: self.question = question
        self.visible = True

    def handle_event(self, event, logical_pos):
        if not self.visible: return None # No action taken
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: # Yes on Enter
                self.visible = False; return "yes"
            if event.key == pygame.K_ESCAPE: # No on Escape
                self.visible = False; return "no"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.yes_button.collidepoint(logical_pos):
                self.visible = False; return "yes"
            if self.no_button.collidepoint(logical_pos):
                self.visible = False; return "no"
        
        return "modal" # Indicates the dialog is active and should block other events

    def draw(self, surface, logical_pos):
        if not self.visible: return
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)); surface.blit(overlay, (0, 0))
        
        pygame.draw.rect(surface, WINDOW_BG_COLOR, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=10)
        
        text_surf = self.font.render(self.question, True, WHITE)
        surface.blit(text_surf, text_surf.get_rect(centerx=self.rect.centerx, y=self.rect.y + 20))
        
        yes_color = BUTTON_HOVER_COLOR if self.yes_button.collidepoint(logical_pos) else BUTTON_COLOR
        pygame.draw.rect(surface, yes_color, self.yes_button, border_radius=5)
        yes_text = self.font.render("Yes", True, WHITE)
        surface.blit(yes_text, yes_text.get_rect(center=self.yes_button.center))
        
        no_color = BUTTON_HOVER_COLOR if self.no_button.collidepoint(logical_pos) else BUTTON_COLOR
        pygame.draw.rect(surface, no_color, self.no_button, border_radius=5)
        no_text = self.font.render("No", True, WHITE)
        surface.blit(no_text, no_text.get_rect(center=self.no_button.center))

class CardInfoWindow:
    """A movable, closable window to display detailed card information."""
    def __init__(self, energy_icons):
        self.width = 380; self.height = 700
        # Position more towards center to avoid overlap with soul burial windows
        self.rect = pygame.Rect((LOGICAL_WIDTH - self.width) / 2, (LOGICAL_HEIGHT - self.height) / 2, self.width, self.height)
        self.visible = False; self.dragging = False; self.drag_offset = (0, 0)
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 24)
        self.bold_small_font = pygame.font.Font(None, 24)
        self.bold_small_font.set_bold(True)
        self.scroll_y = 0
        self.close_button_rect = pygame.Rect(self.width - 35, 5, 30, 30)
        self.energy_icons = energy_icons

    def show(self, card):
        self.scroll_y = 0; self.visible = True
        self.rect.clamp_ip(pygame.Rect(0,0,LOGICAL_WIDTH, LOGICAL_HEIGHT))

    def hide(self): self.visible = False; self.dragging = False

    def handle_event(self, event, logical_pos, game):
        if not self.visible: return False
        relative_pos = (logical_pos[0] - self.rect.x, logical_pos[1] - self.rect.y)
        is_mouse_over = self.rect.collidepoint(logical_pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if is_mouse_over:
                if event.button == 1:
                    if self.close_button_rect.collidepoint(relative_pos):
                        game.deselect_card(); return True 
                    elif pygame.Rect(0, 0, self.width, 40).collidepoint(relative_pos):
                        self.dragging = True; self.drag_offset = (self.rect.x - logical_pos[0], self.rect.y - logical_pos[1]); return True
                if event.button == 4: self.scroll_y = max(0, self.scroll_y - 25)
                elif event.button == 5: self.scroll_y += 25
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.dragging = False; return is_mouse_over
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.topleft = (logical_pos[0] + self.drag_offset[0], logical_pos[1] + self.drag_offset[1])
            self.rect.clamp_ip(pygame.Rect(0,0,LOGICAL_WIDTH, LOGICAL_HEIGHT)); return True
        return is_mouse_over

    def draw_cost_icons(self, surface, cost_string, x, y):
        """Draws energy cost icons based on the cost string."""
        icon_size = self.small_font.get_height()
        
        generic_cost_str = ''.join(filter(str.isdigit, cost_string))
        specific_cost_str = ''.join(filter(str.isalpha, cost_string))
        
        specific_costs = {}
        for char in specific_cost_str:
            specific_costs[char.upper()] = specific_costs.get(char.upper(), 0) + 1

        # Draw generic cost
        if generic_cost_str:
            if icon_img := self.energy_icons.get("N"):
                scaled_icon = pygame.transform.scale(icon_img, (icon_size, icon_size))
                surface.blit(scaled_icon, (x, y))
                
                num_text = self.bold_small_font.render(generic_cost_str, True, WHITE)
                text_rect = num_text.get_rect(center=(x + icon_size / 2, y + icon_size / 2))
                surface.blit(num_text, text_rect)
                x += icon_size + 5

        # Draw specific costs
        for code, count in specific_costs.items():
             if icon_img := self.energy_icons.get(code):
                for _ in range(count):
                    scaled_icon = pygame.transform.scale(icon_img, (icon_size, icon_size))
                    surface.blit(scaled_icon, (x, y))
                    x += icon_size + 5
        return x

    def custom_wrap(self, text, max_width):
        """A custom text wrapper that understands inline icon syntax and handles long words."""
        lines = []
        words = text.split(' ')
        current_line = []
        current_width = 0
        space_width = self.small_font.size(' ')[0]
        inline_icon_size = self.small_font.get_height() + 2 # Icon width + padding

        for word in words:
            is_icon = re.match(r'\(([WBUG])\)', word)
            word_width = 0
            if is_icon:
                word_width = inline_icon_size
            else:
                word_width = self.small_font.size(word)[0]

            # If adding this word would exceed the width, wrap the current line
            buffer = 5
            if current_width + word_width + (space_width if current_line else 0) > max_width - buffer:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = []
                    current_width = 0
                
                if word_width > max_width and not is_icon:
                    broken_word_lines = self._break_long_word(word, max_width)
                    for broken_line in broken_word_lines[:-1]:
                        lines.append(broken_line)
                    current_line = [broken_word_lines[-1]]
                    current_width = self.small_font.size(broken_word_lines[-1])[0]
                else:
                    current_line = [word]
                    current_width = word_width
            else:
                current_line.append(word)
                current_width += word_width + (space_width if len(current_line) > 1 else 0)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines

    def _break_long_word(self, word, max_width):
        if re.match(r'\(([WBUG])\)', word):
            return [word]
            
        lines = []
        current_line = ""
        
        for char in word:
            test_line = current_line + char
            test_width = self.small_font.size(test_line)[0]
            
            if test_width > max_width and current_line:
                lines.append(current_line + "-")  # Add hyphen for word breaking
                current_line = char
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
            
        return lines


    def draw_formatted_line(self, surface, text, x, y):
        """Draws a line of text, replacing energy symbols with icons."""
        parts = text.split(' ')
        inline_icon_size = self.small_font.get_height()
        space_width = self.small_font.size(' ')[0]

        for part in parts:
            if not part: continue
            
            match = re.match(r'\(([WBUG])\)', part)
            if match:
                energy_code = match.group(1)
                if icon_img := self.energy_icons.get(energy_code):
                    scaled_icon = pygame.transform.scale(icon_img, (inline_icon_size, inline_icon_size))
                    surface.blit(scaled_icon, (x, y))
                    x += inline_icon_size + space_width
                continue
            
            is_bold = "<b>" in part
            clean_part = part.replace("<b>", "").replace("</b>", "")
            font_to_use = self.bold_small_font if is_bold else self.small_font
            
            text_img = font_to_use.render(clean_part, True, WHITE)
            surface.blit(text_img, (x, y))
            x += text_img.get_width() + space_width


    def draw(self, main_surface, card):
        if not self.visible or not card: return
        self.surface.fill(WINDOW_BG_COLOR)
        pygame.draw.rect(self.surface, WHITE, self.surface.get_rect(), 2, border_radius=5)
        title_bar_rect = pygame.Rect(0, 0, self.width, 40)
        pygame.draw.rect(self.surface, TITLE_BAR_COLOR, title_bar_rect, border_top_left_radius=5, border_top_right_radius=5)
        title_text = self.font.render(card.data.get("name", ""), True, WHITE)
        self.surface.blit(title_text, title_text.get_rect(centerx=self.width/2, centery=20))
        pygame.draw.rect(self.surface, CLOSE_BUTTON_COLOR, self.close_button_rect, border_radius=3)
        pygame.draw.line(self.surface, WHITE, (self.close_button_rect.left + 5, self.close_button_rect.top + 5), (self.close_button_rect.right - 5, self.close_button_rect.bottom - 5), 3)
        pygame.draw.line(self.surface, WHITE, (self.close_button_rect.left + 5, self.close_button_rect.bottom - 5), (self.close_button_rect.right - 5, self.close_button_rect.top + 5), 3)
        
        if card_preview_image := card.get_preview_image((CARD_PREVIEW_WIDTH, CARD_PREVIEW_HEIGHT)):
             img_rect = card_preview_image.get_rect(centerx=self.width/2, top=title_bar_rect.bottom + 20)
             self.surface.blit(card_preview_image, img_rect)
        
        text_box_rect = pygame.Rect(10, img_rect.bottom + 20, self.width - 20, self.height - img_rect.bottom - 30)
        text_render_surface = pygame.Surface((text_box_rect.width, 1000), pygame.SRCALPHA)
        text_render_surface.fill(TRANSPARENT)
        
        details = card.get_details(); y_offset = 0
        for key, value in details.items():
            key_text = self.bold_small_font.render(f"{key}: ", True, WHITE)
            text_render_surface.blit(key_text, (0, y_offset))
            x_offset = key_text.get_width()
            
            if key == "Cost" and value != "N/A":
                self.draw_cost_icons(text_render_surface, str(value), x_offset, y_offset)
                y_offset += 22
            else:
                remaining_width = text_box_rect.width - x_offset
                wrapped_lines = self.custom_wrap(str(value), remaining_width)

                for i, line in enumerate(wrapped_lines):
                    current_x = x_offset if i == 0 else key_text.get_width()
                    self.draw_formatted_line(text_render_surface, line, current_x, y_offset)
                    y_offset += 22
            y_offset += 10

        max_scroll = max(0, y_offset - text_box_rect.height)
        self.scroll_y = min(self.scroll_y, max_scroll)
        self.surface.blit(text_render_surface, text_box_rect.topleft, (0, self.scroll_y, text_box_rect.width, text_box_rect.height))
        main_surface.blit(self.surface, self.rect.topleft)

class SoulBurialWindow:
    """A scrollable window to display soul burial cards as images."""
    def __init__(self, is_player_side=True):
        self.width = 300
        self.height = 600
        self.is_player_side = is_player_side  # True for player, False for CPU
        self.visible = False
        self.dragging = False
        self.drag_offset = (0, 0)
        self.scroll_y = 0
        self.cards = []
        self.card_size = (80, 120)  # Smaller card images for the list
        self.cards_per_row = 3
        self.card_spacing = 10
        
        # Position window on appropriate side
        if is_player_side:
            self.rect = pygame.Rect(LOGICAL_WIDTH - self.width - 50, (LOGICAL_HEIGHT - self.height) / 2, self.width, self.height)
        else:
            self.rect = pygame.Rect(50, (LOGICAL_HEIGHT - self.height) / 2, self.width, self.height)
        
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.font = pygame.font.Font(None, 24)
        self.close_button_rect = pygame.Rect(self.width - 35, 5, 30, 30)
        
        # Calculate layout
        self.cards_per_row = (self.width - 20) // (self.card_size[0] + self.card_spacing)
        self.row_height = self.card_size[1] + self.card_spacing

    def show(self, cards):
        """Show the soul burial window with the given cards."""
        self.cards = cards
        self.scroll_y = 0
        self.visible = True
        self.rect.clamp_ip(pygame.Rect(0, 0, LOGICAL_WIDTH, LOGICAL_HEIGHT))

    def hide(self):
        """Hide the soul burial window."""
        self.visible = False
        self.dragging = False

    def handle_event(self, event, logical_pos, game):
        """Handle events for the soul burial window."""
        if not self.visible:
            return False
        
        relative_pos = (logical_pos[0] - self.rect.x, logical_pos[1] - self.rect.y)
        is_mouse_over = self.rect.collidepoint(logical_pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if is_mouse_over:
                if event.button == 1:
                    # Check if clicking close button
                    if self.close_button_rect.collidepoint(relative_pos):
                        self.hide()
                        return True
                    # Check if clicking title bar for dragging
                    elif pygame.Rect(0, 0, self.width, 40).collidepoint(relative_pos):
                        self.dragging = True
                        self.drag_offset = (self.rect.x - logical_pos[0], self.rect.y - logical_pos[1])
                        return True
                    # Check if clicking on a card
                    else:
                        clicked_card = self._get_card_at_position(relative_pos)
                        if clicked_card:
                            game.selected_card = clicked_card
                            game.info_window.show(clicked_card)
                            return True
                # Handle scrolling
                elif event.button == 4:  # Mouse wheel up
                    self.scroll_y = max(0, self.scroll_y - 25)
                    return True
                elif event.button == 5:  # Mouse wheel down
                    max_scroll = max(0, self._get_content_height() - (self.height - 50))
                    self.scroll_y = min(self.scroll_y + 25, max_scroll)
                    return True
                return True
        
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return is_mouse_over
        
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.topleft = (logical_pos[0] + self.drag_offset[0], logical_pos[1] + self.drag_offset[1])
            self.rect.clamp_ip(pygame.Rect(0, 0, LOGICAL_WIDTH, LOGICAL_HEIGHT))
            return True
        
        return is_mouse_over

    def _get_card_at_position(self, relative_pos):
        """Get the card at the given relative position."""
        if relative_pos[1] < 50:  # Below title bar
            return None
        
        # Adjust for scroll
        adjusted_y = relative_pos[1] - 50 + self.scroll_y
        
        # Calculate which card was clicked
        row = adjusted_y // self.row_height
        col = relative_pos[0] // (self.card_size[0] + self.card_spacing)
        
        card_index = row * self.cards_per_row + col
        
        if 0 <= card_index < len(self.cards):
            return self.cards[card_index]
        return None

    def _get_content_height(self):
        """Calculate the total height needed for all cards."""
        if not self.cards:
            return 0
        
        rows = (len(self.cards) + self.cards_per_row - 1) // self.cards_per_row
        return rows * self.row_height

    def draw(self, main_surface):
        """Draw the soul burial window."""
        if not self.visible:
            return
        
        self.surface.fill(WINDOW_BG_COLOR)
        pygame.draw.rect(self.surface, WHITE, self.surface.get_rect(), 2, border_radius=5)
        
        # Title bar
        title_bar_rect = pygame.Rect(0, 0, self.width, 40)
        pygame.draw.rect(self.surface, TITLE_BAR_COLOR, title_bar_rect, border_top_left_radius=5, border_top_right_radius=5)
        
        # Title text
        title_text = f"{'Player' if self.is_player_side else 'CPU'} Soul Burial ({len(self.cards)})"
        title_surface = self.font.render(title_text, True, WHITE)
        self.surface.blit(title_surface, title_surface.get_rect(centerx=self.width/2, centery=20))
        
        # Close button
        pygame.draw.rect(self.surface, CLOSE_BUTTON_COLOR, self.close_button_rect, border_radius=3)
        pygame.draw.line(self.surface, WHITE, (self.close_button_rect.left + 5, self.close_button_rect.top + 5), 
                        (self.close_button_rect.right - 5, self.close_button_rect.bottom - 5), 3)
        pygame.draw.line(self.surface, WHITE, (self.close_button_rect.left + 5, self.close_button_rect.bottom - 5), 
                        (self.close_button_rect.right - 5, self.close_button_rect.top + 5), 3)
        
        # Draw cards
        if self.cards:
            start_y = 50 - self.scroll_y
            for i, card in enumerate(self.cards):
                row = i // self.cards_per_row
                col = i % self.cards_per_row
                
                x = 10 + col * (self.card_size[0] + self.card_spacing)
                y = start_y + row * self.row_height
                
                # Only draw if visible
                if y + self.card_size[1] > 50 and y < self.height:
                    card_image = card.get_hand_image(self.card_size)
                    self.surface.blit(card_image, (x, y))
        
        main_surface.blit(self.surface, self.rect.topleft)

class PhaseIndicator:
    def __init__(self):
        self.visible = False; self.display_start_time = 0; self.display_duration = 2000
        scale_factor = 0.5
        try:
            image = pygame.image.load(PHASE_STATE_IMG_PATH).convert_alpha()
            new_size = (int(image.get_width() * scale_factor), int(image.get_height() * scale_factor))
            self.base_image = pygame.transform.scale(image, new_size)
        except pygame.error:
            self.base_image = pygame.Surface((300 * scale_factor, 50 * scale_factor), pygame.SRCALPHA); self.base_image.fill((50,50,50,200))
        
        self.phase_rects = {
            "Restoration": pygame.Rect(5 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
            "Upkeep": pygame.Rect(350 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
            "Draw": pygame.Rect(700 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
            "Main1": pygame.Rect(1050 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
            "Combat": pygame.Rect(1400 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
            "Main2": pygame.Rect(1750 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
            "End": pygame.Rect(2000 * scale_factor, 5 * scale_factor, 180 * scale_factor, 90 * scale_factor),
        }
        self.rect = self.base_image.get_rect(centerx=LOGICAL_WIDTH / 2, centery=LOGICAL_HEIGHT / 2)

    def show(self): self.visible = True; self.display_start_time = pygame.time.get_ticks()
    def update(self):
        if self.visible and pygame.time.get_ticks() - self.display_start_time > self.display_duration: self.visible = False
    def draw(self, surface, current_phase):
        if not self.visible: return
        surface.blit(self.base_image, self.rect)
        if current_phase in self.phase_rects:
            highlight_surf = pygame.Surface(self.phase_rects[current_phase].size, pygame.SRCALPHA); highlight_surf.fill(HIGHLIGHT_COLOR)
            surface.blit(highlight_surf, (self.rect.x + self.phase_rects[current_phase].x, self.rect.y + self.phase_rects[current_phase].y))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.RESIZABLE)
        self.logical_screen = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        pygame.display.set_caption("Bleach Soul Deck"); self.clock = pygame.time.Clock()
        self.large_font = pygame.font.Font(None, 74); self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.running = True; self.all_cards = {}; self.energy_icons = self.load_energy_icons()
        self.card_back_image = self.load_card_back()
        self.load_card_data()
        self.player = Player("Player 1"); self.cpu = Player("CPU")
        self.selected_card = None; self.info_window = CardInfoWindow(self.energy_icons)
        self.player_soul_burial_window = SoulBurialWindow(is_player_side=True)
        self.cpu_soul_burial_window = SoulBurialWindow(is_player_side=False)
        self.phase_indicator = PhaseIndicator(); self.confirmation_dialog = ConfirmationDialog("Advance to next phase?")
        self.game_state = 'main_menu'; self.state_manager = None
        self.define_layout(); self.define_menu_buttons()

    def define_layout(self):
        center_x = LOGICAL_WIDTH / 2; center_y = LOGICAL_HEIGHT / 2
        ZONE_V_GAP = 20; CENTER_GAP = 20
        player_char_y = center_y + (CENTER_GAP / 2); player_supp_y = player_char_y + CARD_HAND_HEIGHT + ZONE_V_GAP
        cpu_char_y = center_y - (CENTER_GAP / 2) - CARD_HAND_HEIGHT; cpu_supp_y = cpu_char_y - CARD_HAND_HEIGHT - ZONE_V_GAP
        ZONE_H_GAP = 30; main_zone_width = (5 * CARD_HAND_WIDTH) + (4 * ZONE_H_GAP)
        start_x_main = center_x - (main_zone_width / 2); main_area_end_x = start_x_main + main_zone_width
        self.player_character_zones = [pygame.Rect(start_x_main + i * (CARD_HAND_WIDTH + ZONE_H_GAP), player_char_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT) for i in range(5)]
        self.player_support_zones = [pygame.Rect(start_x_main + i * (CARD_HAND_WIDTH + ZONE_H_GAP), player_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT) for i in range(5)]
        self.cpu_character_zones = [pygame.Rect(start_x_main + i * (CARD_HAND_WIDTH + ZONE_H_GAP), cpu_char_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT) for i in range(5)]
        self.cpu_support_zones = [pygame.Rect(start_x_main + i * (CARD_HAND_WIDTH + ZONE_H_GAP), cpu_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT) for i in range(5)]
        self.player_field_zone = pygame.Rect(start_x_main - ZONE_H_GAP - CARD_HAND_WIDTH, player_char_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        self.player_deck_zone = pygame.Rect(main_area_end_x + ZONE_H_GAP, player_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        self.player_burial_zone = pygame.Rect(self.player_deck_zone.right + ZONE_H_GAP, player_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        self.cpu_field_zone = pygame.Rect(main_area_end_x + ZONE_H_GAP, cpu_char_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        self.cpu_burial_zone = pygame.Rect(start_x_main - ZONE_H_GAP - CARD_HAND_WIDTH, cpu_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        self.cpu_deck_zone = pygame.Rect(self.cpu_burial_zone.left - ZONE_H_GAP - CARD_HAND_WIDTH, cpu_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        self.pause_button_rect = pygame.Rect(LOGICAL_WIDTH - 60, 10, 50, 50)

        # --- Player Status Display Layout (LP & Energy) ---
        self.player_status_rect = pygame.Rect(self.player_deck_zone.x, self.player_deck_zone.y - 80, self.player_burial_zone.right - self.player_deck_zone.x, 70)
        self.cpu_status_rect = pygame.Rect(self.cpu_deck_zone.x, self.cpu_deck_zone.y + CARD_HAND_HEIGHT + 10, self.cpu_burial_zone.right - self.cpu_deck_zone.x, 70)
        # --- End Status Layout ---

        # --- Next Phase Button Layout ---
        # Positioned above the player status panel.
        self.next_phase_button_rect = pygame.Rect(0, 0, 150, 150)
        button_center_x = self.player_status_rect.centerx
        button_center_y = self.player_status_rect.top - (self.next_phase_button_rect.height / 2) - 15 # Added 15px padding
        self.next_phase_button_rect.center = (button_center_x, button_center_y)
        # --- End Button Layout ---
        
        # --- Reiryoku Zone and Button Layout Update ---
        # Player's reiryoku zone is to the left of their support zones.
        self.player_reiryoku_zone_rect = pygame.Rect(start_x_main - ZONE_H_GAP - CARD_HAND_WIDTH, player_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        # CPU's reiryoku zone is to the right of their support zones, maintaining symmetry with the field layout.
        self.cpu_reiryoku_zone_rect = pygame.Rect(main_area_end_x + ZONE_H_GAP, cpu_supp_y, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        # The channel button is placed below the player's reiryoku zone.
        self.channel_button_rect = pygame.Rect(self.player_reiryoku_zone_rect.x, self.player_reiryoku_zone_rect.bottom + 10, CARD_HAND_WIDTH, 40)
        # --- End Layout Update ---

    def define_menu_buttons(self):
        self.main_menu_buttons = {"New Battle": pygame.Rect(LOGICAL_WIDTH/2 - 150, LOGICAL_HEIGHT/2 - 50, 300, 60),"Load Battle": pygame.Rect(LOGICAL_WIDTH/2 - 150, LOGICAL_HEIGHT/2 + 30, 300, 60),"Quit": pygame.Rect(LOGICAL_WIDTH/2 - 150, LOGICAL_HEIGHT/2 + 110, 300, 60)}
        self.pause_menu_buttons = {"Resume": pygame.Rect(LOGICAL_WIDTH/2 - 150, LOGICAL_HEIGHT/2 - 50, 300, 60),"Save Game": pygame.Rect(LOGICAL_WIDTH/2 - 150, LOGICAL_HEIGHT/2 + 30, 300, 60),"Exit to Main Menu": pygame.Rect(LOGICAL_WIDTH/2 - 150, LOGICAL_HEIGHT/2 + 110, 300, 60)}

    def load_energy_icons(self):
        icons = {}
        for code, filename in ENERGY_MAPPING.items():
            try:
                path = os.path.join(ENERGY_ICON_DIR, filename)
                icons[code] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                print(f"Warning: Energy icon not found: {path}")
        return icons

    def load_card_back(self):
        try: image = pygame.image.load(CARD_BACK_PATH).convert_alpha()
        except pygame.error:
            image = pygame.Surface((CARD_HAND_WIDTH, CARD_HAND_HEIGHT)); image.fill((40, 0, 80)); pygame.draw.rect(image, (80, 0, 160), image.get_rect(), 10)
        return pygame.transform.scale(image, (CARD_HAND_WIDTH, CARD_HAND_HEIGHT))

    def load_card_data(self):
        if not os.path.exists(CARD_DATA_PATH): return
        try:
            with open(CARD_DATA_PATH, 'r', encoding='utf-8') as f: card_list = json.load(f)
            for card_data in card_list:
                if card_id := card_data.get("id"): self.all_cards[card_id] = Card(card_data, CARD_IMAGES_DIR)
        except Exception as e: print(f"Error loading card data: {e}")

    def start_new_game(self):
        self.player = Player("Player 1"); self.cpu = Player("CPU")
        if not self.all_cards: return
        ids = list(self.all_cards.keys()); random.shuffle(ids)
        player_deck_ids = (ids * (50 // len(ids) + 1))[:50]
        cpu_deck_ids = (ids * (50 // len(ids) + 1))[:50]
        random.shuffle(player_deck_ids)
        random.shuffle(cpu_deck_ids)
        self.player.create_deck([self.all_cards[cid] for cid in player_deck_ids])
        self.cpu.create_deck([self.all_cards[cid] for cid in cpu_deck_ids])
        self.state_manager = GameStateManager(self)
        self.game_state = 'in_game'; self.state_manager.start_game()

    def run(self):
        while self.running:
            self.handle_events()
            if self.game_state == 'in_game': self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        
    def scale_mouse_pos(self, pos):
        w, h = self.screen.get_size()
        if w==0 or h==0: return (0,0)
        return int(pos[0] * (LOGICAL_WIDTH / w)), int(pos[1] * (LOGICAL_HEIGHT / h))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.VIDEORESIZE: self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            
            logical_pos = self.scale_mouse_pos(pygame.mouse.get_pos())
            
            if self.confirmation_dialog.visible:
                result = self.confirmation_dialog.handle_event(event, logical_pos)
                if result == "yes":
                    self.state_manager.advance_player_phase()
                if result is not None: continue 

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.game_state == 'in_game': self.game_state = 'paused'
                    elif self.game_state == 'paused': self.game_state = 'in_game'
            
            if self.game_state == 'main_menu': self.handle_main_menu_events(event, logical_pos)
            elif self.game_state == 'in_game': self.handle_ingame_events(event, logical_pos)
            elif self.game_state == 'paused': self.handle_pause_menu_events(event, logical_pos)

    def handle_main_menu_events(self, event, pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.main_menu_buttons["New Battle"].collidepoint(pos): self.start_new_game()
            if self.main_menu_buttons["Load Battle"].collidepoint(pos): self.load_game_state()
            if self.main_menu_buttons["Quit"].collidepoint(pos): self.running = False

    def handle_ingame_events(self, event, pos):
        if self.info_window.handle_event(event, pos, self): return
        if self.player_soul_burial_window.handle_event(event, pos, self): return
        if self.cpu_soul_burial_window.handle_event(event, pos, self): return
        
        if self.state_manager and self.state_manager.sub_state == 'awaiting_discard':
            if self.state_manager.current_player == self.player:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_discard_click(pos)
            return
        
        if self.state_manager and self.state_manager.sub_state == 'awaiting_channel_target':
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, card in enumerate(self.player.hand):
                    if self.get_player_hand_rect(i).collidepoint(pos):
                        self.player.channel_reiryoku(card)
                        self.state_manager.sub_state = None
                        self.deselect_card()
                        return
                self.state_manager.sub_state = None
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pause_button_rect.collidepoint(pos): self.game_state = 'paused'
            elif self.next_phase_button_rect.collidepoint(pos): 
                current_phase = self.state_manager.current_phase
                question = f"End {current_phase}?"
                if current_phase == "Main2":
                    question = "End Turn?"
                self.confirmation_dialog.ask(question)
            elif self.channel_button_rect.collidepoint(pos):
                if self.state_manager and self.state_manager.current_phase in ["Main1", "Main2"] and not self.player.has_channeled_this_turn:
                    self.state_manager.sub_state = 'awaiting_channel_target'
                    print("Select a card from your hand to channel for Reiryoku.")
            else: self.handle_card_click(pos)
    
    def handle_pause_menu_events(self, event, pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pause_menu_buttons["Resume"].collidepoint(pos): self.game_state = 'in_game'
            if self.pause_menu_buttons["Save Game"].collidepoint(pos): self.save_game_state()
            if self.pause_menu_buttons["Exit to Main Menu"].collidepoint(pos): self.game_state = 'main_menu'

    def deselect_card(self): self.selected_card = None; self.info_window.hide()
    
    def handle_discard_click(self, mouse_pos):
        for i, card in enumerate(self.player.hand):
            if self.get_player_hand_rect(i).collidepoint(mouse_pos):
                self.player.discard_card(card)
                self.state_manager.check_hand_size()
                break

    def handle_card_click(self, mouse_pos):
        if self.selected_card and self.selected_card in self.player.hand:
            if self.state_manager and self.state_manager.current_phase in ["Main1", "Main2"]:
                card_type = self.selected_card.data.get("type")
                if card_type == "Character":
                    for i, r in enumerate(self.player_character_zones):
                        if r.collidepoint(mouse_pos) and not self.player.character_zones[i]: self.player.play_card_to_zone(self.selected_card, "character", i); self.deselect_card(); return
                elif card_type in ["Technique", "Equipment"]:
                     for i, r in enumerate(self.player_support_zones):
                        if r.collidepoint(mouse_pos) and not self.player.support_zones[i]: self.player.play_card_to_zone(self.selected_card, "support", i); self.deselect_card(); return
                elif card_type == "Field":
                    if self.player_field_zone.collidepoint(mouse_pos) and not self.player.field_card_zone: self.player.play_card_to_zone(self.selected_card, "field", 0); self.deselect_card(); return
        
        clicked_a_card = False
        for i, card in enumerate(self.player.hand):
            if self.get_player_hand_rect(i).collidepoint(mouse_pos): self.selected_card = card; self.info_window.show(card); clicked_a_card = True; break
        if not clicked_a_card:
            all_zones = [
                (self.player.character_zones, self.player_character_zones), 
                (self.player.support_zones, self.player_support_zones),
                ([self.player.field_card_zone], [self.player_field_zone]), 
                (self.cpu.character_zones, self.cpu_character_zones),
                (self.cpu.support_zones, self.cpu_support_zones),
                ([self.cpu.field_card_zone], [self.cpu_field_zone]),
                (self.player.reiryoku_zone, [self.player_reiryoku_zone_rect]),
                (self.cpu.reiryoku_zone, [self.cpu_reiryoku_zone_rect])
            ]
            for card_list, rect_list in all_zones:
                if rect_list and (rect_list[0] == self.player_reiryoku_zone_rect or rect_list[0] == self.cpu_reiryoku_zone_rect):
                    if card_list and rect_list[0].collidepoint(mouse_pos):
                        self.selected_card = card_list[-1]; self.info_window.show(card_list[-1]); clicked_a_card = True; break
                else:
                    for i, card in enumerate(card_list):
                        if card and rect_list[i].collidepoint(mouse_pos):
                            self.selected_card = card; self.info_window.show(card); clicked_a_card = True; break
                if clicked_a_card: break
        
        # Check for soul burial zone clicks
        if not clicked_a_card:
            if self.player_burial_zone.collidepoint(mouse_pos) and self.player.soul_burial:
                self.player_soul_burial_window.show(self.player.soul_burial)
                clicked_a_card = True
            elif self.cpu_burial_zone.collidepoint(mouse_pos) and self.cpu.soul_burial:
                self.cpu_soul_burial_window.show(self.cpu.soul_burial)
                clicked_a_card = True
        
        if not clicked_a_card: self.deselect_card()

    def update(self):
        self.phase_indicator.update()
        if self.state_manager: self.state_manager.update()

    def get_player_hand_rect(self, i):
        start_x = LOGICAL_WIDTH // 2 - (len(self.player.hand) * (CARD_HAND_WIDTH + 10) // 2)
        return pygame.Rect(start_x + i * (CARD_HAND_WIDTH + 10), LOGICAL_HEIGHT - CARD_HAND_HEIGHT - 20, CARD_HAND_WIDTH, CARD_HAND_HEIGHT)

    def draw(self):
        if self.game_state == 'main_menu': self.draw_main_menu()
        elif self.game_state in ['in_game', 'paused']:
            self.draw_game_board()
            if self.game_state == 'paused': self.draw_pause_menu()
        
        scaled_surface = pygame.transform.scale(self.logical_screen, self.screen.get_size())
        self.screen.blit(scaled_surface, (0, 0)); pygame.display.flip()

    def draw_main_menu(self):
        self.logical_screen.fill((10, 10, 20))
        title = self.large_font.render("Bleach: Soul Deck", True, WHITE)
        self.logical_screen.blit(title, title.get_rect(centerx=LOGICAL_WIDTH/2, centery=LOGICAL_HEIGHT/2 - 200))
        mouse_pos = self.scale_mouse_pos(pygame.mouse.get_pos())
        for name, rect in self.main_menu_buttons.items():
            color = BUTTON_HOVER_COLOR if rect.collidepoint(mouse_pos) else BUTTON_COLOR
            pygame.draw.rect(self.logical_screen, color, rect, border_radius=10)
            text = self.font.render(name, True, WHITE); self.logical_screen.blit(text, text.get_rect(center=rect.center))
    
    def draw_pause_menu(self):
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); self.logical_screen.blit(overlay, (0, 0))
        mouse_pos = self.scale_mouse_pos(pygame.mouse.get_pos())
        for name, rect in self.pause_menu_buttons.items():
            color = BUTTON_HOVER_COLOR if rect.collidepoint(mouse_pos) else BUTTON_COLOR
            pygame.draw.rect(self.logical_screen, color, rect, border_radius=10)
            text = self.font.render(name, True, WHITE); self.logical_screen.blit(text, text.get_rect(center=rect.center))
    
    def draw_game_board(self):
        self.logical_screen.fill((20, 20, 30)); self.draw_zones(self.logical_screen); self.draw_cards_on_field(self.logical_screen)
        self.draw_hands(self.logical_screen); self.draw_counters(self.logical_screen); self.draw_player_status(self.logical_screen)
        self.info_window.draw(self.logical_screen, self.selected_card)
        self.player_soul_burial_window.draw(self.logical_screen)
        self.cpu_soul_burial_window.draw(self.logical_screen)
        pygame.draw.rect(self.logical_screen, GRAY, self.pause_button_rect, border_radius=5)
        pygame.draw.rect(self.logical_screen, WHITE, (self.pause_button_rect.x + 10, self.pause_button_rect.y + 10, 10, 30))
        pygame.draw.rect(self.logical_screen, WHITE, (self.pause_button_rect.x + 30, self.pause_button_rect.y + 10, 10, 30))
        
        if self.state_manager and self.state_manager.current_player == self.player:
            self.draw_channel_button(self.logical_screen)

        if self.state_manager and self.state_manager.sub_state != 'awaiting_discard':
            self.draw_phase_button(self.logical_screen)
        if self.state_manager: self.phase_indicator.draw(self.logical_screen, self.state_manager.current_phase)
        self.confirmation_dialog.draw(self.logical_screen, self.scale_mouse_pos(pygame.mouse.get_pos()))

        if self.state_manager and self.state_manager.sub_state == 'awaiting_discard':
            current_player = self.state_manager.current_player
            discard_text = self.large_font.render(f"Discard down to 6 cards. (Hand: {len(current_player.hand)})", True, (255, 100, 100))
            self.logical_screen.blit(discard_text, discard_text.get_rect(centerx=LOGICAL_WIDTH/2, y=LOGICAL_HEIGHT - 250))
            
        if self.state_manager and self.state_manager.sub_state == 'awaiting_channel_target':
            prompt_text = self.font.render("Select a card in your hand to Channel.", True, (255, 255, 150))
            self.logical_screen.blit(prompt_text, prompt_text.get_rect(centerx=LOGICAL_WIDTH / 2, y=LOGICAL_HEIGHT - 250))


    def draw_phase_button(self, surface):
        mouse_pos = self.scale_mouse_pos(pygame.mouse.get_pos())
        color = BUTTON_HOVER_COLOR if self.next_phase_button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.circle(surface, color, self.next_phase_button_rect.center, self.next_phase_button_rect.width / 2)
        phase_text = self.state_manager.current_phase if self.state_manager else ""
        button_main_text = "End Turn" if phase_text == "Main2" else "Next Phase"
        text1 = self.font.render(button_main_text, True, WHITE)
        text2 = self.small_font.render(f"({phase_text})", True, WHITE)
        surface.blit(text1, text1.get_rect(centerx=self.next_phase_button_rect.centerx, centery=self.next_phase_button_rect.centery - 15))
        surface.blit(text2, text2.get_rect(centerx=self.next_phase_button_rect.centerx, centery=self.next_phase_button_rect.centery + 15))

    def draw_channel_button(self, surface):
        mouse_pos = self.scale_mouse_pos(pygame.mouse.get_pos())
        is_active = self.state_manager and self.state_manager.current_phase in ["Main1", "Main2"] and not self.player.has_channeled_this_turn
        
        color = GRAY if not is_active else BUTTON_HOVER_COLOR if self.channel_button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
            
        pygame.draw.rect(surface, color, self.channel_button_rect, border_radius=5)
        text = self.small_font.render("Channel", True, WHITE)
        surface.blit(text, text.get_rect(center=self.channel_button_rect.center))

    def draw_player_status(self, surface):
        """Draws the Life Points and Energy Pool for both players."""
        if not self.state_manager: return

        # --- Player Status ---
        pygame.draw.rect(surface, (20, 40, 60), self.player_status_rect, border_radius=5)
        pygame.draw.rect(surface, PLAYER_ZONE_COLOR, self.player_status_rect, 2, border_radius=5)
        
        lp_text = self.font.render(f"LP: {self.player.life_points}", True, WHITE)
        surface.blit(lp_text, (self.player_status_rect.x + 10, self.player_status_rect.y + 5))
        
        player_energy = self.player.get_energy_pool()
        icon_size = 24; padding = 8
        x_offset = self.player_status_rect.x + 10
        y_offset = self.player_status_rect.y + lp_text.get_height() + 5

        for code, count in player_energy.items():
            if count > 0 and (icon_img := self.energy_icons.get(code)):
                scaled_icon = pygame.transform.scale(icon_img, (icon_size, icon_size))
                surface.blit(scaled_icon, (x_offset, y_offset))
                
                count_text = self.small_font.render(f"x{count}", True, WHITE)
                surface.blit(count_text, (x_offset + icon_size + 3, y_offset + (icon_size - count_text.get_height()) / 2))
                x_offset += icon_size + count_text.get_width() + padding

        # --- CPU Status ---
        pygame.draw.rect(surface, (60, 20, 30), self.cpu_status_rect, border_radius=5)
        pygame.draw.rect(surface, ENEMY_ZONE_COLOR, self.cpu_status_rect, 2, border_radius=5)
        
        cpu_lp_text = self.font.render(f"LP: {self.cpu.life_points}", True, WHITE)
        surface.blit(cpu_lp_text, (self.cpu_status_rect.x + 10, self.cpu_status_rect.y + 5))
        
        cpu_energy = self.cpu.get_energy_pool()
        x_offset = self.cpu_status_rect.x + 10
        y_offset = self.cpu_status_rect.y + cpu_lp_text.get_height() + 5

        for code, count in cpu_energy.items():
            if count > 0 and (icon_img := self.energy_icons.get(code)):
                scaled_icon = pygame.transform.scale(icon_img, (icon_size, icon_size))
                surface.blit(scaled_icon, (x_offset, y_offset))
                
                count_text = self.small_font.render(f"x{count}", True, WHITE)
                surface.blit(count_text, (x_offset + icon_size + 3, y_offset + (icon_size - count_text.get_height()) / 2))
                x_offset += icon_size + count_text.get_width() + padding

    def draw_zones(self, surface):
        all_player_zones = self.player_character_zones + self.player_support_zones + [self.player_deck_zone, self.player_burial_zone, self.player_field_zone]
        all_cpu_zones = self.cpu_character_zones + self.cpu_support_zones + [self.cpu_deck_zone, self.cpu_burial_zone, self.cpu_field_zone]
        
        for z in all_player_zones: pygame.draw.rect(surface, PLAYER_ZONE_COLOR, z, 2, border_radius=5)
        for z in all_cpu_zones: pygame.draw.rect(surface, ENEMY_ZONE_COLOR, z, 2, border_radius=5)
        
        pygame.draw.rect(surface, REIRYOKU_ZONE_COLOR, self.player_reiryoku_zone_rect, 2, border_radius=5)
        pygame.draw.rect(surface, REIRYOKU_ZONE_COLOR, self.cpu_reiryoku_zone_rect, 2, border_radius=5)

    
    def draw_cards_on_field(self, surface):
        size = (CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        zones_to_draw = [
            (self.player, self.player.character_zones, self.player_character_zones, 0),
            (self.player, self.player.support_zones, self.player_support_zones, 0),
            (self.player, [self.player.field_card_zone], [self.player_field_zone], 0),
            (self.cpu, self.cpu.character_zones, self.cpu_character_zones, 180),
            (self.cpu, self.cpu.support_zones, self.cpu_support_zones, 180),
            (self.cpu, [self.cpu.field_card_zone], [self.cpu_field_zone], 180)
        ]

        for p, card_list, rect_list, rot in zones_to_draw:
            for i, card in enumerate(card_list):
                if card: 
                    img = card.get_hand_image(size)
                    surface.blit(pygame.transform.rotate(img, rot), rect_list[i].topleft)
        
        if self.player.reiryoku_zone:
            surface.blit(self.card_back_image, self.player_reiryoku_zone_rect.topleft)
        if self.cpu.reiryoku_zone:
            surface.blit(pygame.transform.rotate(self.card_back_image, 180), self.cpu_reiryoku_zone_rect.topleft)


    def draw_hands(self, surface):
        for i, card in enumerate(self.player.hand):
            card_rect = self.get_player_hand_rect(i); surface.blit(card.get_hand_image((CARD_HAND_WIDTH, CARD_HAND_HEIGHT)), card_rect.topleft)
            if self.selected_card == card: pygame.draw.rect(surface, (255, 255, 0), card_rect, 4, border_radius=5)
        cpu_start_x = LOGICAL_WIDTH // 2 - (len(self.cpu.hand) * (CARD_HAND_WIDTH + 10) // 2)
        for i in range(len(self.cpu.hand)): surface.blit(self.card_back_image, (cpu_start_x + i * (CARD_HAND_WIDTH + 10), 20))

    def draw_counters(self, surface):
        size = (CARD_HAND_WIDTH, CARD_HAND_HEIGHT)
        if self.player.deck: surface.blit(self.card_back_image, self.player_deck_zone.topleft)
        if self.player.soul_burial: surface.blit(self.player.soul_burial[-1].get_hand_image(size), self.player_burial_zone.topleft)
        if self.cpu.deck: surface.blit(pygame.transform.rotate(self.card_back_image, 180), self.cpu_deck_zone.topleft)
        if self.cpu.soul_burial: surface.blit(pygame.transform.rotate(self.cpu.soul_burial[-1].get_hand_image(size), 180), self.cpu_burial_zone.topleft)
        
        zones_with_counters = [
            (self.player.deck, self.player_deck_zone),
            (self.player.soul_burial, self.player_burial_zone),
            (self.player.reiryoku_zone, self.player_reiryoku_zone_rect),
            (self.cpu.deck, self.cpu_deck_zone),
            (self.cpu.soul_burial, self.cpu_burial_zone),
            (self.cpu.reiryoku_zone, self.cpu_reiryoku_zone_rect)
        ]
        for card_list, zone_rect in zones_with_counters:
            count_text = self.font.render(str(len(card_list)), True, WHITE)
            surface.blit(count_text, count_text.get_rect(center=zone_rect.center))

    def save_game_state(self):
        try:
            state = {"player": self.player.to_dict(), "cpu": self.cpu.to_dict(), "game_state": self.state_manager.to_dict()}
            with open(SAVE_FILE_PATH, 'w') as f: json.dump(state, f, indent=4)
            print("Game saved successfully.")
        except Exception as e: print(f"Error saving game: {e}")

    def load_game_state(self):
        if not os.path.exists(SAVE_FILE_PATH): print("No save file found."); return
        try:
            with open(SAVE_FILE_PATH, 'r') as f: state = json.load(f)
            self.player.from_dict(state['player'], self.all_cards)
            self.cpu.from_dict(state['cpu'], self.all_cards)
            self.state_manager = GameStateManager(self)
            self.state_manager.from_dict(state['game_state'])
            self.game_state = 'in_game'; print("Game loaded successfully.")
        except Exception as e: print(f"Error loading game: {e}")

if __name__ == '__main__':
    game = Game()
    game.run()

