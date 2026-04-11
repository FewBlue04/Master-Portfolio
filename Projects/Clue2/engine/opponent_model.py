"""
Simple Opponent Modeling for Clue AI.
Maintains probabilistic beliefs p(player has card) for unknowns and updates with observations.
"""
from collections import defaultdict
from engine.cards import ALL_CARDS

class OpponentModel:
    def __init__(self, kb, my_name):
        self.kb = kb
        self.my_name = my_name
        self.player_names = list(kb.player_names)
        # belief[(player,card)] = probability in [0,1]
        self.belief = {}
        self._init_beliefs()

    def _init_beliefs(self):
        # initialize from KB deterministic info or uniform priors
        for p in self.player_names:
            for c in ALL_CARDS:
                val = self.kb.has_card.get((p, c))
                if val is True:
                    self.belief[(p, c)] = 1.0
                elif val is False:
                    self.belief[(p, c)] = 0.0
                else:
                    # naive prior: use remaining slots / unknown count if available
                    total_slots = self.kb.num_cards_per_player.get(p, 0)
                    confirmed = sum(1 for card in ALL_CARDS if self.kb.has_card.get((p, card)) is True)
                    remaining_slots = max(total_slots - confirmed, 0)
                    unknown_card_count = sum(1 for card in ALL_CARDS if self.kb.has_card.get((p, card)) is None)
                    if unknown_card_count <= 0:
                        self.belief[(p, c)] = 0.0
                    else:
                        self.belief[(p, c)] = min(1.0, remaining_slots / unknown_card_count)

    def observe_hand(self, player, card):
        # Player definitely has this card
        for c in ALL_CARDS:
            self.belief[(player, c)] = 1.0 if c == card else 0.0
        # Other players cannot have it
        for p in self.player_names:
            if p != player:
                self.belief[(p, card)] = 0.0

    def observe_no_show(self, player, suspect, weapon, room):
        # Decrease belief that player has any of these cards
        for c in (suspect, weapon, room):
            prev = self.belief.get((player, c), 0.5)
            # multiply by factor to reduce belief strongly
            self.belief[(player, c)] = prev * 0.2

    def observe_showed_unknown(self, player, suspect, weapon, room):
        # They showed one of these; increase relative belief among them
        # simple boost: raise their probabilities proportionally
        items = (suspect, weapon, room)
        total = sum(self.belief.get((player, c), 0.01) for c in items)
        if total <= 0:
            # assign uniform
            for c in items:
                self.belief[(player, c)] = max(self.belief.get((player, c), 0.0), 0.4)
            return
        # boost each by a factor based on current
        for c in items:
            prev = self.belief.get((player, c), 0.0)
            # increase by up to +0.5*(1-prev)
            self.belief[(player, c)] = min(1.0, prev + 0.5 * (1.0 - prev))

    def observe_no_refute(self, asker, suspect, weapon, room):
        # Nobody refuted: increase envelope likelihood indirectly by reducing player beliefs
        for p in self.player_names:
            if p == asker:
                continue
            for c in (suspect, weapon, room):
                prev = self.belief.get((p, c), 0.5)
                self.belief[(p, c)] = prev * 0.2

    def get_player_prob_has(self, player, card):
        return float(self.belief.get((player, card), 0.0))

    def get_envelope_probabilities(self):
        # approximate envelope probability as product of (1 - p_player_has)
        probs = {}
        for c in ALL_CARDS:
            prod = 1.0
            for p in self.player_names:
                prod *= (1.0 - self.get_player_prob_has(p, c))
            probs[c] = round(prod, 3)
        return probs
