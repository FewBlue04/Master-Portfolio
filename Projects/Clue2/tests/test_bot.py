import unittest

from bot import BotPlayer, ClueBot
from knowledge_base import KnowledgeBase


class BotTests(unittest.TestCase):
    def setUp(self):
        self.player_names = ["Me", "A", "B"]
        self.my_cards = [
            "Mrs. White",
            "Mr. Green",
            "Mrs. Peacock",
            "Prof. Plum",
            "Lead Pipe",
            "Revolver",
        ]
        self.num_cards = {"Me": 6, "A": 6, "B": 6}

    def test_bot_only_accuses_when_solution_is_complete(self):
        player_names = ["Me", "A"]
        num_cards = {"Me": 6, "A": 12}
        my_cards = [
            "Mrs. White",
            "Mr. Green",
            "Mrs. Peacock",
            "Prof. Plum",
            "Lead Pipe",
            "Revolver",
        ]
        kb = KnowledgeBase(player_names, "Me", my_cards, num_cards)
        bot = ClueBot("Me", kb)

        self.assertFalse(bot.kb.can_accuse())

        for card in [
            "Col. Mustard",
            "Knife",
            "Rope",
            "Wrench",
            "Ballroom",
            "Conservatory",
            "Billiard Room",
            "Library",
            "Study",
            "Hall",
            "Lounge",
            "Dining Room",
        ]:
            kb.observe_hand("A", card)

        self.assertTrue(bot.kb.can_accuse())
        self.assertEqual(bot.kb.get_solution(), ("Miss Scarlett", "Candlestick", "Kitchen"))

    def test_tie_breaking_is_lexicographic(self):
        kb = KnowledgeBase(
            self.player_names,
            "Me",
            ["Kitchen", "Ballroom", "Conservatory", "Hall", "Lounge", "Study"],
            self.num_cards,
        )
        bot = ClueBot("Me", kb)

        move = bot.choose_best_move("Kitchen", ["A", "B"])

        self.assertEqual(move, ("Col. Mustard", "Candlestick", "Ballroom"))

    def test_legal_suggestions_include_reachable_rooms(self):
        kb = KnowledgeBase(self.player_names, "Me", self.my_cards, self.num_cards)
        bot = ClueBot("Me", kb)

        rooms = {move[2] for move in bot.get_legal_suggestions("Kitchen")}

        self.assertEqual(rooms, {"Kitchen", "Ballroom", "Dining Room", "Study"})

    def test_move_selection_prefers_guaranteed_reduction(self):
        kb = KnowledgeBase(self.player_names, "Me", self.my_cards, self.num_cards)
        kb.observe_no_show("A", "Miss Scarlett", "Candlestick", "Kitchen")
        kb.observe_no_show("B", "Miss Scarlett", "Candlestick", "Ballroom")
        bot = ClueBot("Me", kb)

        strong_move = ("Miss Scarlett", "Candlestick", "Dining Room")
        weak_move = ("Col. Mustard", "Knife", "Ballroom")

        strong_score = bot.evaluate_move(strong_move, ["A", "B"])
        weak_score = bot.evaluate_move(weak_move, ["A", "B"])

        self.assertGreater(strong_score, weak_score)

    def test_bot_can_choose_a_different_room(self):
        kb = KnowledgeBase(self.player_names, "Me", self.my_cards, self.num_cards)
        kb.observe_no_show("A", "Miss Scarlett", "Candlestick", "Kitchen")
        kb.observe_no_show("B", "Miss Scarlett", "Candlestick", "Ballroom")
        bot = ClueBot("Me", kb)

        self.assertEqual(
            bot.choose_best_move("Dining Room", ["A", "B"]),
            ("Miss Scarlett", "Candlestick", "Dining Room"),
        )

    def test_bot_player_api_matches_game_engine_expectations(self):
        player = BotPlayer("A", ["Miss Scarlett"], ["Me", "A"], {"Me": 17, "A": 1})
        player.current_room = "Kitchen"

        self.assertEqual(
            player.pick_card_to_show("Miss Scarlett", "Knife", "Kitchen", "Me"),
            "Miss Scarlett",
        )
        self.assertIn(player.choose_suggestion()[2], {"Ballroom", "Dining Room", "Kitchen", "Study"})

    def test_recent_repeat_is_penalized_after_no_progress(self):
        kb = KnowledgeBase(
            self.player_names,
            "Me",
            ["Kitchen", "Ballroom", "Conservatory", "Hall", "Lounge", "Study"],
            self.num_cards,
        )
        bot = ClueBot("Me", kb)
        bot.evaluate_move = lambda move, responder_order: 0
        bot._information_pressure = lambda move: 0

        move = bot.choose_best_move(
            "Kitchen",
            ["A", "B"],
            recent_suggestions=[("Col. Mustard", "Candlestick", "Ballroom")],
            recent_rooms=["Ballroom"],
            no_progress_streak=3,
        )

        self.assertEqual(move, ("Col. Mustard", "Candlestick", "Dining Room"))

    def test_bot_player_updates_no_progress_streak(self):
        player = BotPlayer("Me", self.my_cards, self.player_names, self.num_cards)

        player.last_turn_metrics = player.kb.snapshot_metrics()
        player.last_suggestion = ("Col. Mustard", "Candlestick", "Kitchen")
        player.should_accuse()
        self.assertEqual(player.no_progress_streak, 1)
        self.assertFalse(player.last_progress)

        player.last_turn_metrics = player.kb.snapshot_metrics()
        player.last_suggestion = ("Miss Scarlett", "Knife", "Ballroom")
        player.kb.observe_hand("A", "Miss Scarlett")
        player.should_accuse()
        self.assertEqual(player.no_progress_streak, 0)
        self.assertTrue(player.last_progress)


if __name__ == "__main__":
    unittest.main()
