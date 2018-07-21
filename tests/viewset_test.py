"""Unit tests for view set."""

import pytest

from rest_framework import status
from rest_framework import test

from django import urls

import collections


class ViewSetTest(test.APITestCase):

    def setUp(self):
        url = urls.reverse('register-game')
        response = self.client.post(url)
        actual = response.json()
        expected_type = {
            'game_id': str,
            'created': str
        }
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in actual:
            if key not in expected_type:
                pytest.fail('Unexpected key : {}'.format(key))
            assert isinstance(actual[key], expected_type[key])
        self.game_id = actual.get('game_id')

    def test_set_score(self):
        expected = [
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 1), ('frame_score', None),
                 ('total_score_for_frame', None)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 2),
                 ('frame_score', None), ('total_score_for_frame', 20)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 3), ('frame_score', 9),
                 ('total_score_for_frame', 46)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 4), ('frame_score', None),
                 ('total_score_for_frame', 46)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 5), ('frame_score', None),
                 ('total_score_for_frame', 66)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 6), ('frame_score', None),
                 ('total_score_for_frame', 66)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 7), ('frame_score', None),
                 ('total_score_for_frame', 96)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 8), ('frame_score', 5),
                 ('total_score_for_frame', 138)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 9), ('frame_score', None),
                 ('total_score_for_frame', 138)]),
            collections.OrderedDict(
                [('game', self.game_id), ('frame', 10), ('frame_score', 13),
                 ('total_score_for_frame', 168)])
        ]

        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', '7/3']
        actual = []
        for score in scores:
            url = urls.reverse('play-game', args=(self.game_id, score))
            response = self.client.post(url)
            actual.append(collections.OrderedDict(response.json().items()))
        assert expected == actual

    def test_get_score(self):
        score_url = urls.reverse('get-score', args=(self.game_id,))
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X']
        play_game_responses = {
            0: {'game_id': self.game_id, 'total_score': None},
            1: {'game_id': self.game_id, 'total_score': 20},
            2: {'game_id': self.game_id, 'total_score': 46},
            3: {'game_id': self.game_id, 'total_score': 46},
            4: {'game_id': self.game_id, 'total_score': 66},
            5: {'game_id': self.game_id, 'total_score': 66},
            6: {'game_id': self.game_id, 'total_score': 96}
        }
        for index, score in enumerate(scores):
            game_url = urls.reverse('play-game', args=(self.game_id, score))
            self.client.post(game_url)
            game_response = self.client.get(score_url)
            assert game_response.json() == play_game_responses[index]

    def test_get_score__last_all_strikes(self):
        score_url = urls.reverse('get-score', args=(self.game_id,))
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '4/', '2-3', 'X-X-X']
        play_game_responses = {
            0: {'game_id': self.game_id, 'total_score': None},
            1: {'game_id': self.game_id, 'total_score': 20},
            2: {'game_id': self.game_id, 'total_score': 46},
            3: {'game_id': self.game_id, 'total_score': 46},
            4: {'game_id': self.game_id, 'total_score': 66},
            5: {'game_id': self.game_id, 'total_score': 66},
            6: {'game_id': self.game_id, 'total_score': 96},
            7: {'game_id': self.game_id, 'total_score': 140},
            8: {'game_id': self.game_id, 'total_score': 157},
            9: {'game_id': self.game_id, 'total_score': 187},
        }
        for index, score in enumerate(scores):
            game_url = urls.reverse('play-game', args=(self.game_id, score))
            self.client.post(game_url)
            game_response = self.client.get(score_url)
            assert game_response.json() == play_game_responses[index]
