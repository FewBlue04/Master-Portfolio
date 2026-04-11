"""
Deterministic constraint engine for Clue.

The envelope is represented as a special entity, and every update is
propagated to closure before control returns to callers.
"""

from __future__ import annotations

from copy import deepcopy

from .cards import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS

ENVELOPE = "__ENVELOPE__"
CATEGORIES = {
    "suspect": tuple(SUSPECTS),
    "weapon": tuple(WEAPONS),
    "room": tuple(ROOMS),
}


class ContradictionError(Exception):
    """Raised when a knowledge update violates Clue constraints."""


class KnowledgeBase:
    """Constraint store for one player: ``has_card`` assignments and propagation to a fixed point."""

    def __init__(self, player_names, my_name, my_cards, num_cards_per_player):
        self.player_names = list(player_names)
        self.my_name = my_name
        self.num_cards_per_player = dict(num_cards_per_player)
        self.entities = list(self.player_names) + [ENVELOPE]

        # (entity, card) -> True | False | None
        self.has_card = {(entity, card): None for entity in self.entities for card in ALL_CARDS}

        # Each clause means "entity has at least one of these cards".
        self.clauses = []

        self._initialize(my_cards)

    def _initialize(self, my_cards):
        my_cards = set(my_cards)

        for card in ALL_CARDS:
            self._assign(self.my_name, card, card in my_cards)

        for category_cards in CATEGORIES.values():
            self.clauses.append((ENVELOPE, frozenset(category_cards)))

        self.propagate()

    def clone(self):
        return deepcopy(self)

    def add_constraint(self, entity, card, value):
        self._assign(entity, card, value)
        self.propagate()

    def observe_hand(self, player, card):
        self.add_constraint(player, card, True)

    def observe_showed_card_to_me(self, player, card):
        self.observe_hand(player, card)

    def observe_no_show(self, player, suspect, weapon, room):
        for card in (suspect, weapon, room):
            self._assign(player, card, False)
        self.propagate()

    def observe_showed_unknown(self, player, suspect, weapon, room):
        self.clauses.append((player, frozenset((suspect, weapon, room))))
        self.propagate()

    def observe_showed_card_to_other(self, player, suspect, weapon, room):
        self.observe_showed_unknown(player, suspect, weapon, room)

    def get_possible_owners(self, card):
        return {entity for entity in self.entities if self.has_card[(entity, card)] is not False}

    def get_envelope_candidates(self, category):
        return {
            card for card in CATEGORIES[category] if self.has_card[(ENVELOPE, card)] is not False
        }

    def get_solution(self):
        return (
            self._find_envelope_card("suspect"),
            self._find_envelope_card("weapon"),
            self._find_envelope_card("room"),
        )

    def can_accuse(self):
        return self.is_solved()

    def is_solved(self):
        suspect, weapon, room = self.get_solution()
        return suspect is not None and weapon is not None and room is not None

    def is_consistent(self):
        try:
            self._check_consistency()
        except ContradictionError:
            return False
        return True

    def snapshot_metrics(self):
        return {
            "total_possible_owners": sum(len(self.get_possible_owners(card)) for card in ALL_CARDS),
            "confirmed_assignments": sum(
                1 for card in ALL_CARDS if self._confirmed_owner(card) is not None
            ),
            "envelope_candidate_total": sum(
                len(self.get_envelope_candidates(category)) for category in CATEGORIES
            ),
            "unresolved_clauses": len(self.clauses),
        }

    def score_delta(self, before_metrics):
        after = self.snapshot_metrics()
        return (
            before_metrics["total_possible_owners"]
            - after["total_possible_owners"]
            + after["confirmed_assignments"]
            - before_metrics["confirmed_assignments"]
            + before_metrics["envelope_candidate_total"]
            - after["envelope_candidate_total"]
            + before_metrics.get("unresolved_clauses", 0)
            - after.get("unresolved_clauses", 0)
        )

    def get_notebook(self):
        notebook = {}
        for player in self.player_names:
            notebook[player] = {}
            for card in ALL_CARDS:
                notebook[player][card] = self.has_card[(player, card)]
        return notebook

    def card_status(self, card):
        owner = self._confirmed_owner(card)
        if owner == self.my_name:
            return "mine"
        if owner == ENVELOPE:
            return "envelope"
        if owner is not None:
            return "held"
        return "unknown"

    def propagate(self):
        changed = True
        while changed:
            changed = False
            changed |= self._apply_card_uniqueness()
            changed |= self._apply_singleton_assignments()
            changed |= self._apply_player_card_limits()
            changed |= self._apply_clause_reduction()
            changed |= self._apply_envelope_category_rules()
            self._check_consistency()

    def _assign(self, entity, card, value):
        key = (entity, card)
        current = self.has_card[key]

        if current == value:
            return False
        if current is not None and current != value:
            raise ContradictionError(f"Conflicting assignment for {entity} and {card}")

        self.has_card[key] = value
        return True

    def _confirmed_owner(self, card):
        owner = None
        for entity in self.entities:
            if self.has_card[(entity, card)] is True:
                if owner is not None and owner != entity:
                    raise ContradictionError(f"Multiple confirmed owners for {card}")
                owner = entity
        return owner

    def _find_envelope_card(self, category):
        for card in CATEGORIES[category]:
            if self.has_card[(ENVELOPE, card)] is True:
                return card
        return None

    def _apply_card_uniqueness(self):
        changed = False

        for card in ALL_CARDS:
            owner = self._confirmed_owner(card)
            if owner is None:
                continue
            for entity in self.entities:
                if entity != owner:
                    changed |= self._assign(entity, card, False)

        return changed

    def _apply_singleton_assignments(self):
        changed = False

        for card in ALL_CARDS:
            owner = self._confirmed_owner(card)
            if owner is not None:
                continue

            possible_owners = self.get_possible_owners(card)
            if len(possible_owners) == 1:
                changed |= self._assign(next(iter(possible_owners)), card, True)

        return changed

    def _apply_player_card_limits(self):
        changed = False

        for player in self.player_names:
            confirmed = [card for card in ALL_CARDS if self.has_card[(player, card)] is True]
            unknown = [card for card in ALL_CARDS if self.has_card[(player, card)] is None]

            allowed = self.num_cards_per_player[player]
            remaining = allowed - len(confirmed)

            if remaining < 0:
                raise ContradictionError(f"{player} exceeds hand size")

            if remaining == 0:
                for card in unknown:
                    changed |= self._assign(player, card, False)

            if remaining == len(unknown):
                for card in unknown:
                    changed |= self._assign(player, card, True)

        return changed

    def _apply_clause_reduction(self):
        changed = False
        reduced_clauses = []

        for entity, cards in self.clauses:
            remaining = {card for card in cards if self.has_card[(entity, card)] is not False}

            if not remaining:
                raise ContradictionError(f"Unsatisfied clause for {entity}: {sorted(cards)}")

            if any(self.has_card[(entity, card)] is True for card in remaining):
                continue

            if len(remaining) == 1:
                changed |= self._assign(entity, next(iter(remaining)), True)
                continue

            reduced_clauses.append((entity, frozenset(remaining)))

        self.clauses = reduced_clauses
        return changed

    def _apply_envelope_category_rules(self):
        changed = False

        for category, cards in CATEGORIES.items():
            true_cards = [card for card in cards if self.has_card[(ENVELOPE, card)] is True]
            if len(true_cards) > 1:
                raise ContradictionError(f"Envelope has multiple {category} cards")

            if len(true_cards) == 1:
                true_card = true_cards[0]
                for card in cards:
                    if card != true_card:
                        changed |= self._assign(ENVELOPE, card, False)
                continue

            candidates = [card for card in cards if self.has_card[(ENVELOPE, card)] is not False]

            if not candidates:
                raise ContradictionError(f"Envelope has no {category} candidate")

            if len(candidates) == 1:
                changed |= self._assign(ENVELOPE, candidates[0], True)

        return changed

    def _check_consistency(self):
        for card in ALL_CARDS:
            if not self.get_possible_owners(card):
                raise ContradictionError(f"{card} has no possible owner")

        for player in self.player_names:
            confirmed = sum(1 for card in ALL_CARDS if self.has_card[(player, card)] is True)
            possible = sum(1 for card in ALL_CARDS if self.has_card[(player, card)] is not False)
            required = self.num_cards_per_player[player]

            if confirmed > required:
                raise ContradictionError(f"{player} has too many confirmed cards")
            if possible < required:
                raise ContradictionError(f"{player} cannot reach required hand size")

        for category in CATEGORIES:
            if not self.get_envelope_candidates(category):
                raise ContradictionError(f"Envelope has no {category} candidates")

        for entity, cards in self.clauses:
            remaining = [card for card in cards if self.has_card[(entity, card)] is not False]
            if not remaining:
                raise ContradictionError(f"Clause contradiction for {entity}")
