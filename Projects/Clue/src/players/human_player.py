"""
human_player.py

Implements a simple command-line human player for the Clue engine.
This class inherits from BasePlayer and provides a minimal interactive
turn flow for the MVP (no board, no UI).

For now, the human player:
- sees their hand
- chooses an action (placeholder)
- eventually will make suggestions, refutations, or accusations
"""

from engine.base_player import BasePlayer
from engine.game_state import GameState


class HumanPlayer(BasePlayer):
    """
    A human-controlled player using simple CLI input.

    Why this class exists:
    - The TurnManager expects every player to implement take_turn().
    - This class provides a minimal interactive loop for humans.
    - Later, this will expand to support suggestions, refutations,
      and accusations.
    """

    def take_turn(self, game_state: GameState):
        """
        Called by the TurnManager when it's this player's turn.

        For the MVP:
        - Show the player's hand
        - Ask for a placeholder action
        - Real logic (suggestions/refutations/accusations) will be added later
        """
        print(f"\n{self.name}, it's your turn!")
        print("Your hand:")

        for card in game_state.hands[self.name]:
            print(f"  - {card}")

        # Placeholder action loop
        print("\nChoose an action:")
        print("1. Pass turn (placeholder)")
        print("2. Make accusation (placeholder)")
        print("3. Quit game")

        choice = input("> ").strip()

        if choice == "1":
            print(f"{self.name} passes the turn.\n")
            return

        elif choice == "2":
            print("Accusation logic not implemented yet.\n")
            # Later: call accusation logic here
            return

        elif choice == "3":
            print("Ending game early.\n")
            game_state.end_game()
            return

        else:
            print("Invalid choice. Passing turn by default.\n")
            return
