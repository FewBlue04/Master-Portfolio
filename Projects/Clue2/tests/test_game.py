import unittest

from clue_game.bot import BotPlayer
from clue_game.cards import CARD_TYPE, ROOMS, SUSPECTS, WEAPONS
from clue_game.game import GameEngine


class GameEngineTests(unittest.TestCase):
    def test_simulated_human_seat_does_not_request_manual_show(self):
        game = GameEngine(human_name="Sim", num_bots=1)

        sim_name = game.human_name
        sim_player = game.players[sim_name]
        num_cards_per_player = {name: len(game.players[name].cards) for name in game.player_names}

        sim_bot = BotPlayer(
            name=sim_name,
            cards=list(sim_player.cards),
            all_players=game.player_names,
            num_cards_per_player=num_cards_per_player,
        )
        sim_bot.current_room = sim_player.current_room
        sim_bot.is_human = False
        game.players[sim_name] = sim_bot

        show_card = sim_bot.cards[0]
        suspect = SUSPECTS[0]
        weapon = WEAPONS[0]
        room = ROOMS[0]

        if CARD_TYPE[show_card] == "suspect":
            suspect = show_card
        elif CARD_TYPE[show_card] == "weapon":
            weapon = show_card
        else:
            room = show_card

        result = game.make_suggestion("Bot A", suspect, weapon, room)

        self.assertEqual(result["type"], "shown")
        self.assertFalse(game.awaiting_human_show)


if __name__ == "__main__":
    unittest.main()
