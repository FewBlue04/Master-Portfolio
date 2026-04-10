"""
Clue Bot Player — uses KnowledgeBase for optimal play.
"""

from engine.knowledge_base import KnowledgeBase
from engine.cards import SUSPECTS, WEAPONS, ROOMS, CARD_TYPE, ROOM_ADJACENCY, SECRET_PASSAGES


class BotPlayer:
    def __init__(self, name, cards, all_players, num_cards_per_player):
        self.name = name
        self.cards = list(cards)
        self.current_room = None
        self.eliminated = False

        self.kb = KnowledgeBase(
            player_names=all_players,
            my_name=name,
            my_cards=self.cards,
            num_cards_per_player=num_cards_per_player,
        )

    # ------------------------------------------------------------------
    # Observation callbacks (called by game engine)
    # ------------------------------------------------------------------

    def observe_no_show(self, player, suspect, weapon, room):
        """Another player passed — they have none of the three cards."""
        self.kb.observe_no_show(player, suspect, weapon, room)

    def observe_showed_card_to_other(self, shower, suspect, weapon, room):
        """
        `shower` showed a card to another player (not us).
        We know shower has at least one of suspect/weapon/room.
        """
        self.kb.observe_showed_unknown(shower, suspect, weapon, room)

    def observe_showed_card_to_me(self, shower, card):
        """Another player showed THIS specific card to us."""
        self.kb.observe_hand(shower, card)

    # ------------------------------------------------------------------
    # Decision methods
    # ------------------------------------------------------------------

    def choose_suggestion(self):
        """
        Returns (suspect, weapon, room) — the best suggestion to make.
        Uses KB scoring to maximize expected information gain.
        """
        # Build responder order starting with the next player after this bot
        if self.name in self.kb.player_names:
            idx = self.kb.player_names.index(self.name)
            responder_order = self.kb.player_names[idx+1:] + self.kb.player_names[:idx]
        else:
            responder_order = list(self.kb.player_names)

        # Allow the bot to consider moving: current room, adjacent rooms, and secret passage.
        candidates = []
        cur = self.current_room
        if cur:
            candidates.append(cur)
            # adjacent
            for nb in ROOM_ADJACENCY.get(cur, []):
                if nb not in candidates:
                    candidates.append(nb)
            # secret passage
            sp = SECRET_PASSAGES.get(cur)
            if sp and sp not in candidates:
                candidates.append(sp)
        else:
            # If no current room known, try all rooms
            candidates = list(ROOMS)

        # Aggressive envelope-driven shortcut: if envelope probabilities point
        # strongly to particular candidates, suggest them directly to confirm.
        env_probs = self.kb.get_envelope_probabilities()
        def top_candidate(lst):
            best = None
            best_p = 0.0
            for c in lst:
                p = env_probs.get(c, 0.0)
                if p > best_p:
                    best_p = p
                    best = c
            return best, best_p

        s_top, s_p = top_candidate(SUSPECTS)
        w_top, w_p = top_candidate(WEAPONS)
        r_top, r_p = top_candidate(ROOMS)

        # If any candidate is very likely, or average confidence is high, push that triple.
        if (s_p >= 0.6 or w_p >= 0.6 or r_p >= 0.6) or ((s_p + w_p + r_p) / 3.0) >= 0.45:
            # Prefer current room if r_top is low confidence
            chosen_room = r_top if r_p >= 0.4 else (self.current_room or r_top)
            if chosen_room is None:
                chosen_room = self.current_room or ROOMS[0]
            return (s_top or SUSPECTS[0], w_top or WEAPONS[0], chosen_room)

        best_trip = None
        best_score = float('-inf')
        for room in candidates:
            s, w, r, score = self.kb.best_suggestion(available_room=room, responder_order=responder_order)
            # small movement penalty: prefer staying in place
            move_penalty = 0.0 if room == cur else 0.2
            adj_penalty = 0.1 if room in ROOM_ADJACENCY.get(cur, []) else 0.0
            score_adj = score - (move_penalty + adj_penalty)
            if score_adj > best_score:
                best_score = score_adj
                best_trip = (s, w, r)

        if best_trip:
            return best_trip
        # fallback
        s, w, r, score = self.kb.best_suggestion(available_room=self.current_room, responder_order=responder_order)
        return s, w, r

    def choose_accusation(self):
        """
        Returns (suspect, weapon, room) if we're confident enough to accuse,
        else None.
        """
        sol_s, sol_w, sol_r = self.kb.get_solution()
        if sol_s and sol_w and sol_r:
            return sol_s, sol_w, sol_r

        # Partial-solution heuristic: if for each category there is exactly one
        # high-probability envelope candidate (based on envelope probs), accuse.
        probs = self.kb.get_envelope_probabilities()
        # Get top candidate per category
        def top_candidate(lst):
            best = None
            best_p = 0.0
            for c in lst:
                p = probs.get(c, 0.0)
                if p > best_p:
                    best_p = p
                    best = c
            return best, best_p

        s_c, s_p = top_candidate(SUSPECTS)
        w_c, w_p = top_candidate(WEAPONS)
        r_c, r_p = top_candidate(ROOMS)

        # Require reasonably high confidence across all three to accuse
        if s_p >= 0.85 and w_p >= 0.85 and r_p >= 0.85:
            return s_c, w_c, r_c
        return None

    def should_accuse(self):
        return self.kb.is_solved()

    def pick_card_to_show(self, suspect, weapon, room, asker_name=None):
        """
        When asked to show a card, pick the one that reveals least info.
        Prefer showing cards that are already known by the asker if possible,
        otherwise show the one held by the most other players.
        """
        can_show = [c for c in (suspect, weapon, room) if c in self.cards]
        if not can_show:
            return None
        # Prefer showing a card that the asker likely already knows (minimize leak).
        # The GameEngine will call BotPlayer.pick_card_to_show only when some human
        # or bot asked; we don't have the asker's identity here, so prefer:
        # 1) card known to many players (common)
        # 2) card type already solved in KB
        # 3) card with lowest entropy (few unknowns)

        # Score each candidate; prefer cards asker likely already knows (if asker provided)
        def card_score(card):
            score = 0.0
            # If KB knows some player definitely has it, it's "common" (less new info)
            owner_known = any(self.kb.has_card.get((p, card)) is True for p in self.kb.player_names)
            if owner_known:
                score += 5.0

            # If asker already has this card (confirmed), prefer showing it
            if asker_name is not None:
                asker_has = self.kb.has_card.get((asker_name, card))
                if asker_has is True:
                    score += 10.0
                elif asker_has is None:
                    # small boost if asker might have it (unknown)
                    score += 1.0

            # If type already solved, showing it leaks less
            sol_s, sol_w, sol_r = self.kb.get_solution()
            ctype = CARD_TYPE[card]
            if (ctype == "suspect" and sol_s) or (ctype == "weapon" and sol_w) or (ctype == "room" and sol_r):
                score += 3.0

            # Fewer unknown owners => more common
            none_count = sum(1 for p in self.kb.player_names if self.kb.has_card.get((p, card)) is None)
            score += (len(self.kb.player_names) - none_count)

            return score

        best = max(can_show, key=card_score)
        return best

    def get_knowledge_summary(self):
        """Returns a human-readable summary for UI display."""
        sol_s, sol_w, sol_r = self.kb.get_solution()
        lines = []
        if sol_s:
            lines.append(f"✓ Murderer: {sol_s}")
        else:
            lines.append("? Murderer: unknown")
        if sol_w:
            lines.append(f"✓ Weapon: {sol_w}")
        else:
            lines.append("? Weapon: unknown")
        if sol_r:
            lines.append(f"✓ Room: {sol_r}")
        else:
            lines.append("? Room: unknown")
        return "\n".join(lines)
