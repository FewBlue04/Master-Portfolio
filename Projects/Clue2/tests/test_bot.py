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

        self.assertEqual(move, ("Col. Mustard", "Candlestick", "Kitchen"))

    def test_move_selection_prefers_guaranteed_reduction(self):
        kb = KnowledgeBase(self.player_names, "Me", self.my_cards, self.num_cards)
        kb.observe_no_show("A", "Miss Scarlett", "Candlestick", "Kitchen")
        kb.observe_no_show("B", "Miss Scarlett", "Candlestick", "Ballroom")
        bot = ClueBot("Me", kb)

        strong_move = ("Miss Scarlett", "Candlestick", "Kitchen")
        weak_move = ("Col. Mustard", "Knife", "Kitchen")

        strong_score = bot.evaluate_move(strong_move, ["A", "B"])
        weak_score = bot.evaluate_move(weak_move, ["A", "B"])

        self.assertGreater(strong_score, weak_score)
        self.assertEqual(bot.choose_best_move("Kitchen", ["A", "B"]), strong_move)

    def test_bot_player_api_matches_game_engine_expectations(self):
        player = BotPlayer("A", ["Miss Scarlett"], ["Me", "A"], {"Me": 17, "A": 1})
        player.current_room = "Kitchen"

        self.assertEqual(
            player.pick_card_to_show("Miss Scarlett", "Knife", "Kitchen", "Me"),
            "Miss Scarlett",
        )
        self.assertEqual(player.choose_suggestion()[2], "Kitchen")


if __name__ == "__main__":
    unittest.main()
