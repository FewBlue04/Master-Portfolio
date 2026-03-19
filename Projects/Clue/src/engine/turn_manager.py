"""
turn_manager.py

Coordinates the flow of the game:
- Runs the main game loop
- Determines whose turn it is
- Calls into player logic (human or bot)
- Advances turns
- Ends the game when an accusation is correct

This file contains *game flow*, not game state or game logic.
"""

from typing import List

from engine.game_state import GameState


class TurnManager:
    """
    Controls the turn-by-turn progression of the game.

    Why this class exists:
    - GameState stores data, but does not know how to *run* the game.
    - Players (human or bot) need a consistent interface for taking turns.
    - The engine needs a central coordinator that decides:
        - whose turn it is
        - what actions they can take
        - when the game ends
    """

    def __init__(self, game_state: GameState, players: List[object]):
        """
        Args:
            game_state:
                The shared GameState object containing hands, envelope,
                turn index, and history.

            players:
                A list of player objects (HumanPlayer, BotPlayer, etc.)
                in the same order as game_state.players.
        """
        self.game_state = game_state
        self.players = players

    # ---------------------------------------------------------
    # Main Game Loop
    # ---------------------------------------------------------

    def run(self):
        """
        Run the game loop until someone makes a correct accusation.

        For the MVP:
        - Each turn simply calls player.take_turn()
        - No UI, no board, no movement
        - The bot and humans will eventually make suggestions/refutations
        """
        print("Game started!\n")

        while not self.game_state.is_over:
            current_player_name = self.game_state.current_player
            current_player_obj = self.players[self.game_state.current_player_index]

            print(f"--- {current_player_name}'s turn ---")

            # Delegate the turn to the player object
            # (HumanPlayer or BotPlayer will implement take_turn)
            current_player_obj.take_turn(self.game_state)

            # If the game ended during the turn (correct accusation), stop
            if self.game_state.is_over:
                break

            # Otherwise, move to the next player
            self.game_state.advance_turn()

        print("\nGame over!")
