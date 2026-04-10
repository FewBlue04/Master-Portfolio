"""
Clue Game Engine — manages game state, turns, and rules.
"""

import random
from engine.cards import SUSPECTS, WEAPONS, ROOMS, ALL_CARDS
from engine.bot import BotPlayer


class Player:
    """Simple human player model."""
    def __init__(self, name, cards):
        self.name = name
        self.cards = list(cards)
        self.current_room = random.choice(ROOMS)
        self.eliminated = False
        self.is_human = True


class GameEngine:
    def __init__(self, human_name="You", num_bots=3):
        self.human_name = human_name
        self.num_bots = max(1, min(num_bots, 5))  # 1-5 bots
        self.log = []  # event log for UI
        self.game_over = False
        self.winner = None
        self.solution = {}

        self._setup_game()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_game(self):
        """Shuffle cards, deal hands, create players."""
        # Pick solution
        self.solution = {
            "suspect": random.choice(SUSPECTS),
            "weapon":  random.choice(WEAPONS),
            "room":    random.choice(ROOMS),
        }

        # Remaining cards to deal
        remaining = [
            c for c in ALL_CARDS
            if c != self.solution["suspect"]
            and c != self.solution["weapon"]
            and c != self.solution["room"]
        ]
        random.shuffle(remaining)

        # Player names
        bot_names = [f"Bot {chr(65+i)}" for i in range(self.num_bots)]
        self.player_names = [self.human_name] + bot_names
        n_players = len(self.player_names)

        # Deal cards as evenly as possible
        hands = {name: [] for name in self.player_names}
        for i, card in enumerate(remaining):
            hands[self.player_names[i % n_players]].append(card)

        num_cards_per_player = {
            name: len(cards) for name, cards in hands.items()
        }

        # Create players
        self.players = {}
        self.players[self.human_name] = Player(self.human_name, hands[self.human_name])

        for bot_name in bot_names:
            bot = BotPlayer(
                name=bot_name,
                cards=hands[bot_name],
                all_players=self.player_names,
                num_cards_per_player=num_cards_per_player,
            )
            bot.current_room = random.choice(ROOMS)
            bot.is_human = False
            self.players[bot_name] = bot

        # Human player starting room
        self.players[self.human_name].current_room = random.choice(ROOMS)

        # Turn order
        self.turn_order = list(self.player_names)
        self.current_turn_index = 0
        self.current_player_name = self.turn_order[0]

        # Pending state
        self.pending_suggestion = None  # {suspect, weapon, room, asker}
        self.pending_responder_index = None
        self.awaiting_human_show = False
        self.awaiting_human_suggestion = False
        self.awaiting_human_move = False
        self.awaiting_human_accusation_choice = False

        self._log(f"Game started! Solution is hidden. {n_players} players.")
        self._log(f"Your cards: {', '.join(hands[self.human_name])}")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg, kind="info"):
        self.log.append({"msg": msg, "kind": kind})

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    def get_current_player(self):
        return self.players[self.current_player_name]

    def is_human_turn(self):
        return self.current_player_name == self.human_name

    def advance_turn(self):
        """Move to the next non-eliminated player."""
        while True:
            self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
            name = self.turn_order[self.current_turn_index]
            if not self.players[name].eliminated:
                self.current_player_name = name
                break

    # ------------------------------------------------------------------
    # Suggestions
    # ------------------------------------------------------------------

    def make_suggestion(self, asker_name, suspect, weapon, room):
        """
        Process a suggestion. Returns event dict describing what happened.
        """
        asker = self.players[asker_name]
        # Move suspect to room
        if suspect in self.players:
            self.players[suspect].current_room = room
        asker.current_room = room

        self._log(
            f"💬 {asker_name} suggests: {suspect}, {weapon}, in {room}",
            "suggestion"
        )

        # Find who can show
        order = self.turn_order
        start = (order.index(asker_name) + 1) % len(order)

        self.pending_suggestion = {
            "asker": asker_name,
            "suspect": suspect,
            "weapon": weapon,
            "room": room,
        }

        result = self._resolve_suggestion(start)
        return result

    def _resolve_suggestion(self, start_index):
        """
        Walk through players after asker to find who can show a card.
        Returns dict with outcome.
        """
        order = self.turn_order
        asker_name = self.pending_suggestion["asker"]
        suspect = self.pending_suggestion["suspect"]
        weapon = self.pending_suggestion["weapon"]
        room = self.pending_suggestion["room"]

        n = len(order)
        for i in range(n - 1):
            idx = (start_index + i) % n
            responder_name = order[idx]
            responder = self.players[responder_name]

            if responder.eliminated:
                continue

            can_show = [c for c in (suspect, weapon, room) if c in responder.cards]

            if not can_show:
                # Cannot show — all bots learn this
                self._notify_no_show(responder_name, asker_name, suspect, weapon, room)
                self._log(f"   ❌ {responder_name} cannot show any card.", "nope")
            else:
                # Can show — handle human/bot differently
                if responder_name == self.human_name:
                    # Need UI to ask human what to show
                    self.awaiting_human_show = True
                    self.pending_responder_index = idx
                    return {
                        "type": "await_human_show",
                        "cards_can_show": can_show,
                        "asker": asker_name,
                    }
                else:
                    # Bot picks a card; give the bot the asker's identity so it can
                    # prefer showing a card the asker already knows.
                    if responder.is_human:
                        card = random.choice(can_show)
                    else:
                        card = responder.pick_card_to_show(suspect, weapon, room, asker_name)

                    self._notify_show(responder_name, asker_name, card, suspect, weapon, room)
                    return {"type": "shown", "shower": responder_name, "asker": asker_name, "card": card if asker_name == self.human_name else None}

        # Nobody could show
        self._log(f"   🚨 Nobody could refute the suggestion!", "alert")
        return {"type": "no_refute"}

    def human_shows_card(self, card):
        """Human chose to show this card."""
        asker = self.pending_suggestion["asker"]
        s = self.pending_suggestion["suspect"]
        w = self.pending_suggestion["weapon"]
        r = self.pending_suggestion["room"]

        self._notify_show(self.human_name, asker, card, s, w, r)
        self.awaiting_human_show = False
        result = {"type": "shown", "shower": self.human_name, "asker": asker, "card": None}
        return result

    def _notify_no_show(self, passer, asker, suspect, weapon, room):
        """Tell all bots that `passer` couldn't show."""
        for name, player in self.players.items():
            if not player.is_human and name != passer:
                player.observe_no_show(passer, suspect, weapon, room)

    def _notify_show(self, shower, asker, card, suspect, weapon, room):
        """Distribute show event to appropriate bots."""
        if asker == self.human_name:
            self._log(f"   ✅ {shower} shows you: {card}", "reveal")
        else:
            self._log(f"   ✅ {shower} shows {asker} a card (unknown to you).", "reveal")

        for name, player in self.players.items():
            if player.is_human:
                continue
            if name == shower:
                continue
            if name == asker:
                # Asker sees the actual card
                player.observe_showed_card_to_me(shower, card)
            else:
                # Others only know someone showed something
                player.observe_showed_card_to_other(shower, suspect, weapon, room)

    # ------------------------------------------------------------------
    # Accusations
    # ------------------------------------------------------------------

    def make_accusation(self, accuser_name, suspect, weapon, room):
        correct = (
            suspect == self.solution["suspect"] and
            weapon  == self.solution["weapon"] and
            room    == self.solution["room"]
        )

        self._log(
            f"⚖️  {accuser_name} accuses: {suspect}, {weapon}, {room}",
            "accusation"
        )

        if correct:
            self._log(f"🏆 {accuser_name} is CORRECT! Game over!", "win")
            self.game_over = True
            self.winner = accuser_name
            return {"type": "correct", "accuser": accuser_name}
        else:
            self._log(f"💀 {accuser_name} is WRONG! Eliminated.", "wrong")
            self.players[accuser_name].eliminated = True
            # Check if all eliminated
            active = [p for p in self.player_names if not self.players[p].eliminated]
            if len(active) == 0:
                self._log("💀 All players eliminated. Nobody wins!", "gameover")
                self.game_over = True
                self.winner = None
            return {"type": "wrong", "accuser": accuser_name}

    # ------------------------------------------------------------------
    # Bot turn automation
    # ------------------------------------------------------------------

    def run_bot_turn(self):
        """
        Run a full bot turn. Returns list of events for UI.
        """
        bot_name = self.current_player_name
        bot = self.players[bot_name]

        if bot.eliminated:
            self.advance_turn()
            return [{"type": "skip", "player": bot_name}]

        events = []

        # Check if bot wants to accuse
        if bot.should_accuse():
            s, w, r = bot.choose_accusation()
            result = self.make_accusation(bot_name, s, w, r)
            events.append(result)
            if not self.game_over:
                self.advance_turn()
            return events

        # Otherwise make a suggestion
        s, w, r = bot.choose_suggestion()
        bot.current_room = r
        result = self.make_suggestion(bot_name, s, w, r)
        events.append(result)

        # If awaiting human show, stop — UI will call human_shows_card
        if result.get("type") == "await_human_show":
            return events

        if not self.game_over:
            self.advance_turn()

        return events

    # ------------------------------------------------------------------
    # Queries for UI
    # ------------------------------------------------------------------

    def get_human_cards(self):
        return self.players[self.human_name].cards

    def get_human_room(self):
        return self.players[self.human_name].current_room

    def get_all_rooms(self):
        return ROOMS

    def get_player_rooms(self):
        return {name: p.current_room for name, p in self.players.items()}

    def get_bot_knowledge(self, bot_name):
        """Get bot's KB notebook for display."""
        bot = self.players.get(bot_name)
        if bot and not bot.is_human:
            return bot.kb.get_notebook()
        return {}

    def get_bot_solution_known(self, bot_name):
        bot = self.players.get(bot_name)
        if bot and not bot.is_human:
            return bot.kb.get_solution()
        return (None, None, None)

    def get_all_bot_summaries(self):
        summaries = {}
        for name, player in self.players.items():
            if not player.is_human:
                summaries[name] = player.get_knowledge_summary()
        return summaries
