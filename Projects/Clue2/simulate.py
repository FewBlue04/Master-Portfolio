"""Headless simulation harness for deterministic Clue bot evaluation."""

from __future__ import annotations

import argparse
import random
import statistics
from collections import Counter

from engine.bot import BotPlayer
from engine.game import GameEngine


DEFAULT_TURN_CAP = 500
DEFAULT_STALL_LIMIT = 40


def create_all_bot_game(num_bots, seed=None):
    if seed is not None:
        random.seed(seed)

    game = GameEngine(human_name="Sim", num_bots=num_bots)
    human_name = game.human_name
    human_player = game.players[human_name]
    my_cards = list(human_player.cards)
    num_cards_per_player = {
        name: len(game.players[name].cards)
        for name in game.player_names
    }

    bot = BotPlayer(
        name=human_name,
        cards=my_cards,
        all_players=game.player_names,
        num_cards_per_player=num_cards_per_player,
    )
    bot.current_room = human_player.current_room
    bot.is_human = False
    game.players[human_name] = bot
    return game


def aggregate_bot_metrics(game):
    metrics = {
        "total_possible_owners": 0,
        "confirmed_assignments": 0,
        "envelope_candidate_total": 0,
        "solved_bots": 0,
    }

    for player in game.players.values():
        if player.is_human:
            continue
        snapshot = player.kb.snapshot_metrics()
        metrics["total_possible_owners"] += snapshot["total_possible_owners"]
        metrics["confirmed_assignments"] += snapshot["confirmed_assignments"]
        metrics["envelope_candidate_total"] += snapshot["envelope_candidate_total"]
        metrics["unresolved_clauses"] = metrics.get("unresolved_clauses", 0) + snapshot["unresolved_clauses"]
        metrics["solved_bots"] += int(player.kb.is_solved())

    return metrics


def metrics_progressed(before, after):
    return (
        after["total_possible_owners"] < before["total_possible_owners"]
        or after["confirmed_assignments"] > before["confirmed_assignments"]
        or after["envelope_candidate_total"] < before["envelope_candidate_total"]
        or after.get("unresolved_clauses", 0) < before.get("unresolved_clauses", 0)
        or after["solved_bots"] > before["solved_bots"]
    )


def run_single_game(num_bots, max_turns=DEFAULT_TURN_CAP, stall_limit=DEFAULT_STALL_LIMIT, seed=None, debug=False):
    game = create_all_bot_game(num_bots=num_bots, seed=seed)
    turns = 0
    no_progress_turns = 0
    baseline = aggregate_bot_metrics(game)
    peak_no_progress = 0

    if debug:
        print(f"seed={seed} players={game.player_names} baseline={baseline}")

    while not game.game_over and turns < max_turns:
        current_player = game.current_player_name
        events = game.run_bot_turn()
        turns += 1

        current_metrics = aggregate_bot_metrics(game)
        progressed = metrics_progressed(baseline, current_metrics)
        no_progress_turns = 0 if progressed else no_progress_turns + 1
        peak_no_progress = max(peak_no_progress, no_progress_turns)

        if debug:
            print(
                f"turn={turns} player={current_player} events={events} "
                f"metrics={current_metrics} progressed={progressed} "
                f"no_progress={no_progress_turns}"
            )

        if game.game_over:
            break

        if no_progress_turns >= stall_limit:
            break

        baseline = current_metrics

    if game.game_over:
        ended_by = "correct_accusation" if game.winner is not None else "all_eliminated"
    elif turns >= max_turns:
        ended_by = "turn_cap"
    else:
        ended_by = "stalled"

    suggestion_events = [
        event for event in game.state_tracker.suggestions
        if event["type"] == "suggestion"
    ]
    no_refute_events = [
        event for event in game.state_tracker.suggestions
        if event["type"] == "no_show" and event["passer"] is None
    ]
    accusations = list(game.state_tracker.accusations)
    correct_accusations = sum(1 for event in accusations if event["correct"])
    wrong_accusations = len(accusations) - correct_accusations

    result = {
        "num_bots": num_bots,
        "seed": seed,
        "winner": game.winner,
        "ended_by": ended_by,
        "turn_count": turns,
        "suggestion_count": len(suggestion_events),
        "no_refute_count": len(no_refute_events),
        "accusation_count": len(accusations),
        "correct_accusations": correct_accusations,
        "wrong_accusations": wrong_accusations,
        "max_consecutive_no_progress_turns": peak_no_progress,
        "final_metrics": aggregate_bot_metrics(game),
    }
    return result


