import time
import random

class GameStateManager:
    def __init__(self, game):
        self.game = game
        self.players = [game.player, game.cpu]
        self.turn_index = 0
        self.phase_order = ["Restoration", "Upkeep", "Draw", "Main1", "Combat", "Main2", "End"]
        self.phase_index = 0
        self.is_processing_automatic_phases = False
        self.first_turn = True
        self.sub_state = None # e.g., 'awaiting_discard', 'awaiting_channel_target'

    @property
    def current_player(self):
        return self.players[self.turn_index]

    @property
    def current_phase(self):
        return self.phase_order[self.phase_index]

    def start_game(self):
        """Initializes the game and starts the first turn."""
        if not self.players[0].hand and not self.players[1].hand:
             for _ in range(5):
                self.players[0].draw_card()
                self.players[1].draw_card()
        
        print(f"--- Game Start ---")
        self.start_turn()

    def advance_player_phase(self):
        """Manually advances the phase, called by player input."""
        if self.is_processing_automatic_phases:
            return

        if self.current_phase == "Main2":
            self.phase_index = self.phase_order.index("End")
            self.execute_phase_actions()
        else:
            self._advance_phase()

    def update(self):
        """Automatically progresses through phases that don't require player input."""
        if self.is_processing_automatic_phases:
            time.sleep(0.5) 
            if self.current_phase in ["Restoration", "Upkeep", "Draw"]:
                self._advance_phase()
            else:
                self.is_processing_automatic_phases = False

    def _advance_phase(self):
        """Core logic to advance to the next phase and handle turn changes."""
        self.phase_index += 1
        if self.phase_index >= len(self.phase_order):
            self.end_turn()
        else:
            self.execute_phase_actions()
            if self.current_phase not in ["Restoration", "Upkeep", "Draw"]:
                self.is_processing_automatic_phases = False

    def check_hand_size(self):
        """Called after a player discards. Checks if they can now end their turn."""
        if self.sub_state == 'awaiting_discard' and len(self.current_player.hand) <= 6:
            print(f"{self.current_player.name} has discarded down to a valid hand size.")
            self.sub_state = None
            self.end_turn()

    def end_turn(self):
        """Finalizes the turn and starts the next one."""
        self.phase_index = 0
        self.turn_index = (self.turn_index + 1) % 2
        if self.turn_index == 0: self.first_turn = False 
        self.start_turn()

    def start_turn(self):
        """Begins a new turn and handles automatic start-of-turn phases."""
        print(f"\n--- {self.current_player.name}'s Turn ---")
        # --- Reset once-per-turn actions ---
        self.current_player.has_channeled_this_turn = False
        # --- End reset ---
        self.is_processing_automatic_phases = True
        self.execute_phase_actions()
    
    def execute_phase_actions(self):
        """Executes the logic for the current phase."""
        print(f"Entering {self.current_phase} Phase for {self.current_player.name}.")
        self.game.phase_indicator.show() 
        phase_action = getattr(self, f"on_{self.current_phase.lower()}_phase", None)
        if phase_action:
            phase_action()
    
    def on_restoration_phase(self):
        self.current_player.ready_all_cards()

    def on_upkeep_phase(self):
        # Placeholder for future upkeep effects
        pass

    def on_draw_phase(self):
        if self.turn_index == 0 and self.first_turn:
            print(f"{self.current_player.name} skips their first Draw Phase.")
            return
        
        card = self.current_player.draw_card()
        if card:
            print(f"{self.current_player.name} draws a card.")
        else:
            print(f"{self.current_player.name}'s deck is empty!")

    def on_end_phase(self):
        """Handles the End Phase logic, including hand size check and turn progression."""
        print(f"End Phase: Cleanup effects resolve.")
        
        if len(self.current_player.hand) > 6:
            self.sub_state = 'awaiting_discard'
            print(f"{self.current_player.name} must discard {len(self.current_player.hand) - 6} card(s).")
            
            if self.current_player == self.game.cpu:
                self.handle_cpu_discard()
            return
        
        self.end_turn()

    def handle_cpu_discard(self):
        """Handles the CPU's random discard logic."""
        print(f"{self.current_player.name} is discarding...")
        time.sleep(1) 
        while len(self.current_player.hand) > 6:
            if not self.current_player.hand: break
            card_to_discard = random.choice(self.current_player.hand)
            self.current_player.discard_card(card_to_discard)
            print(f"{self.current_player.name} discarded '{card_to_discard.data['name']}'.")
            time.sleep(0.5)
        
        self.check_hand_size()

    def to_dict(self):
        return {"turn_index": self.turn_index, "phase_index": self.phase_index, "first_turn": self.first_turn}

    def from_dict(self, data):
        self.turn_index = data.get("turn_index", 0)
        self.phase_index = data.get("phase_index", 0)
        self.first_turn = data.get("first_turn", True)

