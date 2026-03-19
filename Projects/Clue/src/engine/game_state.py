"""
game_state.py

Holds all persistent information about the current game of Clue.
This is the central data model that the engine, turn manager, and AI
will read from and update.

For the MVP (1–2 humans + 1 bot, no board/UI), the GameState tracks:
- players
- each player's hand
- the solution envelope
- whose turn it is
- whether the game is over
- optional history of suggestions/refutations/accusations
"""

from typing import List, Dict, Tuple, Any

from engine.cards import Card


class GameState:
    """
    Represents the full state of a running Clue game.

    Why this class exists:
    - The engine needs a single source of truth for all game data.
    - The bot needs access to hands, envelope structure, and history
      to perform deduction.
    - The turn manager needs to know whose turn it is and whether the
      game has ended.

    This class contains *no game logic* — only data.
    """

    def __init__(
        self,
        players: List[str],
        envelope: Tuple[Card, Card, Card],
        hands: Dict[str, List[Card]],
    ):
        """
        Initialize the game state.

        Args:
            players:
                A list of player identifiers (names or objects).
                Order matters — this defines turn order.

            envelope:
                A tuple of 3 Cards (suspect, weapon, room) representing
                the hidden murder solution.

            hands:
                A dictionary mapping each player to the list of Cards
                they were dealt at the start of the game.
        """
        self.players = players
        self.envelope = envelope
        self.hands = hands

        # Index of the current player in the players list
        self.current_player_index = 0

        # Flag indicating whether the game has ended
        self.is_over = False

        # Optional: store history of events (suggestions, refutations, accusations)
        # This is extremely useful for the bot's deduction engine.
        self.history: List[Any] = []

    # ---------------------------------------------------------
    # Turn Management Helpers
    # ---------------------------------------------------------

    @property
    def current_player(self) -> str:
        """Return the identifier of the player whose turn it is."""
        return self.players[self.current_player_index]

    def advance_turn(self):
        """
        Move to the next player's turn.

        This does not enforce any game rules — the turn manager
        will call this after handling suggestions/refutations.
        """
        self.current_player_index = (self.current_player_index + 1) % len(self.players)

    # ---------------------------------------------------------
    # History Tracking
    # ---------------------------------------------------------

    def record_event(self, event: Any):
        """
        Append an event to the game history.

        Why this matters:
        - The bot will use this to deduce which cards are possible.
        - The engine can replay or inspect past actions.
        """
        self.history.append(event)

    # ---------------------------------------------------------
    # Game End Helpers
    # ---------------------------------------------------------

    def end_game(self):
        """
        Mark the game as finished.

        The turn manager or accusation logic will call this when
        someone makes a correct accusation.
        """
        self.is_over = True
