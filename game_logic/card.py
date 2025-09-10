import pygame
import os

class Card:
    def __init__(self, data, images_dir):
        self.data = data
        self.images_dir = images_dir
        self.image = self.load_image()
        self.is_exhausted = False # For tracking tapped/used state

    def load_image(self):
        """Loads the card's image from the generated_cards folder."""
        try:
            card_id = self.data.get("id")
            image_path = os.path.join(self.images_dir, f"{card_id}.png")
            return pygame.image.load(image_path).convert_alpha()
        except pygame.error as e:
            # print(f"Could not load image for {self.data.get('name')}: {e}")
            return self.create_placeholder_image()

    def create_placeholder_image(self):
        """Creates a placeholder surface if the card image is not found."""
        placeholder = pygame.Surface((420, 600))
        placeholder.fill((50, 50, 50))
        font = pygame.font.Font(None, 36)
        text_surf = font.render(self.data.get("name", "Unknown"), True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(210, 300))
        placeholder.blit(text_surf, text_rect)
        return placeholder

    def get_preview_image(self, size):
        """Returns a scaled version of the card image for preview."""
        return pygame.transform.scale(self.image, size)

    def get_hand_image(self, size):
        """Returns a scaled version of the card image for display in hand/field."""
        return pygame.transform.scale(self.image, size)

    def get_details(self):
        """Returns a dictionary of important card details for display."""
        details = {
            "Type": f"{self.data.get('type', 'N/A')} - {self.data.get('subtypes', '')}",
            "Faction": self.data.get('faction', 'N/A'),
            "Cost": self.data.get('cost', 'N/A')
        }
        if self.data.get('type') == 'Character':
            details["Reiatsu"] = self.data.get('reiatsu', '0')
            details["Genryu"] = self.data.get('genryu', '0')
        
        details["Rules"] = self.data.get('rules_text', '')
        details["Flavor"] = self.data.get('flavor_text', '')
        return details

