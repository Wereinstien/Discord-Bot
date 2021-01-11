import glob
import numpy as np
import random
from PIL import Image


CARD_SHEETS = glob.glob('Cards/*.png')
STATES = {
    'SETUP': 0,
    'DRAW': 2,
    'NOMINATE': 3,
    'VOTE': 4,
}


class BadPeople:

    _game_state = STATES['SETUP']
    deck = []
    players = None
    nominees = []
    round = 0

    def __init__(self, players):
        if players:
            random.shuffle(players)
            self.players = {player: 0 for player in players}
            self._create_deck()
            self._game_state = STATES['DRAW']

    def _check_state(self, exp):
        if self._game_state != exp:
            raise ValueError('You cannot call this command at this time.')
        return 0

    def game_state(self):
        return self._game_state

    def _create_deck(self):
        self._check_state(STATES['SETUP'])

        for file in CARD_SHEETS:
            img = Image.open(file)
            width, height = img.size
            w_pad, h_pad = int(np.ceil(width / 4)), int(np.ceil(height / 4))

            for w in range(0, width, w_pad):
                for h in range(0, height, h_pad):
                    card = (w, h, w + w_pad, h + h_pad)
                    self.deck.append(img.crop(card))

        random.shuffle(self.deck)

    def get_dictator(self):
        if self.players:
            idx = self.round % len(self.players.keys())
            return list(self.players.keys())[idx]

        return None

    def draw_card(self):
        self._check_state(STATES['DRAW'])
        self._game_state = STATES['NOMINATE']
        return self.deck.pop()

    def nominate(self, player):
        self._check_state(STATES['NOMINATE'])
        if player in self.players.keys():
            if len(self.nominees) < 2:
                self.nominees.append(player)
            else:
                raise ValueError(f'You can only nominate two players.')
        else:
            raise ValueError(f'{player} is not playing.')

        if len(self.nominees) == 2:
            self._game_state = STATES['VOTE']

    def get_nominees(self):
        self._check_state(STATES['VOTE'])
        return self.nominees

    def winner(self, winner):
        self._check_state(STATES['VOTE'])

        game_winner = None

        if winner != -1:
            self.players[self.nominees[winner]] += 1
            game_winner = self.nominees[winner] if self.players[self.nominees[winner]] == 7 else None
        else:
            self.players[self.nominees[0]] += 1
            self.players[self.nominees[1]] += 1
            if self.players[self.nominees[0]] == self.players[self.nominees[1]] == 7:
                game_winner = f'{self.nominees[0]} and {self.nominees[1]}'
            else:
                game_winner = self.nominees[0] if self.players[self.nominees[0]] == 7 else None
                game_winner = self.nominees[1] if self.players[self.nominees[1]] == 7 else None

        self.nominees = []
        self.round += 1
        self._game_state = STATES['DRAW']
        return game_winner

    def score(self):
        return self.players
