from django.db import models
from django.core import validators
from django.utils import timezone

from game import fields as game_fields

import functools
import random


def random_string(char_length):
    """Generates a random string of a specified character length."""
    allowed_chars = ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                     '0123456789')
    return ''.join([random.choice(allowed_chars) for i in range(char_length)])


class ErrorModel(object):
    errors = []

    def add_error(self, error_object):
        """Appends the error to the list of errors."""
        self.errors.append(error_object)


class BaseModel(models.Model, object):
    # Encapsulates all error objects.

    class Meta:
        abstract = True
        app_label = 'game'


class GameRegistration(BaseModel, ErrorModel):
    """Instance of this class represents the user playing the bowling game."""

    def __init__(self, * args, **kwargs):
        super(GameRegistration, self).__init__(*args, **kwargs)
        self.errors = []

    game_id = models.CharField(
        max_length=16, help_text='Unique bowling game id', primary_key=True,
        default=functools.partial(random_string, char_length=16),
        validators=[validators.MinLengthValidator(16)])
    created_timestamp = models.DateTimeField(default=timezone.now)

    def __repr__(self):
        return '{}:{}'.format(self.__class__.__name__, self.__dict__)

    class Meta:
        indexes = [
            models.Index(fields=['game_id'])
        ]


class ScorePerFrame(BaseModel, ErrorModel):
    score_per_frame_id = models.AutoField(primary_key=True)
    game = models.ForeignKey(
        GameRegistration, on_delete=models.CASCADE, related_name='game_score')
    frame = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(10)])
    first_attempt_score = game_fields.BowlingScoreField(
        verbose_name='Score for the first attempt.',
        help_text='Score in the first attempt.')
    second_attempt_score = game_fields.BowlingScoreField(
        verbose_name='Score for the first attempt.',
        help_text='Score in the second attempt.')
    # In case of last attempt.
    third_attempt_score = game_fields.BowlingScoreField(
        verbose_name='Score for the first attempt.',
        help_text='Score in the 3rd attempt. This applies only to 10th frame.')
    # Total score.
    frame_score = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(30)],
        help_text='Current for the given frame.', null=True)
    frame_version = models.PositiveIntegerField(
        validators=[validators.MinValueValidator(1)])
    total_score_for_frame = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(300)],
        help_text='Total score till this frame.', null=True)

    def __init__(self, * args, **kwargs):
        super(ScorePerFrame, self).__init__(*args, **kwargs)
        self.errors = []

    def queryset_by_game(self):
        return ScorePerFrame.objects.filter(game=self.game)

    def get_previous_frame(self, frame):
        """Returns the previous frame."""
        return self.queryset_by_game().filter(frame__lt=frame).order_by(
            '-frame').first()

    @property
    def is_spare(self):
        return ((self._get_score(self.first_attempt_score) +
                 self._get_score(self.second_attempt_score)) == 10)

    @property
    def is_strike(self):
        return self.first_attempt_score == 'X'

    def _get_score(self, score):
        score_dict = {
            'X': 10
        }
        val = score_dict.get(score)
        return val if val is not None else int(score)

    def _calculate_scores_for_open_frame(self, total, previous_score,
                                         prior_to_previous, prev):
        """Calculates the frame scores for an open frame.

        Args:
            total: score of the current frame
            previous_score: model score representing the last frame
            prior_to_previous: model score representing the penultimate frame
            prev: model score representing the frame prior to the penultimate
                 frame

        Returns:
            total score of the current frame
        """
        if self.frame == 1:
            self.total_score_for_frame = total
            return total
        # Current score
        if previous_score.is_strike:
            previous_score.frame_score = 10 + total
            # Just save the totals.
            # Check if the frame prior was a strike or not.
            if prior_to_previous and prior_to_previous.is_strike:
                prior_to_previous.frame_score = (
                    20 + self._get_score(self.first_attempt_score))
                if prior_to_previous.frame > 1:
                    prior_to_previous.total_score_for_frame = (
                        prev.total_score_for_frame +
                        prior_to_previous.frame_score)
                else:
                    prior_to_previous.total_score_for_frame = (
                        prior_to_previous.frame_score)
                prior_to_previous.save(recursive_save=False)
                previous_score.total_score_for_frame = (
                    prior_to_previous.total_score_for_frame +
                    previous_score.frame_score)
            previous_score.save(recursive_save=False)
        elif previous_score.is_spare:
            # Initialise the score of the previous entry, and then calculate the
            # frame score.
            previous_score.frame_score = (
                10 + self._get_score(self.first_attempt_score))
            if prior_to_previous:
                previous_score.total_score_for_frame = (
                    (prior_to_previous.total_score_for_frame or 0) +
                    previous_score.frame_score)
            previous_score.save(recursive_save=False)
        self.total_score_for_frame = (
            previous_score.total_score_for_frame + total)

    def _calculate_scores_for_strike(
            self, total, previous_score, prior_to_previous, prev):
        """Calculates the frame scores for an open frame.

        Args:
            total: score of the current frame
            previous_score: model score representing the last frame
            prior_to_previous: model score representing the penultimate frame
            prev: model score representing the frame prior to the penultimate
                 frame

        Returns:
            total score of the current frame
        """
        # No need to calculate the current frame's score. It will be calculated
        # recursively.
        if previous_score:
            if previous_score.is_strike:
                if prior_to_previous and prior_to_previous.is_strike:
                    prior_to_previous.frame_score = 30
                    if prior_to_previous.frame == 1:
                        prior_to_previous.total_score_for_frame = (
                            prior_to_previous.frame_score)
                    else:
                        prior_to_previous.total_score_for_frame = (
                            prev.total_score_for_frame +
                            prior_to_previous.frame_score)
                    prior_to_previous.save(recursive_save=False)
            elif previous_score.is_spare:
                previous_score.frame_score = 20
                if (prior_to_previous and
                    prior_to_previous.total_score_for_frame):
                        previous_score.total_score_for_frame = (
                            prior_to_previous.total_score_for_frame +
                            previous_score.frame_score)
            previous_score.save(recursive_save=False)
        if self.frame == 10:
            if (previous_score and previous_score.is_strike and
                previous_score.frame_score is None):
                    previous_score.frame_score = 10 + (
                        self._get_score(self.first_attempt_score) +
                        self._get_score(self.second_attempt_score))
                    previous_score.total_score_for_frame = (
                        previous_score.frame_score +
                        prior_to_previous.total_score_for_frame)
                    previous_score.save(recursive_save=False)
            self.total_score_for_frame = (
                previous_score.total_score_for_frame + total)

    def _calculate_scores_for_spare(
            self, total, previous_score, prior_to_previous, prev):
        """Calculates the frame scores for an open frame.

        Args:
            total: score of the current frame
            previous_score: model score representing the last frame
            prior_to_previous: model score representing the penultimate frame
            prev: model score representing the frame prior to the penultimate
                frame

        Returns:
            total score of the current frame
        """
        if previous_score:
            if previous_score.is_strike:
                previous_score.frame_score = 20
                if (prior_to_previous and prior_to_previous.is_strike and
                    prior_to_previous.frame_score is None):
                        prior_to_previous.frame_score = (
                            20 + self._get_score(self.first_attempt_score))
                        prior_to_previous.total_score_for_frame = (
                            (prev.total_score_for_frame if
                                prev else 0) +
                            prior_to_previous.frame_score)
                        prior_to_previous.save(recursive_save=False)
                previous_score.total_score_for_frame = (
                    (prior_to_previous.total_score_for_frame
                     if prior_to_previous is not None else 0) +
                    previous_score.frame_score)
            elif previous_score.is_spare:
                previous_score.frame_score = (
                    10 + self._get_score(self.first_attempt_score))
                if prior_to_previous:
                    previous_score.total_score_for_frame = (
                        prior_to_previous.total_score_for_frame +
                        previous_score.frame_score)
            previous_score.save(recursive_save=False)
        if self.frame == 10:
            # Last frame
            self.total_score_for_frame = (
                previous_score.total_score_for_frame + total)

    def calculate_frame_score(self):
        """
        Calculates the  score of the frame and  retroactively calculate the
        scores of the previous frames.
        """
        total = (self._get_score(self.first_attempt_score) +
                 self._get_score(self.second_attempt_score) +
                 self._get_score(self.third_attempt_score))
        previous_score = self.get_previous_frame(self.frame)
        prior_to_previous = (
            self.get_previous_frame(previous_score.frame)
            if previous_score else None)
        # one before penultimate
        prev = (
            self.get_previous_frame(prior_to_previous.frame)
            if prior_to_previous else None)
        # If the frame was open, then return the sum of the attempted scores.
        if total < 10:
            self._calculate_scores_for_open_frame(
                total, previous_score, prior_to_previous, prev)
            return total
        elif self.is_strike:
            self._calculate_scores_for_strike(
                total, previous_score, prior_to_previous, prev)
        elif self.is_spare:
            self._calculate_scores_for_spare(
                total, previous_score, prior_to_previous, prev)

        if self.frame == 10:
            return total

        # Assigning a temporary score in the mean time. This represents the
        # total score of all frames until now.
        if self.total_score_for_frame is None:
            if (previous_score and previous_score.total_score_for_frame and
                prior_to_previous and
                prior_to_previous.total_score_for_frame):  # NOQA: E129
                    self.total_score_for_frame = max(
                        previous_score.total_score_for_frame,
                        prior_to_previous.total_score_for_frame)
            elif (previous_score and
                  previous_score.total_score_for_frame is not None):
                self.total_score_for_frame = (
                    previous_score.total_score_for_frame)

    def save(self, *args, **kwargs):
        """Saves the score of the user's frame."""
        recursive_save = kwargs.pop('recursive_save', True)
        if recursive_save:
            self.frame_score = self.calculate_frame_score()
        super(ScorePerFrame, self).save(*args, **kwargs)

    def __repr__(self):
        return '{}:{}'.format(self.__class__.__name__, self.__dict__)

    class Meta:
        unique_together = ('frame', 'frame_version', 'game')
        indexes = [
            models.Index(fields=['frame']),
            models.Index(fields=['first_attempt_score']),
            models.Index(fields=['second_attempt_score']),
            models.Index(fields=['third_attempt_score'])]


class Game(ErrorModel):
    """Encapsulates all the frames in addition to the score."""

    def __init__(self, game_id=None, total_score=None):
        self.game_id = game_id
        self.total_score = total_score
        self.errors = []

    def __eq__(self, other):
        return (self.game_id == other.game_id and
                self.total_score == other.total_score and
                self.errors == other.errors)

    def __repr__(self):
        return '{}:{}'.format(self.__class__.__name__, self.__dict__)


class Error(object):
    """
    An instance of this class encapsulates the error code and the message to be
    returned.

    Attributes:
        error_code: HTTP error code representation
        error_message error message that represents the error
    """
    def __init__(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message

    def __eq__(self, other):
        return (self.error_code == other.error_code and
                self.error_message == other.error_message)

    def __repr__(self):
        return '{}:{}'.format(self.__class__.__name__, self.__dict__)
