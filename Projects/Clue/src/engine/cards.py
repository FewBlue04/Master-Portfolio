"""
cards.py

Defines all card types used in the Clue engine:
- Suspects
- Weapons
- Rooms
- A unified Card class

This file establishes the core domain model for the entire game.
Every other engine module imports from here.
"""

from enum import Enum, auto
# Enum: lets us define a fixed set of named constants (perfect for suspects/weapons/rooms)
# auto(): automatically assigns each enum member a unique value so we don't manually number them

from dataclasses import dataclass
# dataclass: auto-generates __init__, __repr__, __eq__, etc. for simple data containers

from typing import Union
# Union: indicates that a variable may be one of several types
# Here: a Card can wrap a Suspect OR a Weapon OR a Room


# -----------------------------
# Card Category Definitions
# -----------------------------

class Suspect(Enum):
    """All possible suspects in the game."""
    MUSTARD = auto()
    SCARLET = auto()
    PLUM = auto()
    GREEN = auto()
    WHITE = auto()
    PEACOCK = auto()


class Weapon(Enum):
    """All possible weapons in the game."""
    ROPE = auto()
    KNIFE = auto()
    CANDLESTICK = auto()
    REVOLVER = auto()
    LEAD_PIPE = auto()
    WRENCH = auto()


class Room(Enum):
    """All possible rooms in the game."""
    KITCHEN = auto()
    BALLROOM = auto()
    CONSERVATORY = auto()
    DINING_ROOM = auto()
    BILLIARD_ROOM = auto()
    LIBRARY = auto()
    LOUNGE = auto()
    HALL = auto()
    STUDY = auto()


# -----------------------------
# Unified Card Type
# -----------------------------

@dataclass(frozen=True)
class Card:
    """
    A unified card type used throughout the engine.

    Why this exists:
    - The game uses three different categories (Suspect, Weapon, Room)
    - But the engine should treat all cards uniformly
    - Wrapping them in a Card class gives us one consistent type

    frozen=True:
        Makes the Card immutable — once created, it cannot change.
        This matches real-world behavior: cards don't mutate.
    """
    value: Union[Suspect, Weapon, Room]
    # Union: ensures the card must be exactly one of these enum types
    # This gives strong type safety and clean autocomplete everywhere else

    def __str__(self):
        """
        Returns a clean, human-readable name for printing.
        Example: 'KITCHEN' -> 'Kitchen'
        """
        return self.value.name.title()
