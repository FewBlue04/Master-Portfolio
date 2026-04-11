"""
Clue game constants — card definitions, room adjacency, and secret passages.

Defines all game constants including suspect/weapon/room lists, room adjacency
graph for movement, and secret passage connections. Used by all modules for
validation and game mechanics.
"""

# === Card Definitions ===
# Standard Clue suspect characters
SUSPECTS = [
    "Miss Scarlett",
    "Col. Mustard",
    "Mrs. White",
    "Mr. Green",
    "Mrs. Peacock",
    "Prof. Plum",
]

# Standard Clue murder weapons
WEAPONS = [
    "Candlestick",
    "Knife",
    "Lead Pipe",
    "Revolver",
    "Rope",
    "Wrench",
]

# Standard Clue room locations
ROOMS = [
    "Kitchen",
    "Ballroom",
    "Conservatory",
    "Billiard Room",
    "Library",
    "Study",
    "Hall",
    "Lounge",
    "Dining Room",
]

# === Derived Collections ===
# Master list of all cards in the game
ALL_CARDS = SUSPECTS + WEAPONS + ROOMS

# Map each card to its category for validation
CARD_TYPE = {}
for s in SUSPECTS:
    CARD_TYPE[s] = "suspect"
for w in WEAPONS:
    CARD_TYPE[w] = "weapon"
for r in ROOMS:
    CARD_TYPE[r] = "room"

# === Board Layout ===
# Room adjacency graph for legal movement (door-to-door connections)
ROOM_ADJACENCY = {
    "Kitchen": ["Ballroom", "Dining Room"],
    "Ballroom": ["Kitchen", "Conservatory", "Billiard Room"],
    "Conservatory": ["Ballroom", "Billiard Room"],
    "Billiard Room": ["Ballroom", "Conservatory", "Library"],
    "Library": ["Billiard Room", "Study"],
    "Study": ["Library", "Hall"],
    "Hall": ["Study", "Lounge"],
    "Lounge": ["Hall", "Dining Room"],
    "Dining Room": ["Lounge", "Kitchen"],
}

# Secret passages for teleport movement (classic Clue board connections)
SECRET_PASSAGES = {
    "Kitchen": "Study",
    "Study": "Kitchen",
    "Conservatory": "Lounge",
    "Lounge": "Conservatory",
}

# === UI Display Constants ===
# Color scheme for suspect tokens on the game board
SUSPECT_COLORS = {
    "Miss Scarlett": "#e74c3c",
    "Col. Mustard": "#f39c12",
    "Mrs. White": "#ecf0f1",
    "Mr. Green": "#27ae60",
    "Mrs. Peacock": "#2980b9",
    "Prof. Plum": "#8e44ad",
}

# Unicode icons for weapon cards in the UI
WEAPON_ICONS = {
    "Candlestick": "🕯",
    "Knife": "🔪",
    "Lead Pipe": "🔧",
    "Revolver": "🔫",
    "Rope": "🪢",
    "Wrench": "🔩",
}
