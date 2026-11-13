"""Chronology and equation checks; no historical outcome scoring."""
import unittest
from copy import deepcopy
from run import rating_at


def game(gid, day, home=1, away=2, rd=2, year=2024, neutral=False, resumed=False):
    return dict(game_id=gid, available_day=day, year=year, home=home, away=away,
                home_runs=max(rd, 0), away_runs=max(-rd, 0), valid=True,
                issues=[], neutral=neutral, resumed=resumed)


class RatingTests(unittest.TestCase):
    def test_target_same_day_and_future_independence(self):
        history = [game(1, '2024-04-01'), game(2, '2024-04-02', home=2, away=3)]
        rating, _ = rating_at(history, '2024-04-03', 2024, [1, 2, 3])
        extra = [game(3, '2024-04-03', rd=1000), game(4, '2024-04-04', rd=-1000),
                 game(5, '2022-04-01', rd=1000, year=2022)]
        changed, _ = rating_at(history + extra, '2024-04-03', 2024, [1, 2, 3])
        self.assertEqual(rating, changed)

    def test_resumption_is_not_available_until_next_day(self):
        history = [game(1, '2024-04-01'), game(2, '2024-04-05', home=2, away=3, resumed=True)]
        _, before = rating_at(history, '2024-04-05', 2024, [1, 2, 3])
        _, after = rating_at(history, '2024-04-06', 2024, [1, 2, 3])
        self.assertEqual(before['history_game_ids'], [1])
        self.assertEqual(after['history_game_ids'], [1, 2])
        self.assertEqual(after['resumed_games'], 1)

    def test_invalid_history_blocks(self):
        history = [game(1, '2024-04-01')]
        history[0]['valid'] = False
        with self.assertRaises(AssertionError):
            rating_at(history, '2024-04-02', 2024, [1, 2, 3])

    def test_neutral_shrinkage_matches_closed_form(self):
        history = [game(1, '2024-04-01', rd=4, neutral=True),
                   game(2, '2024-04-01', home=3, away=1, rd=0)]
        rating, details = rating_at(history, '2024-04-02', 2024, [1, 2, 3])
        w = 2 ** (-1 / 60)
        # The non-neutral game's residual is absorbed by h. Neutral game:
        # r1=-r2=4w/(2w+20), r3=0.
        self.assertAlmostEqual(rating[1], 4*w/(2*w+20), places=12)
        self.assertAlmostEqual(rating[2], -rating[1], places=12)
        self.assertAlmostEqual(rating[3], 0, places=12)
        self.assertEqual(details['neutral_games'], 1)

    def test_empty_history_and_previous_season_weight(self):
        rating, details = rating_at([], '2024-04-02', 2024, [1, 2, 3])
        self.assertEqual(rating, {1: 0., 2: 0., 3: 0.})
        self.assertTrue(details['fallback'])
        _, details = rating_at([game(1, '2023-12-31', year=2023)], '2024-01-01', 2024, [1, 2, 3])
        self.assertAlmostEqual(details['sum_weights'], .5 * 2**(-1/60))


if __name__ == '__main__':
    unittest.main()
