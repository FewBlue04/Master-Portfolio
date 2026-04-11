"""
Clue game card definitions and constants.
"""

SUSPECTS = [
    "Miss Scarlett",
    "Col. Mustard",
    "Mrs. White",
    "Mr. Green",
    "Mrs. Peacock",
    "Prof. Plum",
]

WEAPONS = [
    "Candlestick",
    "Knife",
    "Lead Pipe",
    "Revolver",
    "Rope",
    "Wrench",
]

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

ALL_CARDS = SUSPECTS + WEAPONS + ROOMS

CARD_TYPE = {}
for s in SUSPECTS:
    CARD_TYPE[s] = "suspect"
for w in WEAPONS:
    CARD_TYPE[w] = "weapon"
for r in ROOMS:
    CARD_TYPE[r] = "room"

# Board layout: rooms and their adjacency (for movement simulation)
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

# Secret passages (classic Clue)
SECRET_PASSAGES = {
    "Kitchen": "Study",
    "Study": "Kitchen",
    "Conservatory": "Lounge",
    "Lounge": "Conservatory",
}

SUSPECT_COLORS = {
    "Miss Scarlett": "#e74c3c",
    "Col. Mustard": "#f39c12",
    "Mrs. White": "#ecf0f1",
    "Mr. Green": "#27ae60",
    "Mrs. Peacock": "#2980b9",
    "Prof. Plum": "#8e44ad",
}

WEAPON_ICONS = {
    "Candlestick": "🕯",
    "Knife": "🔪",
    "Lead Pipe": "🔧",
    "Revolver": "🔫",
    "Rope": "🪢",
    "Wrench": "🔩",
}
