"""
deck.py

Responsible for:
- Building the full Clue deck (all suspects, weapons, rooms)
- Creating the solution envelope (1 suspect, 1 weapon, 1 room)
- Dealing the remaining cards to players

This module contains pure deck logic with no game flow or AI behavior.
"""

import random
# random: used to shuffle the deck and randomly select solution cards

from typing import List, Dict, Tuple
# List, Dict, Tuple: type hints for clarity and IDE support

from engine.cards import Card, Suspect, Weapon, Room
# Importing the unified Card type and all card categories


# ---------------------------------------------------------
# Deck Construction
# ---------------------------------------------------------

def build_full_deck() -> List[Card]:
    """
    Create a list of all cards in the game.

    Why this exists:
    - The deck is composed of every suspect, weapon, and room.
    - Each enum value is wrapped in a Card object so the engine
      can treat all cards uniformly.

    Returns:
        A list of Card objects representing the full deck.
    """
    deck = []

    # Add all suspects
    for suspect in Suspect:
        deck.append(Card(suspect))

    # Add all weapons
    for weapon in Weapon:
        deck.append(Card(weapon))

    # Add all rooms
    for room in Room:
        deck.append(Card(room))

    return deck


# ---------------------------------------------------------
# Solution Envelope
# ---------------------------------------------------------

def create_solution_envelope(deck: List[Card]) -> Tuple[Card, Card, Card]:
    """
    Randomly select one suspect, one weapon, and one room to form the solution.

    Why this exists:
    - Clue's core mechanic is deducing which 3 cards were removed from the deck.
    - These cards must be removed from the deck before dealing.

    Args:
        deck: The full deck of Card objects.

    Returns:
        A tuple: (suspect_card, weapon_card, room_card)
    """
    # Filter deck by card category
    suspects = [c for c in deck if isinstance(c.value, Suspect)]
    weapons  = [c for c in deck if isinstance(c.value, Weapon)]
    rooms    = [c for c in deck if isinstance(c.value, Room)]

    # Randomly choose one from each category
    suspect_card = random.choice(suspects)
    weapon_card  = random.choice(weapons)
    room_card    = random.choice(rooms)

    # Remove chosen cards from the deck so they are not dealt
    deck.remove(suspect_card)
    deck.remove(weapon_card)
    deck.remove(room_card)

    return suspect_card, weapon_card, room_card


# ---------------------------------------------------------
# Dealing Cards
# ---------------------------------------------------------

def deal_cards(players: List[str], deck: List[Card]) -> Dict[str, List[Card]]:
    """
    Shuffle the remaining deck and deal cards evenly to all players.

    Why this exists:
    - After removing the solution envelope, the remaining cards must be
      distributed round-robin to players.
    - This mirrors the real Clue setup.

    Args:
        players: A list of player identifiers (names or objects).
        deck: The remaining deck after removing the solution cards.

    Returns:
        A dictionary mapping each player to their list of dealt cards.
    """
    random.shuffle(deck)  # Shuffle in-place

    # Initialize empty hands for each player
    hands = {player: [] for player in players}

    # Deal cards round-robin
    i = 0
    for card in deck:
        hands[players[i]].append(card)
        i = (i + 1) % len(players)

    return hands
