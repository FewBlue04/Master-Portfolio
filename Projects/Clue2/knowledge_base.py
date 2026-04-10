"""
Knowledge Base for Clue AI Bot.

Uses propositional logic and constraint propagation to track:
- Which cards each player definitely HAS
- Which cards each player definitely DOES NOT have
- Clause constraints: "at least one of {A, B, C} is held by player P"

The KB reasons over these facts using:
1. Direct elimination (when someone shows/doesn't show a card)
2. Clause resolution (when all but one card in a clause is eliminated)
3. Cross-player inference (if a card is confirmed held by P, no one else has it)
4. Information gain scoring (entropy-based) for optimal suggestion selection
"""

from itertools import combinations
from collections import defaultdict
from engine.cards import ALL_CARDS, SUSPECTS, WEAPONS, ROOMS, CARD_TYPE


class KnowledgeBase:
    def __init__(self, player_names, my_name, my_cards, num_cards_per_player):
        """
        player_names: list of all player names in turn order
        my_name: the bot's own name
        my_cards: list of cards the bot holds
        num_cards_per_player: dict {player_name: num_cards}
        """
        self.player_names = player_names
        self.my_name = my_name
        self.num_cards_per_player = num_cards_per_player

        # Tri-state knowledge per (player, card):
        #   True  = player definitely HAS this card
        #   False = player definitely does NOT have this card
        #   None  = unknown
        self.has_card = {}  # (player, card) -> True/False/None

        # Clauses: list of (player, frozenset_of_cards)
        # meaning: player has AT LEAST ONE of these cards
        self.clauses = []

        # Confirmed solution candidates
        self._solution_suspect = None
        self._solution_weapon = None
        self._solution_room = None

        # Initialize
        self._init_knowledge(my_cards)

    def _init_knowledge(self, my_cards):
        """Set up initial state from own hand."""
        for player in self.player_names:
            for card in ALL_CARDS:
                self.has_card[(player, card)] = None

        # Bot knows its own cards
        for card in my_cards:
            self._set_has(self.my_name, card, True)

        # Bot doesn't have cards not in hand
        for card in ALL_CARDS:
            if card not in my_cards:
                self._set_has(self.my_name, card, False)

    # ------------------------------------------------------------------
    # Core setters with propagation
    # ------------------------------------------------------------------

    def _set_has(self, player, card, value):
        """Set has_card and trigger propagation if value changed."""
        key = (player, card)
        if self.has_card.get(key) == value:
            return  # no change
        self.has_card[key] = value
        self._propagate()

    def _propagate(self):
        """Run constraint propagation until fixpoint."""
        changed = True
        while changed:
            changed = False
            changed |= self._propagate_card_uniqueness()
            changed |= self._propagate_clauses()
            changed |= self._propagate_player_counts()
            changed |= self._infer_solution()

    def _propagate_card_uniqueness(self):
        """If player P has card C, no other player has C."""
        changed = False
        for card in ALL_CARDS:
            # Find who is confirmed to have this card
            owner = None
            for player in self.player_names:
                if self.has_card.get((player, card)) is True:
                    owner = player
                    break
            if owner:
                for player in self.player_names:
                    if player != owner and self.has_card.get((player, card)) is not False:
                        self.has_card[(player, card)] = False
                        changed = True
        return changed

    def _propagate_clauses(self):
        """
        For each clause (player, cards):
          - Remove cards we know player doesn't have
          - If only one card remains, player must have it
          - If player has any card in clause, clause is satisfied → remove
        """
        changed = False
        new_clauses = []
        for (player, cards) in self.clauses:
            # Check if satisfied
            satisfied = any(
                self.has_card.get((player, c)) is True for c in cards
            )
            if satisfied:
                changed = True
                continue  # drop clause

            # Remove eliminated cards
            remaining = frozenset(
                c for c in cards
                if self.has_card.get((player, c)) is not False
            )

            if len(remaining) == 0:
                # Contradiction — shouldn't happen in valid game
                new_clauses.append((player, remaining))
                continue

            if len(remaining) == 1:
                # Must have this card
                (card,) = remaining
                if self.has_card.get((player, card)) is not True:
                    self.has_card[(player, card)] = True
                    changed = True
                # Clause is now resolved, drop it
                changed = True
                continue

            if remaining != cards:
                changed = True

            new_clauses.append((player, remaining))

        self.clauses = new_clauses
        return changed

    def _propagate_player_counts(self):
        """
        If a player has exactly N unknowns and we know they hold exactly N more cards,
        all those unknowns must be True.
        Conversely, if they've confirmed all their cards, remaining unknowns are False.
        """
        changed = False
        for player in self.player_names:
            if player == self.my_name:
                continue
            total = self.num_cards_per_player.get(player, 0)
            confirmed = sum(
                1 for c in ALL_CARDS
                if self.has_card.get((player, c)) is True
            )
            unknowns = [
                c for c in ALL_CARDS
                if self.has_card.get((player, c)) is None
            ]
            needed = total - confirmed

            if needed == len(unknowns) and needed > 0:
                # All unknowns must be True
                for c in unknowns:
                    self.has_card[(player, c)] = True
                    changed = True
            elif needed == 0 and unknowns:
                # No more cards to assign — all unknowns are False
                for c in unknowns:
                    self.has_card[(player, c)] = False
                    changed = True

        return changed

    def _infer_solution(self):
        """
        A card is in the solution envelope if NO player has it.
        """
        changed = False
        for card in ALL_CARDS:
            all_false = all(
                self.has_card.get((p, card)) is False
                for p in self.player_names
            )
            if all_false:
                # This card is in the envelope
                ctype = CARD_TYPE[card]
                if ctype == "suspect" and self._solution_suspect != card:
                    self._solution_suspect = card
                    changed = True
                elif ctype == "weapon" and self._solution_weapon != card:
                    self._solution_weapon = card
                    changed = True
                elif ctype == "room" and self._solution_room != card:
                    self._solution_room = card
                    changed = True
        return changed

    # ------------------------------------------------------------------
    # Public observation methods
    # ------------------------------------------------------------------

    def observe_hand(self, player, card):
        """We directly see that `player` has `card` (e.g. they showed it to us)."""
        self._set_has(player, card, True)

    def observe_no_show(self, player, suspect, weapon, room):
        """
        `player` could not show any of {suspect, weapon, room}.
        → player does NOT have any of these cards.
        """
        for card in (suspect, weapon, room):
            self._set_has(player, card, False)

    def observe_showed_unknown(self, player, suspect, weapon, room):
        """
        `player` showed a card to someone else but we don't know which.
        → player has AT LEAST ONE of {suspect, weapon, room}.
        """
        cards = frozenset([suspect, weapon, room])
        # Only add clause if not already subsumed
        already = any(
            p == player and existing_cards.issubset(cards)
            for (p, existing_cards) in self.clauses
        )
        if not already:
            # Remove any existing supersets (weaker clauses)
            self.clauses = [
                (p, cs) for (p, cs) in self.clauses
                if not (p == player and cards.issubset(cs))
            ]
            self.clauses.append((player, cards))
            self._propagate()

    # ------------------------------------------------------------------
    # Solution queries
    # ------------------------------------------------------------------

    def get_solution(self):
        """Returns (suspect, weapon, room) if fully solved, else None fields."""
        return (self._solution_suspect, self._solution_weapon, self._solution_room)

    def is_solved(self):
        s, w, r = self.get_solution()
        return s is not None and w is not None and r is not None

    def card_status(self, card):
        """
        Returns one of:
          'mine'     - bot holds it
          'held'     - confirmed held by another player (not solution)
          'envelope' - confirmed in solution envelope
          'unknown'  - uncertain
        """
        if self.has_card.get((self.my_name, card)) is True:
            return 'mine'
        all_false = all(
            self.has_card.get((p, card)) is False
            for p in self.player_names
        )
        if all_false:
            return 'envelope'
        any_true = any(
            self.has_card.get((p, card)) is True
            for p in self.player_names if p != self.my_name
        )
        if any_true:
            return 'held'
        return 'unknown'

    # ------------------------------------------------------------------
    # Optimal suggestion selection (information gain / entropy)
    # ------------------------------------------------------------------

    def score_suggestion(self, suspect, weapon, room):
        """
        Score a suggestion triple by expected information gain.
        Higher = better question to ask.

        Strategy:
        - Prioritize triples containing unknown/envelope cards
        - Penalize triples where we already know all three cards
        - Reward triples that maximally disambiguate the solution
        """
        # Optimize by precomputing status and unknown counts once per evaluation
        cards = [suspect, weapon, room]
        status_map = {}
        none_counts = {}
        for c in cards:
            # determine status quickly
            if self.has_card.get((self.my_name, c)) is True:
                st = 'mine'
            else:
                all_false = True
                any_true = False
                none_count = 0
                for p in self.player_names:
                    v = self.has_card.get((p, c))
                    if v is True:
                        any_true = True
                    if v is not False:
                        all_false = False
                    if v is None:
                        none_count += 1
                if all_false:
                    st = 'envelope'
                elif any_true:
                    st = 'held'
                else:
                    st = 'unknown'
                none_counts[c] = none_count
            status_map[c] = st

        # Base scoring using status counts
        score = 0.0
        unknown_count = sum(1 for c in cards if status_map[c] == 'unknown')
        envelope_count = sum(1 for c in cards if status_map[c] == 'envelope')
        held_count = sum(1 for c in cards if status_map[c] == 'held')
        mine_count = sum(1 for c in cards if status_map[c] == 'mine')

        score += unknown_count * 10.0
        score += envelope_count * 15.0
        score -= mine_count * 5.0
        score -= held_count * 3.0

        # Bonus for specific solution candidate
        sol_s, sol_w, sol_r = self.get_solution()
        if sol_s == suspect:
            score += 5.0
        if sol_w == weapon:
            score += 5.0
        if sol_r == room:
            score += 5.0

        # Bonus: prefer cards with many unknowns
        for c in cards:
            nc = none_counts.get(c)
            if nc is None:
                # compute if not computed (shouldn't happen normally)
                nc = sum(1 for p in self.player_names if self.has_card.get((p, c)) is None)
            score += nc * 2.0

        return score

    def best_suggestion(self, available_room=None, responder_order=None):
        """
        Find the best (suspect, weapon, room) suggestion to make.
        If available_room is specified, fix the room (current location).
        Returns (suspect, weapon, room, score).
        """
        best_score = -999
        best = None

        # Determine room choices
        rooms_to_try = [available_room] if available_room else ROOMS

        # If responder_order not supplied, default to player_names order
        if responder_order is None:
            responder_order = list(self.player_names)

        # Precompute envelope probs to include in scoring
        envelope_probs = self.get_envelope_probabilities()

        # Helper: approximate probability that player `p` has `card`.
        def p_player_has(p, card):
            v = self.has_card.get((p, card))
            if v is True:
                return 1.0
            if v is False:
                return 0.0
            return 0.5

        # Evaluate all reasonable combinations (search space small: 6*6*<=9)
        for s in SUSPECTS:
            for w in WEAPONS:
                for r in rooms_to_try:
                    base = self.score_suggestion(s, w, r)

                    # Add envelope probability bonus (we want to confirm envelope candidates)
                    env_bonus = envelope_probs.get(s, 0.0) + envelope_probs.get(w, 0.0) + envelope_probs.get(r, 0.0)

                    # Responder-aware bonus: reward triples likely to produce an early show.
                    # For each responder in order, compute their probability of showing any of the three
                    # and weight earlier responders higher (1/(idx+1)).
                    responder_bonus = 0.0
                    for idx, p in enumerate(responder_order):
                        # Skip the asker if present here (we assume asker is removed in order by caller)
                        prob_show = 1.0 - ((1.0 - p_player_has(p, s)) * (1.0 - p_player_has(p, w)) * (1.0 - p_player_has(p, r)))
                        responder_bonus += prob_show * (1.0 / (idx + 1))

                    score = base + env_bonus * 25.0 + responder_bonus * 10.0

                    if score > best_score:
                        best_score = score
                        best = (s, w, r)

        return best[0], best[1], best[2], best_score

    # ------------------------------------------------------------------
    # Debug / display helpers
    # ------------------------------------------------------------------

    def get_notebook(self):
        """
        Returns a structured dict for UI display:
        { card: { player: True/False/None, ... } }
        """
        notebook = {}
        for card in ALL_CARDS:
            notebook[card] = {}
            for player in self.player_names:
                notebook[card][player] = self.has_card.get((player, card))
        return notebook

    def get_envelope_probabilities(self):
        """
        Rough probability that each card is in the envelope.
        Estimate using per-player unknown-slot model:
        For each player, estimate probability they hold the card as:
          - 1.0 if confirmed True
          - 0.0 if confirmed False
          - else remaining_slots / unknown_card_count (approx)
        Then envelope probability ~= product_p (1 - prob_player_has(card)).
        """
        probs = {}
        for card in ALL_CARDS:
            status = self.card_status(card)
            if status == 'envelope':
                probs[card] = 1.0
            elif status in ('mine', 'held'):
                probs[card] = 0.0
            else:
                # Use per-player estimates based on their remaining unknown slots
                per_player_has = []
                for p in self.player_names:
                    v = self.has_card.get((p, card))
                    if v is True:
                        per_player_has.append(1.0)
                        continue
                    if v is False:
                        per_player_has.append(0.0)
                        continue

                    # Unknown: estimate probability p has card by (remaining_slots / unknown_card_count)
                    total_slots = self.num_cards_per_player.get(p, 0)
                    confirmed = sum(1 for c in ALL_CARDS if self.has_card.get((p, c)) is True)
                    remaining_slots = max(total_slots - confirmed, 0)
                    unknown_card_count = sum(1 for c in ALL_CARDS if self.has_card.get((p, c)) is None)
                    if unknown_card_count <= 0:
                        est = 0.0
                    else:
                        est = min(1.0, remaining_slots / unknown_card_count)
                    per_player_has.append(est)

                prob_no_one = 1.0
                for est in per_player_has:
                    prob_no_one *= (1.0 - est)
                probs[card] = round(prob_no_one, 3)
        return probs
