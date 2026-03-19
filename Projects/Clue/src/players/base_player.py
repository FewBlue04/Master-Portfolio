"""
player_base.py

Defines the abstract base class for all players in the Clue engine.
This includes human players and bot players.

Why this file exists:
- The TurnManager expects every player object to implement take_turn().
- HumanPlayer and BotPlayer will share common structure and behavior.
- This enforces a clean, consistent interface across all player types.
"""

from abc import ABC, abstractmethod
# ABC: allows us to define abstract base classes
# abstractmethod: forces subclasses to implement required methods

from engine.game_state import GameState


class BasePlayer(ABC):
    """
    Abstract base class for all players.

    Every player must:
    - have a name (string identifier)
    - implement take_turn(), which the TurnManager will call each round

    This class contains no gameplay logic — only the interface.
    """

    def __init__(self, name: str):
        """
        Args:
            name:
                A string identifier for the player.
                Must match the name used in GameState.players.
        """
        self.name = name

    @abstractmethod
    def take_turn(self, game_state: GameState):
        """
        Called by the TurnManager when it is this player's turn.

        Args:
            game_state:
                The shared GameState object containing hands, envelope,
                turn index, and history.

        Subclasses must implement this method.

        For the MVP:
        - HumanPlayer will print prompts and accept CLI input.
        - BotPlayer will run deduction logic and choose an action.
        """
        pass
