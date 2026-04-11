import unittest

from simulate import metrics_progressed, run_single_game, summarize_results


class SimulationTests(unittest.TestCase):
    def test_metrics_progressed_detects_reduction(self):
        before = {
            "total_possible_owners": 100,
            "confirmed_assignments": 10,
            "envelope_candidate_total": 12,
            "solved_bots": 0,
        }
        after = {
            "total_possible_owners": 98,
            "confirmed_assignments": 10,
            "envelope_candidate_total": 12,
            "solved_bots": 0,
        }

        self.assertTrue(metrics_progressed(before, after))
        self.assertFalse(metrics_progressed(before, before))

    def test_run_single_game_respects_turn_cap(self):
        result = run_single_game(num_bots=1, max_turns=1, stall_limit=50, seed=7, debug=False)

        self.assertEqual(result["turn_count"], 1)
        self.assertIn(result["ended_by"], {"turn_cap", "correct_accusation", "all_eliminated"})

    def test_summary_aggregates_results(self):
        summary = summarize_results(
            [
                {
                    "turn_count": 10,
                    "ended_by": "correct_accusation",
                    "winner": "Bot A",
                    "accusation_count": 1,
                    "correct_accusations": 1,
                    "suggestion_count": 8,
                    "no_refute_count": 2,
                    "max_consecutive_no_progress_turns": 4,
                },
                {
                    "turn_count": 20,
                    "ended_by": "stalled",
                    "winner": None,
                    "accusation_count": 2,
                    "correct_accusations": 0,
                    "suggestion_count": 15,
                    "no_refute_count": 1,
                    "max_consecutive_no_progress_turns": 10,
                },
            ]
        )

        self.assertEqual(summary["games_played"], 2)
        self.assertEqual(summary["average_turns"], 15)
        self.assertEqual(summary["median_turns"], 15)
        self.assertEqual(summary["solve_rate"], 0.5)
        self.assertEqual(summary["stall_rate"], 0.5)
        self.assertEqual(summary["accusation_accuracy"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
