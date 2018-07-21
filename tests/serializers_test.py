"""Unit tests for serializers."""

from django import test
from game import models as game_models
from game import serializers

import collections
import datetime


class GameRegistrationSerializerTest(test.TestCase):

    def setUp(self):
        self.game_object = game_models.GameRegistration(
            game_id='abcdefgh123456',
            created_timestamp=datetime.datetime(2018, 1, 1, 0, 0))
        self.game_object.errors = []

    def tearDown(self):
        self.game_object = None

    def test_game_registration_serializer__success(self):
        serializer_instance = serializers.GameRegistrationSerializer(
            self.game_object)
        assert serializer_instance.data == {'game_id': 'abcdefgh123456',
                                            'created': '2018-01-01T00:00:00Z'}

    def test_game_registration_serializer__error(self):
        self.game_object.add_error(
            game_models.Error(error_code=404, error_message='Game not found'))
        serializer_instance = serializers.GameRegistrationSerializer(
            self.game_object)
        errors = {'errors': [{'error_code': 404,
                              'error_message': 'Game not found'}]}
        expected = collections.OrderedDict(errors)
        assert serializer_instance.data == expected


class ScorePerFrameSerializerTest(test.TestCase):

    def setUp(self):
        self.game_object = game_models.GameRegistration(game_id='abcde12345')
        self.game_object.save()

    def test_score_per_frame__success__spare(self):
        score_per_frame = game_models.ScorePerFrame(
            game=self.game_object, first_attempt_score='5',
            second_attempt_score=5, third_attempt_score=0, frame=1,
            frame_version=1, frame_score=10)
        score_per_frame.save()
        serializer_instance = serializers.ScorePerFrameSerializer(
            score_per_frame)
        assert serializer_instance.data == {'game': 'abcde12345', 'frame': 1,
                                            'frame_score': None,
                                            'total_score_for_frame': None}

    def test_score_per_frame__success__strike(self):
        score_per_frame = game_models.ScorePerFrame(
            game=self.game_object, first_attempt_score='X',
            second_attempt_score=0, third_attempt_score=0, frame=1,
            frame_version=1, frame_score=10)
        score_per_frame.save()
        serializer_instance = serializers.ScorePerFrameSerializer(
            score_per_frame)
        assert serializer_instance.data == {'game': 'abcde12345', 'frame': 1,
                                            'frame_score': None,
                                            'total_score_for_frame': None}

    def test_score_per_frame__success__open_frame(self):
        score_per_frame = game_models.ScorePerFrame(
            game=self.game_object, first_attempt_score='2',
            second_attempt_score='4', third_attempt_score=0, frame=1,
            frame_version=1, frame_score=10)
        score_per_frame.save()
        serializer_instance = serializers.ScorePerFrameSerializer(
            score_per_frame)
        assert serializer_instance.data == {'game': 'abcde12345', 'frame': 1,
                                            'frame_score': 6,
                                            'total_score_for_frame': 6}

    def test_score_per_frame__failure(self):
        score_per_frame = game_models.ScorePerFrame(
            first_attempt_score=5, second_attempt_score=5,
            third_attempt_score=0, frame=1, frame_version=1, frame_score=10)
        score_per_frame.add_error(
            game_models.Error(
                error_code=400,
                error_message='Game has already been played.'))
        errors = {'errors': [
            {'error_code': 400,
             'error_message': 'Game has already been played.'}]}
        expected = collections.OrderedDict(errors)
        serializer_instance = serializers.ScorePerFrameSerializer(
            score_per_frame)
        assert serializer_instance.data == expected


class ScoreSerializerTest(test.TestCase):

    def test_calculate_score_for_game__open_frame(self):
        game = game_models.Game(game_id='abcde12345', total_score=6)
        serializer_instance = serializers.ScoreSerializer(game)
        assert serializer_instance.data == {
            'total_score': 6,
            'game_id': 'abcde12345'
        }

    def test_calculate_score_for_game__None(self):
        game = game_models.Game(total_score=None)
        serializer_instance = serializers.ScoreSerializer(game)
        assert serializer_instance.data == {
            'total_score': None,
            'game_id': None
        }
