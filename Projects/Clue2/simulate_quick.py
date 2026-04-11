"""Quick simulation (fewer trials) for faster feedback."""
import random
from collections import defaultdict

from engine.game import GameEngine
from engine.bot import BotPlayer
from engine.cards import ROOMS


def run_trials(num_bots, trials=20):
    wins = defaultdict(int)
    total_turns = 0
    for t in range(trials):
        g = GameEngine(human_name="Sim", num_bots=num_bots)
        human_name = g.human_name
        my_cards = list(g.players[human_name].cards)
        num_cards_per_player = {name: len(g.players[name].cards) for name in g.player_names}
        bot = BotPlayer(
            name=human_name,
            cards=my_cards,
            all_players=g.player_names,
            num_cards_per_player=num_cards_per_player,
        )
        bot.is_human = False
        bot.current_room = random.choice(ROOMS)
        g.players[human_name] = bot

        turns = 0
        while not g.game_over and turns < 2000:
            g.run_bot_turn()
            if not g.game_over:
                g.advance_turn()
            turns += 1

        winner = g.winner or "None"
        wins[winner] += 1
        total_turns += turns

    avg_turns = total_turns / trials if trials else 0
    return wins, avg_turns


def main():
    random.seed(42)
    configs = [1,2,3]
    trials = 20
    for nb in configs:
        print(f"Quick: {trials} trials with {nb} bots (+1 simulated human as bot)")
        wins, avg_turns = run_trials(nb, trials=trials)
        print(f" Avg turns: {avg_turns:.1f}")
        for k, v in sorted(wins.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")
        print("---")


if __name__ == '__main__':
    main()
