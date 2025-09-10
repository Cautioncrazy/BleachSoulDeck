import random

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.deck = []
        self.soul_burial = [] # Graveyard
        self.character_zones = [None] * 5
        self.support_zones = [None] * 5
        self.field_card_zone = None
        self.life_points = 30
        
        # --- Reiryoku Mechanic Attributes ---
        self.reiryoku_zone = []
        self.has_channeled_this_turn = False
        # --- End Attributes ---

    def create_deck(self, cards):
        """Initializes the player's deck."""
        self.deck = cards
        random.shuffle(self.deck)

    def draw_card(self):
        """Draws a card from the deck to the hand."""
        if self.deck:
            card = self.deck.pop(0)
            self.hand.append(card)
            return card
        return None

    def discard_card(self, card_to_discard):
        """Moves a card from hand to the soul burial."""
        if card_to_discard in self.hand:
            self.hand.remove(card_to_discard)
            self.soul_burial.append(card_to_discard)
            print(f"{self.name} discarded {card_to_discard.data['name']}")

    def play_card_to_zone(self, card, zone_type, index):
        """Plays a card from the hand to a specified zone."""
        if card in self.hand:
            if zone_type == "character" and self.character_zones[index] is None:
                self.character_zones[index] = card
                self.hand.remove(card)
            elif zone_type == "support" and self.support_zones[index] is None:
                self.support_zones[index] = card
                self.hand.remove(card)
            elif zone_type == "field" and self.field_card_zone is None:
                self.field_card_zone = card
                self.hand.remove(card)

    def channel_reiryoku(self, card):
        """Moves a card from hand to the reiryoku zone to generate energy."""
        if card in self.hand and not self.has_channeled_this_turn:
            self.hand.remove(card)
            self.reiryoku_zone.append(card)
            self.has_channeled_this_turn = True
            print(f"{self.name} channeled {card.data['name']} for Reiryoku.")
            return True
        print(f"Error: Cannot channel {card.data['name']}.")
        return False

    def get_energy_pool(self):
        """Calculates and returns the player's available energy."""
        energy = {"N": 0, "W": 0, "B": 0, "U": 0, "G": 0}
        # Each card in the reiryoku zone provides 1 Neutral energy.
        energy["N"] += len(self.reiryoku_zone)
        
        # This can be expanded later to check for cards on the field that produce energy.
        # for card in self.character_zones + self.support_zones:
        #     if card and hasattr(card, 'produces_energy') and card.produces_energy:
        #         for type, amount in card.energy_production.items():
        #             energy[type] += amount
        
        return energy

    def ready_all_cards(self):
        """Readies all cards on the field at the start of a turn."""
        for card in self.character_zones:
            if card: card.is_exhausted = False
        for card in self.support_zones:
            if card: card.is_exhausted = False
        if self.field_card_zone:
            self.field_card_zone.is_exhausted = False

    def to_dict(self):
        """Converts the player's state to a serializable dictionary."""
        return {
            "name": self.name,
            "life_points": self.life_points,
            "hand": [card.data['id'] for card in self.hand],
            "deck": [card.data['id'] for card in self.deck],
            "soul_burial": [card.data['id'] for card in self.soul_burial],
            "character_zones": [card.data['id'] if card else None for card in self.character_zones],
            "support_zones": [card.data['id'] if card else None for card in self.support_zones],
            "field_card_zone": self.field_card_zone.data['id'] if self.field_card_zone else None,
            "reiryoku_zone": [card.data['id'] for card in self.reiryoku_zone], # Added for saving
            "has_channeled_this_turn": self.has_channeled_this_turn, # Added for saving
        }

    def from_dict(self, data, all_cards_map):
        """Reconstructs the player's state from a dictionary."""
        self.name = data.get("name", "Player")
        self.life_points = data.get("life_points", 30)
        self.hand = [all_cards_map.get(cid) for cid in data.get("hand", []) if cid]
        self.deck = [all_cards_map.get(cid) for cid in data.get("deck", []) if cid]
        self.soul_burial = [all_cards_map.get(cid) for cid in data.get("soul_burial", []) if cid]
        self.character_zones = [all_cards_map.get(cid) for cid in data.get("character_zones", [None]*5)]
        self.support_zones = [all_cards_map.get(cid) for cid in data.get("support_zones", [None]*5)]
        field_cid = data.get("field_card_zone")
        self.field_card_zone = all_cards_map.get(field_cid) if field_cid else None
        self.reiryoku_zone = [all_cards_map.get(cid) for cid in data.get("reiryoku_zone", []) if cid] # Added for loading
        self.has_channeled_this_turn = data.get("has_channeled_this_turn", False) # Added for loading

