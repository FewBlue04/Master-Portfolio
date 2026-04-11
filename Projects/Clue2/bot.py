"""
Deterministic Clue bot.

Move choice is based on one-step constraint-reduction simulation with fixed
lexicographic tie-breaking. No probability or randomness is used.
"""

from __future__ import annotations

from engine.cards import SUSPECTS, WEAPONS
from engine.knowledge_base import ContradictionError, KnowledgeBase


class ClueBot:
    def __init__(self, name, kb):
        self.name = name
        self.kb = kb

    def take_turn(self, current_room, responder_order):
        if self.kb.can_accuse():
            suspect, weapon, room = self.kb.get_solution()
            return ("accuse", suspect, weapon, room)

        suspect, weapon, room = self.choose_best_move(current_room, responder_order)
        return ("suggest", suspect, weapon, room)

    def get_legal_suggestions(self, position):
        suggestions = [
            (suspect, weapon, position)
            for suspect in sorted(SUSPECTS)
            for weapon in sorted(WEAPONS)
        ]
        return suggestions

    def evaluate_move(self, move, responder_order):
        baseline = self.kb.snapshot_metrics()
        outcome_scores = []

        for branch in self._enumerate_outcomes(move, responder_order):
            outcome_scores.append(branch.score_delta(baseline))

        if not outcome_scores:
            return float("-inf")

        return min(outcome_scores)

    def choose_best_move(self, current_room, responder_order):
        best_move = None
        best_score = float("-inf")

        for move in self.get_legal_suggestions(current_room):
            score = self.evaluate_move(move, responder_order)
            if score > best_score or (score == best_score and (best_move is None or move < best_move)):
                best_score = score
                best_move = move

        return best_move

    def _enumerate_outcomes(self, move, responder_order):
        suspect, weapon, room = move
        cards = (suspect, weapon, room)
        outcomes = []

        for responder_index, responder in enumerate(responder_order):
            branch = self.kb.clone()
            try:
                for previous in responder_order[:responder_index]:
                    branch.observe_no_show(previous, suspect, weapon, room)
            except ContradictionError:
                continue

            candidate_cards = sorted(
                card for card in cards
                if branch.has_card[(responder, card)] is not False
            )

            for card in candidate_cards:
                shown_branch = branch.clone()
                try:
                    shown_branch.observe_showed_card_to_me(responder, card)
                except ContradictionError:
                    continue
                outcomes.append(shown_branch)

        no_refute_branch = self.kb.clone()
        try:
            for responder in responder_order:
                no_refute_branch.observe_no_show(responder, suspect, weapon, room)
        except ContradictionError:
            pass
        else:
            outcomes.append(no_refute_branch)

        return outcomes


class BotPlayer:
    def __init__(self, name, cards, all_players, num_cards_per_player, **_ignored):
        self.name = name
        self.cards = list(cards)
        self.all_players = list(all_players)
        self.num_cards_per_player = dict(num_cards_per_player)

        self.current_room = None
        self.eliminated = False
        self.is_human = False

        self.kb = KnowledgeBase(
            player_names=self.all_players,
            my_name=self.name,
            my_cards=self.cards,
            num_cards_per_player=self.num_cards_per_player,
        )
        self.policy = ClueBot(self.name, self.kb)

    def _responder_order(self):
        start = (self.all_players.index(self.name) + 1) % len(self.all_players)
        return [
            self.all_players[(start + offset) % len(self.all_players)]
            for offset in range(len(self.all_players) - 1)
        ]

    def should_accuse(self):
        return self.kb.can_accuse()

    def choose_accusation(self):
        return self.kb.get_solution()

    def choose_suggestion(self):
        responder_order = self._responder_order()
        return self.policy.choose_best_move(self.current_room, responder_order)

    def pick_card_to_show(self, suspect, weapon, room, asker_name):
        showable = sorted(card for card in (suspect, weapon, room) if card in self.cards)
        return showable[0]

    def observe_no_show(self, player, suspect, weapon, room):
        self.kb.observe_no_show(player, suspect, weapon, room)

    def observe_showed_card_to_me(self, player, card):
        self.kb.observe_showed_card_to_me(player, card)

    def observe_showed_card_to_other(self, player, suspect, weapon, room):
        self.kb.observe_showed_card_to_other(player, suspect, weapon, room)

    def get_knowledge_summary(self):
        metrics = self.kb.snapshot_metrics()
        suspect, weapon, room = self.kb.get_solution()
        return {
            "solved": self.kb.is_solved(),
            "solution": {
                "suspect": suspect,
                "weapon": weapon,
                "room": room,
            },
            "metrics": metrics,
        }
