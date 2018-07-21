from unittest import mock

import pytest
from pytest import mark

from django import db as django_db
from django import test

from django_mock_queries import query as mock_query

from game import models as game_models
from game import services
from game import exceptions


class GamerRegistrationMockTest(test.TestCase):

    @mark.django_db(transaction=False)
    def test_register_name__success(self):
        """Tests if the game registration succeeds."""
        with mock.patch('game.models.GameRegistration'):
            game_object = services.register_game()
            assert game_object.save.call_count == 1

    @mark.django_db(transaction=False)
    def test_register_name__error(self):
        """Tests if the game registration fails."""
        error_list = []

        def add_error(err):
            error_list.append(err)

        expected_mock = mock.Mock()
        expected_mock.add_error = mock.MagicMock(side_effect=add_error)
        save_method = mock.MagicMock(
            side_effect=django_db.DatabaseError('test'))
        expected_mock.save = save_method
        with mock.patch(
                'game.models.GameRegistration',
                side_effect=lambda: expected_mock):
            game_object = services.register_game()
            assert game_object == expected_mock
            assert game_object.save.call_count == 1
            assert game_object.add_error.call_count == 1
            assert error_list == [game_models.Error(
                error_code=500,
                error_message='Unable to register the game.')]

    def test_register_game__transactional_support(self):
        game_object = services.register_game()
        assert game_object is not None
        assert game_object.errors == []