def summarize_results(results):
    if not results:
        return {
            "games_played": 0,
            "average_turns": 0.0,
            "median_turns": 0.0,
            "solve_rate": 0.0,
            "stall_rate": 0.0,
            "turn_cap_rate": 0.0,
            "accusation_accuracy": 0.0,
            "average_suggestions": 0.0,
            "average_no_refutes": 0.0,
            "average_no_progress_streak": 0.0,
            "ended_by": {},
            "wins": {},
        }

    ended_by_counts = Counter(result["ended_by"] for result in results)
    win_counts = Counter(result["winner"] or "None" for result in results)
    total_turns = [result["turn_count"] for result in results]
    total_accusations = sum(result["accusation_count"] for result in results)
    total_correct = sum(result["correct_accusations"] for result in results)

    return {
        "games_played": len(results),
        "average_turns": statistics.mean(total_turns),
        "median_turns": statistics.median(total_turns),
        "solve_rate": ended_by_counts["correct_accusation"] / len(results),
        "stall_rate": ended_by_counts["stalled"] / len(results),
        "turn_cap_rate": ended_by_counts["turn_cap"] / len(results),
        "accusation_accuracy": (
            total_correct / total_accusations if total_accusations else 0.0
        ),
        "average_suggestions": statistics.mean(
            result["suggestion_count"] for result in results
        ),
        "average_no_refutes": statistics.mean(
            result["no_refute_count"] for result in results
        ),
        "average_no_progress_streak": statistics.mean(
            result["max_consecutive_no_progress_turns"] for result in results
        ),
        "ended_by": dict(ended_by_counts),
        "wins": dict(win_counts),
    }


def run_trials(num_bots, trials=100, max_turns=DEFAULT_TURN_CAP, stall_limit=DEFAULT_STALL_LIMIT, seed=12345, debug=False):
    results = []
    for index in range(trials):
        game_seed = None if seed is None else seed + index
        results.append(
            run_single_game(
                num_bots=num_bots,
                max_turns=max_turns,
                stall_limit=stall_limit,
                seed=game_seed,
                debug=debug,
            )
        )
    return results, summarize_results(results)


def print_summary(summary, num_bots):
    print(f"{summary['games_played']} games with {num_bots} bots (+ simulated human bot)")
    print(f"  Avg turns: {summary['average_turns']:.1f}")
    print(f"  Median turns: {summary['median_turns']:.1f}")
    print(f"  Solve rate: {summary['solve_rate']:.1%}")
    print(f"  Stall rate: {summary['stall_rate']:.1%}")
    print(f"  Turn-cap rate: {summary['turn_cap_rate']:.1%}")
    print(f"  Accusation accuracy: {summary['accusation_accuracy']:.1%}")
    print(f"  Avg suggestions: {summary['average_suggestions']:.1f}")
    print(f"  Avg no-refutes: {summary['average_no_refutes']:.1f}")
    print(f"  Avg max no-progress streak: {summary['average_no_progress_streak']:.1f}")
    print("  Ended by:")
    for label, count in sorted(summary["ended_by"].items()):
        print(f"    {label}: {count}")
    print("  Wins:")
    for label, count in sorted(summary["wins"].items(), key=lambda item: (-item[1], item[0])):
        print(f"    {label}: {count}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run deterministic Clue bot simulations.")
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--bot-configs", type=int, nargs="+", default=[1, 2, 3, 4])
    parser.add_argument("--max-turns", type=int, default=DEFAULT_TURN_CAP)
    parser.add_argument("--stall-limit", type=int, default=DEFAULT_STALL_LIMIT)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    for num_bots in args.bot_configs:
        results, summary = run_trials(
            num_bots=num_bots,
            trials=args.trials,
            max_turns=args.max_turns,
            stall_limit=args.stall_limit,
            seed=args.seed,
            debug=args.debug,
        )
        print_summary(summary, num_bots)
        print("---")


if __name__ == "__main__":
    main()
