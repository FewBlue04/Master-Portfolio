"""
Lightweight GameStateTracker — records suggestions, responses, shows, and accusations
for use by bots and analysis tools.
"""


class GameStateTracker:
    """Append-only log of suggestion and accusation events for analysis and simulations."""

    def __init__(self, player_names):
        self.player_names = list(player_names)
        self.suggestions = []  # list of suggestion events
        self.accusations = []  # list of accusation events

    def record_suggestion(self, asker, suspect, weapon, room, responder_sequence):
        evt = {
            "type": "suggestion",
            "asker": asker,
            "suspect": suspect,
            "weapon": weapon,
            "room": room,
            "responder_sequence": list(responder_sequence),
        }
        self.suggestions.append(evt)
        return evt

    def record_show(self, shower, asker, card=None):
        evt = {
            "type": "show",
            "shower": shower,
            "asker": asker,
            "card": card,  # may be None if unknown to observers
        }
        self.suggestions.append(evt)
        return evt

    def record_no_show(self, passer, asker, suspect, weapon, room):
        evt = {
            "type": "no_show",
            "passer": passer,
            "asker": asker,
            "suspect": suspect,
            "weapon": weapon,
            "room": room,
        }
        self.suggestions.append(evt)
        return evt

    def record_accusation(self, accuser, suspect, weapon, room, correct):
        evt = {
            "type": "accusation",
            "accuser": accuser,
            "suspect": suspect,
            "weapon": weapon,
            "room": room,
            "correct": bool(correct),
        }
        self.accusations.append(evt)
        return evt

    def recent_suggestions(self, n=20):
        return list(self.suggestions[-n:])
