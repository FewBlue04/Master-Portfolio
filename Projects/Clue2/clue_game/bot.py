"""
Deterministic Clue bot — one-step lookahead policy with constraint reduction.

Implements a deterministic AI that evaluates moves by simulating constraint
reduction outcomes. Uses fixed lexicographic tie-breaking and no randomness.
Depends on KnowledgeBase for deductions and GameStateTracker for history.
"""

from __future__ import annotations

from collections import deque

from .cards import ROOM_ADJACENCY, ROOMS, SECRET_PASSAGES, SUSPECTS, WEAPONS
from .knowledge_base import ContradictionError, KnowledgeBase


class ClueBot:
    """Deterministic bot with one-step lookahead policy based on constraint reduction.

    Evaluates legal suggestions by simulating all possible response outcomes and
    scoring them by the reduction in knowledge uncertainty. Uses fixed lexicographic
    tie-breaking and incorporates information pressure and repeat penalties.

    Args:
        name: Bot display name
        kb: KnowledgeBase instance for deductions

    Attributes:
        name: Bot display name
        kb: KnowledgeBase for tracking card knowledge
    """

    def __init__(self, name: str, kb: KnowledgeBase) -> None:
        self.name = name
        self.kb = kb

    def get_reachable_rooms(self, position: str | None) -> list[str]:
        """Return sorted list of rooms reachable from current position.

        Includes current room, adjacent rooms, and any secret passage destination.
        If position is invalid, returns all rooms (teleport for debugging).

        Args:
            position: Current room name or None

        Returns:
            Sorted list of reachable room names
        """
        if not position or position not in ROOM_ADJACENCY:
            return sorted(ROOMS)

        reachable = {position}
        reachable.update(ROOM_ADJACENCY.get(position, []))

        secret_room = SECRET_PASSAGES.get(position)
        if secret_room:
            reachable.add(secret_room)

        return sorted(reachable)

    def get_legal_suggestions(self, position: str) -> list[tuple[str, str, str]]:
        """Generate all legal (suspect, weapon, room) tuples from current position.

        Args:
            position: Current room name

        Returns:
            List of (suspect, weapon, room) tuples in lexicographic order
        """
        suggestions = [
            (suspect, weapon, room)
            for room in self.get_reachable_rooms(position)
            for suspect in sorted(SUSPECTS)
            for weapon in sorted(WEAPONS)
        ]
        return suggestions

    def evaluate_move(self, move: tuple[str, str, str], responder_order: list[str]) -> float:
        """Score a move by worst-case constraint reduction across all response outcomes.

        Uses minimax reasoning: assumes opponents will respond in the way that
        minimizes knowledge gain. Returns negative infinity if no valid responses.

        Args:
            move: (suspect, weapon, room) tuple to evaluate
            responder_order: List of player names in response order

        Returns:
            Worst-case score (lower = better, negative infinity = invalid)
        """
        baseline = self.kb.snapshot_metrics()
        outcome_scores = []

        for branch in self._enumerate_outcomes(move, responder_order):
            outcome_scores.append(branch.score_delta(baseline))

        if not outcome_scores:
            return float("-inf")

        return min(outcome_scores)

    def choose_best_move(
        self,
        current_room,
        responder_order,
        recent_suggestions=None,
        recent_rooms=None,
        no_progress_streak=0,
        debug=False,
    ):
        recent_suggestions = list(recent_suggestions or [])
        recent_rooms = list(recent_rooms or [])
        candidates = []

        for move in self.get_legal_suggestions(current_room):
            # Core evaluation: worst-case constraint reduction
            raw_score = self.evaluate_move(move, responder_order)
            # Bonus for cards with many possible owners (high information value)
            info_pressure = self._information_pressure(move)
            # Penalty for repeating recent suggestions to avoid loops
            repeat_penalty = self._repeat_penalty(
                move,
                recent_suggestions=recent_suggestions,
                recent_rooms=recent_rooms,
                no_progress_streak=no_progress_streak,
            )
            # Combined score: knowledge gain + exploration bonus - repetition penalty
            score = raw_score + info_pressure - repeat_penalty
            candidates.append(
                {
                    "move": move,
                    "score": score,
                    "raw_score": raw_score,
                    "info_pressure": info_pressure,
                    "repeat_penalty": repeat_penalty,
                }
            )

        # Sort by score (descending) then lexicographically for deterministic tie-breaking
        candidates.sort(key=lambda item: (-item["score"], item["move"]))
        # Apply escape rule: force exploration if stuck in local optimum
        filtered_candidates = self._apply_escape_rule(
            candidates,
            recent_suggestions=recent_suggestions,
            no_progress_streak=no_progress_streak,
        )

        best_move = None
        best_score = float("-inf")

        for candidate in filtered_candidates:
            move = candidate["move"]
            score = candidate["score"]
            # Select best score, with lexicographic tie-breaking for determinism
            if score > best_score or (
                score == best_score and (best_move is None or move < best_move)
            ):
                best_score = score
                best_move = move

        if debug:
            top_candidates = filtered_candidates[:3]
            print(
                f"[{self.name}] current_room={current_room} no_progress={no_progress_streak} "
                f"choice={best_move} candidates={top_candidates}"
            )

        return best_move

    def _information_pressure(self, move):
        suspect, weapon, room = move
        pressure = 0

        for card in (suspect, weapon, room):
            possible_owners = len(self.kb.get_possible_owners(card))
            pressure += max(0, len(self.kb.entities) - possible_owners)

            category = "room" if card in ROOMS else ("suspect" if card in SUSPECTS else "weapon")
            if card in self.kb.get_envelope_candidates(category):
                pressure += 1

        overlap = 0
        move_cards = {suspect, weapon, room}
        for entity, clause_cards in self.kb.clauses:
            overlap += len(move_cards & set(clause_cards))

        return pressure + overlap

    def _repeat_penalty(self, move, recent_suggestions, recent_rooms, no_progress_streak):
        penalty = 0

        for recency, previous_move in enumerate(reversed(recent_suggestions), start=1):
            if previous_move == move:
                penalty += max(1, 8 - recency)
            elif previous_move[2] == move[2]:
                penalty += max(0, 4 - recency)

        if no_progress_streak > 0:
            for recency, room in enumerate(reversed(recent_rooms), start=1):
                if room == move[2]:
                    penalty += max(1, 5 - recency) + min(no_progress_streak, 4)

        return penalty

    def _apply_escape_rule(self, candidates, recent_suggestions, no_progress_streak):
        if no_progress_streak < 3:
            return candidates

        recent_set = set(recent_suggestions)
        fresh_candidates = [
            candidate for candidate in candidates if candidate["move"] not in recent_set
        ]
        return fresh_candidates or candidates

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
                card for card in cards if branch.has_card[(responder, card)] is not False
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
    """In-game bot: wraps :class:`KnowledgeBase` and :class:`ClueBot` for turns and observations."""

    def __init__(self, name, cards, all_players, num_cards_per_player, debug=False, **_ignored):
        self.name = name
        self.cards = list(cards)
        self.all_players = list(all_players)
        self.num_cards_per_player = dict(num_cards_per_player)
        self.debug = debug

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
        self.recent_suggestions = deque(maxlen=6)
        self.recent_rooms = deque(maxlen=6)
        self.no_progress_streak = 0
        self.last_turn_metrics = None
        self.last_suggestion = None
        self.last_progress = False

    def _finalize_previous_turn(self):
        if self.last_turn_metrics is None:
            return

        current_metrics = self.kb.snapshot_metrics()
        progress = self.kb.score_delta(self.last_turn_metrics) > 0
        self.last_progress = progress
        self.no_progress_streak = 0 if progress else self.no_progress_streak + 1

        if self.debug:
            print(
                f"[{self.name}] previous_move={self.last_suggestion} progress={progress} "
                f"no_progress_streak={self.no_progress_streak} metrics={current_metrics}"
            )

        self.last_turn_metrics = None

    def _responder_order(self):
        start = (self.all_players.index(self.name) + 1) % len(self.all_players)
        return [
            self.all_players[(start + offset) % len(self.all_players)]
            for offset in range(len(self.all_players) - 1)
        ]

    def should_accuse(self):
        self._finalize_previous_turn()
        return self.kb.can_accuse()

    def choose_accusation(self):
        return self.kb.get_solution()

    def choose_suggestion(self):
        responder_order = self._responder_order()
        move = self.policy.choose_best_move(
            self.current_room,
            responder_order,
            recent_suggestions=self.recent_suggestions,
            recent_rooms=self.recent_rooms,
            no_progress_streak=self.no_progress_streak,
            debug=self.debug,
        )
        self.recent_suggestions.append(move)
        self.recent_rooms.append(move[2])
        self.last_suggestion = move
        self.last_turn_metrics = self.kb.snapshot_metrics()
        return move

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
            "no_progress_streak": self.no_progress_streak,
            "last_progress": self.last_progress,
        }