class SetScoreFrameScoreTest(test.TestCase):
    """Unit tests to verify creating a bowling score."""

    def setUp(self):
        self.game_registration = game_models.GameRegistration.objects.create()
        self.queryset = game_models.ScorePerFrame.objects.select_related('game')

    def test_set_frame_score__game_object_not_found(self):
        score_object = services.set_frame_score(
            self.queryset, 'abcde12345', 'X')
        assert score_object.errors == [
            game_models.Error(
                error_code=404,
                error_message='No game was found for the game id: abcde12345.')]
        assert score_object.frame_score is None
        assert score_object.first_attempt_score is None
        assert score_object.second_attempt_score is None
        assert score_object.third_attempt_score is None

    def test_set_frame_score__invalid_score_format(self):
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'XX')
        assert score_object.errors == [
            game_models.Error(
                error_code=400,
                error_message='Score format: XX is invalid.')]
        assert score_object.frame_score is None
        assert score_object.first_attempt_score is None
        assert score_object.second_attempt_score is None
        assert score_object.third_attempt_score is None

    def test_set_frame_score__create_first_frame_strike(self):
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X')
        assert score_object.errors == []
        assert score_object.first_attempt_score == 'X'
        assert score_object.second_attempt_score == 0
        assert score_object.third_attempt_score == 0
        assert score_object.frame_score is None
        assert score_object.total_score_for_frame is None
        assert score_object.frame_version == 1
        assert score_object.frame == 1

    def test_set_frame_score__create_first_frame_spare(self):
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, '3/')
        assert score_object.errors == []
        assert score_object.first_attempt_score == '3'
        assert score_object.second_attempt_score == 7
        assert score_object.third_attempt_score == 0
        assert score_object.frame == 1
        assert score_object.frame_score is None
        assert score_object.total_score_for_frame is None
        assert score_object.frame_version == 1

    def test_set_frame_score__create_first_frame_open_frame(self):
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, '3-5')
        assert score_object.errors == []
        assert score_object.first_attempt_score == '3'
        assert score_object.second_attempt_score == '5'
        assert score_object.third_attempt_score == 0
        assert score_object.frame == 1
        assert score_object.frame_score == 8
        assert score_object.frame_version == 1
        assert score_object.total_score_for_frame == 8

    def test_set_frame_score__multiple_frames(self):
        services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X')
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, '7/')
        assert score_object.errors == []
        assert score_object.first_attempt_score == '7'
        assert score_object.second_attempt_score == 3
        assert score_object.third_attempt_score == 0
        assert score_object.frame == 2
        assert score_object.frame_score is None
        assert score_object.frame_version == 1

    def test_set_frame_score__race_condition_version_raises_error(self):
        services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X')
        with mock.patch('django.db.models.query.QuerySet.values_list',
                        return_value=mock_query.MockSet((0,))), \
                mock.patch('django.db.models.query.QuerySet.aggregate',
                           return_value={'frame_max': 0}):
            score_object = services.set_frame_score(
                self.queryset, self.game_registration.game_id, '2-3')
            assert score_object.errors == [
                game_models.Error(
                    error_code=500,
                    error_message=(
                        'Unable to save score: \'2-3\' for '
                        'game: \'{game}\'.'.format(
                            game=self.game_registration.game_id)))]
            assert score_object.frame_score is None
            assert score_object.first_attempt_score is None
            assert score_object.second_attempt_score is None
            assert score_object.third_attempt_score is None

    def test_set_frame_score__game_has_been_played(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', '7/3']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X')
        assert score_object.errors == [
            game_models.Error(
                error_code=400,
                error_message='Game:\'{}\' has already been played.'.format(
                    self.game_registration.game_id))]
        assert score_object.frame_score is None
        assert score_object.first_attempt_score is None
        assert score_object.second_attempt_score is None
        assert score_object.third_attempt_score is None

    def test_set_frame_score__last_attempt_all_strikes(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X-X-X')
        assert score_object.errors == []
        assert score_object.frame_score == 30
        assert score_object.first_attempt_score == 'X'
        assert score_object.second_attempt_score == 'X'
        assert score_object.third_attempt_score == 'X'
        assert score_object.total_score_for_frame == 188
        # Asserting total frames
        total_scores = [
            score for score in game_models.ScorePerFrame.objects.select_related(
                'game').filter(game=self.game_registration.game_id).values_list(
                'total_score_for_frame', flat=True)]
        assert total_scores == [20, 37, 46, 66, 96, 118, 133, 138, 158, 188]

    def test_set_frame_score__last_attempt_two_strikes_open_frame(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X-X-9')
        assert score_object.errors == []
        assert score_object.frame_score == 29
        assert score_object.first_attempt_score == 'X'
        assert score_object.second_attempt_score == 'X'
        assert score_object.third_attempt_score == '9'
        # Asserting total frames
        total_scores = [
            score for score in game_models.ScorePerFrame.objects.select_related(
                'game').filter(game=self.game_registration.game_id).values_list(
                'total_score_for_frame', flat=True)]
        assert total_scores == [20, 37, 46, 66, 96, 118, 133, 138, 158, 187]

    def test_set_frame_score__last_attempt_one_strikes_open_frame(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X-2-5')
        assert score_object.errors == []
        assert score_object.frame_score == 17
        assert score_object.first_attempt_score == 'X'
        assert score_object.second_attempt_score == '2'
        assert score_object.third_attempt_score == '5'
        # Asserting total frames
        total_scores = [
            score for score in game_models.ScorePerFrame.objects.select_related(
                'game').filter(game=self.game_registration.game_id).values_list(
                'total_score_for_frame', flat=True)]
        assert total_scores == [20, 37, 46, 66, 96, 118, 133, 138, 158, 175]

    def test_set_frame_score__last_attempt_spare(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, '7/5')
        assert score_object.errors == []
        assert score_object.frame_score == 15
        assert score_object.first_attempt_score == '7'
        assert score_object.second_attempt_score == 3
        assert score_object.third_attempt_score == '5'
        # Asserting total frames
        total_scores = [
            score for score in game_models.ScorePerFrame.objects.select_related(
                'game').filter(game=self.game_registration.game_id).values_list(
                'total_score_for_frame', flat=True)]
        assert total_scores == [20, 37, 46, 66, 96, 118, 133, 138, 155, 170]

    def test_set_frame_score__last_attempt_open_frame(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, '2-3')
        assert score_object.errors == []
        assert score_object.frame_score == 5
        assert score_object.first_attempt_score == '2'
        assert score_object.second_attempt_score == '3'
        assert score_object.third_attempt_score == 0
        # Asserting total frames
        total_scores = [
            score for score in game_models.ScorePerFrame.objects.select_related(
                'game').filter(game=self.game_registration.game_id).values_list(
                'total_score_for_frame', flat=True)]
        assert total_scores == [20, 37, 46, 66, 96, 118, 133, 138, 150, 155]

    def test_set_frame_score__last_attempt_strike_spare(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        score_object = services.set_frame_score(
            self.queryset, self.game_registration.game_id, 'X-7/')
        assert score_object.errors == []
        assert score_object.frame_score == 20
        assert score_object.first_attempt_score == 'X'
        assert score_object.second_attempt_score == '7'
        assert score_object.third_attempt_score == 3
        # Asserting total frames
        total_scores = [
            score for score in game_models.ScorePerFrame.objects.select_related(
                'game').filter(game=self.game_registration.game_id).values_list(
                'total_score_for_frame', flat=True)]
        assert total_scores == [20, 37, 46, 66, 96, 118, 133, 138, 158, 178]


class ParseScoreTest(test.TestCase):

    def test_parse_score__invalid_score(self):
        with pytest.raises(
                exceptions.MissingScoreException,
                message='Scoring is not available for frame: 5'):
            services._parse_score('', 5)

    def test_parse_score__invalid_strike_score_last_attempt(self):
        with pytest.raises(
                exceptions.InvalidScoreLengthForFrame,
                message=('{scoring_type} {score} has an incorrect number of '
                         'attempts for frame: {frame}.'.format(
                             scoring_type=services.SCORING_TYPE_STRIKE,
                             score='X-X', frame=10))):
            services._parse_score('X-X', 10)

    def test_parse_score__invalid_spare_score_last_attempt_2(self):
        with pytest.raises(
                exceptions.InvalidScoreLengthForFrame,
                message=('{scoring_type} {score} has an incorrect attempts for '
                         'frame: {frame}.'.format(
                             scoring_type=services.SCORING_TYPE_SPARE,
                             score='7/', frame=10))):
            services._parse_score('7/', 10)

    def test_parse_score__invalid_strike_score_prior_to_last_attempt(self):
        with pytest.raises(
                exceptions.InvalidScoreLengthForFrame,
                message=('{scoring_type} {score} has an incorrect attempts for '
                         'frame: {frame}.'.format(
                             scoring_type=services.SCORING_TYPE_STRIKE,
                             score='X-X', frame=10))):
            services._parse_score('X-X', 4)

    def test_parse_score__open_frame(self):
        assert services._parse_score('2-3', 5) == ['2', '3', 0]

    def test_parse_score__spare(self):
        assert services._parse_score('7/', 5) == ['7', 3, 0]

    def test_parse_score__strike(self):
        assert services._parse_score('X', 4) == ['X', 0, 0]

    def test_parse_score__all_strikes_last_attempt(self):
        assert services._parse_score('X-X-X', 10) == ['X', 'X', 'X']

    def test_parse_score__strikes_spare_last_attempt(self):
        assert services._parse_score('X-7/', 10) == ['X', '7', 3]

    def test_parse_score__strike_strike_open_last_attempt(self):
        assert services._parse_score('X-X-9', 10) == ['X', 'X', '9']

    def test_parse_score__strike_open_frame_last_attempt(self):
        assert services._parse_score('X-2-3', 10) == ['X', '2', '3']

    def test_parse_score__spare__last_attempt(self):
        assert services._parse_score('7/4', 10) == ['7', 3, '4']

    def test_parse_score__spare__strike_last_attempt(self):
        assert services._parse_score('7/X', 10) == ['7', 3, 'X']


class FrameScoreTest(test.TestCase):
    """Encapsulates all tests associated with frame score."""

    def setUp(self):
        self.game_registration = game_models.GameRegistration.objects.create()
        self.queryset = game_models.ScorePerFrame.objects.select_related('game')

    def test_game_id_not_found(self):
        score_object = services.get_frame_score(self.queryset, 'abcde12345')
        game_object = game_models.Game('abcde12345')
        game_object.errors = [
            game_models.Error(
                error_code=404,
                error_message='No game was found for the game id: abcde12345.')]
        assert score_object == game_object

    def test_calculate_score_for_active_game(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 96)

    def test_calculate_score_for_completed_game(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', '7/3']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 168)

    def test_calculate_score_for_completed_game_2(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', 'X-X-9']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 187)

    def test_calculate_score_for_completed_game_3(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', '7/X']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 175)

    def test_calculate_score_for_completed_game_4(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', 'X-4-9']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 181)

    def test_calculate_score_for_completed_game_5(self):
        scores = ['X', '7/', '7-2', '9/', 'X', 'X', 'X', '2-3', '6/', 'X-4/']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 178)

    def test_calculate_score_for_all_strikes_open_frame(self):
        scores = ['X', 'X', '7-2', 'X', 'X', 'X', 'X', 'X', 'X', 'X-X-X']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 265)

    def test_calculate_score_for_all_strikes_spare(self):
        scores = ['X', 'X', '7/', 'X', 'X', 'X', 'X', 'X', 'X', 'X-X-X']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 277)

    def test_calculate_score_for_all_strikes(self):
        scores = ['X', 'X', 'X', 'X', 'X', 'X', 'X', 'X', 'X', 'X-X-X']
        for score in scores:
            services.set_frame_score(
                self.queryset, self.game_registration.game_id, score)
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(
            self.game_registration.game_id, 300)

    def test_calculate_score_for_new_game(self):
        game_object = services.get_frame_score(
            self.queryset, self.game_registration.game_id)
        assert game_object == game_models.Game(self.game_registration.game_id)
