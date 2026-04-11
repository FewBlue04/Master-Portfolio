import unittest

from clue_game.knowledge_base import ENVELOPE, ContradictionError, KnowledgeBase


class KnowledgeBaseTests(unittest.TestCase):
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
        self.kb = KnowledgeBase(self.player_names, "Me", self.my_cards, self.num_cards)

    def test_card_uniqueness_propagates(self):
        self.kb.observe_hand("A", "Miss Scarlett")

        self.assertTrue(self.kb.has_card[("A", "Miss Scarlett")])
        self.assertFalse(self.kb.has_card[("Me", "Miss Scarlett")])
        self.assertFalse(self.kb.has_card[("B", "Miss Scarlett")])
        self.assertFalse(self.kb.has_card[(ENVELOPE, "Miss Scarlett")])

    def test_player_card_completion_eliminates_remaining_cards(self):
        single_card_counts = {"Me": 6, "A": 1, "B": 11}
        kb = KnowledgeBase(self.player_names, "Me", self.my_cards, single_card_counts)

        kb.observe_hand("A", "Miss Scarlett")

        self.assertTrue(kb.has_card[("A", "Miss Scarlett")])
        self.assertFalse(kb.has_card[("A", "Candlestick")])
        self.assertFalse(kb.has_card[("A", "Kitchen")])

    def test_envelope_category_singleton_assigns_remaining_card(self):
        for suspect in (
            "Miss Scarlett",
            "Mrs. White",
            "Mr. Green",
            "Mrs. Peacock",
            "Prof. Plum",
        ):
            self.kb.add_constraint(ENVELOPE, suspect, False)

        self.assertTrue(self.kb.has_card[(ENVELOPE, "Col. Mustard")])

    def test_clause_reduction_forces_last_remaining_card(self):
        self.kb.observe_showed_unknown("A", "Miss Scarlett", "Candlestick", "Kitchen")
        self.kb.observe_no_show("A", "Miss Scarlett", "Candlestick", "Ballroom")

        self.assertTrue(self.kb.has_card[("A", "Kitchen")])

    def test_contradiction_is_raised(self):
        self.kb.observe_hand("A", "Miss Scarlett")

        with self.assertRaises(ContradictionError):
            self.kb.add_constraint("B", "Miss Scarlett", True)

    def test_clone_is_isolated(self):
        clone = self.kb.clone()
        clone.observe_hand("A", "Miss Scarlett")

        self.assertIsNone(self.kb.has_card[("A", "Miss Scarlett")])
        self.assertTrue(clone.has_card[("A", "Miss Scarlett")])


if __name__ == "__main__":
    unittest.main()
