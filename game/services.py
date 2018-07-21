"""Module that encapsulates all service functions.
"""
import logging
import re
from django.db import DatabaseError
from django.db import models as django_models
from django.db import transaction

from game import exceptions
from game import models as game_models


SCORING_TYPE_STRIKE = 'strike'
SCORING_TYPE_SPARE = 'spare'
SCORING_TYPE_OPEN = 'open'


def register_game():
    """Registers the game and returns the game instance."""
    try:
        with transaction.atomic(savepoint=False):
            game_object = game_models.GameRegistration()
            game_object.save()
            return game_object
    except DatabaseError:
        logging.exception('Unable to register the game')
        game_object = game_models.GameRegistration()
        game_object.add_error(
            game_models.Error(
                error_code=500, error_message='Unable to register the game.'))
        return game_object


def set_frame_score(score_queryset, game_id, score):
    """Sets the frame score for a valid game.

    The implementation executes the following:

    1. load the game object associated with game id; if the game does not exist
    then raise a 404 error.

    2. fetch the number of frames that have been played so far. If the number of
    frames played equals "10", i.e. the game is over, then a 400 error is raised

    3. If the score format is valid, then and no frames have been played, then
       a frame is created and the score calculated.
    """
    try:
        with transaction.atomic(savepoint=False):
            # If the game has not been created, then return a 404.
            game_object, game_object_created = _get_game_object(
                game_id, game_models.ScorePerFrame)
            if not game_object_created:
                # Error object is returned
                return game_object

            if not _is_valid_score(score):
                frame_score = game_models.ScorePerFrame()
                frame_score.add_error(game_models.Error(
                    error_code=400,
                    error_message='Score format: {} is invalid.'.format(score)))
                return frame_score

            spf_qs = score_queryset.filter(game=game_object)
            if not spf_qs or len(spf_qs) == 0:
                # First frame.

                (first_score, second_score,
                 third_score) = _parse_score(score, 1)
                bowling_frame = game_object.game_score.create(
                    frame=1,
                    first_attempt_score=first_score,
                    second_attempt_score=second_score,
                    third_attempt_score=third_score,
                    frame_version=1)
                return bowling_frame

            # If the game has been completed, then return a 400.
            number_of_played_frames = spf_qs.aggregate(
                django_models.Max('frame')).get('frame__max', 0)

            if number_of_played_frames == 10:
                frame_score = game_models.ScorePerFrame()
                frame_score.add_error(game_models.Error(
                    error_code=400,
                    error_message='Game:\'{}\' has already been played.'.format(
                        game_id)))
                return frame_score

            # Parse the score, and check if the version has been created.
            (first_score, second_score,
             third_score) = _parse_score(score, number_of_played_frames + 1)
            version_number_tuple = spf_qs.filter(game=game_object).filter(
                frame=number_of_played_frames + 1).values_list(
                'frame_version').first()
            (version_number, ) = (
                version_number_tuple
                if version_number_tuple is not None else (0, ))
            # Update the frame by to indicate a new frame is being played.
            score_per_frame = game_object.game_score.create(
                first_attempt_score=first_score,
                second_attempt_score=second_score,
                third_attempt_score=third_score,
                frame=number_of_played_frames + 1,
                frame_version=version_number + 1)
            return score_per_frame
    except:
        logging.exception(
            ('Unable to save the frame for score {}'
             ' and game:{}.'.format(score, game_id)))
        frame_score = game_models.ScorePerFrame()
        frame_score.add_error(game_models.Error(
            error_code=500,
            error_message=('Unable to save score: \'{score}\' for game: '
                           '\'{game}\'.'.format(game=game_id, score=score))))
        return frame_score


def get_frame_score(queryset, game_id):
    """Gets the scores of the all the frames in addition to the total score."""
    with transaction.atomic(savepoint=False):
        game_object, is_returned = _get_game_object(game_id, game_models.Game)
        game_object.game_id = game_id
        if not is_returned:
            return game_object
        spf_qs = queryset.filter(game=game_object).order_by('frame')
        # If number of played frames = 10, that means the game has been
        # completed. In that event,
        total_score = None
        for score in reversed(spf_qs):
            if total_score is None and score.total_score_for_frame is not None:
                total_score = score.total_score_for_frame
        return game_models.Game(game_id, total_score)


def _get_game_object(game_id, clazz_instance):
    """Returns the game object by game id.

    Returns:
        a tuple of game object and boolean flag indicating that the game object
        was created or not
    """
    try:
        with transaction.atomic(savepoint=False):
            game_object = game_models.GameRegistration.objects.get(pk=game_id)
            return game_object, True
    except game_models.GameRegistration.DoesNotExist:
        logging.error('No game was found for game id : {}'.format(game_id))
        clazz_object = clazz_instance()
        clazz_object.add_error(game_models.Error(
            error_code=404,
            error_message='No game was found for the game id: {}.'.format(
                game_id)))
        return clazz_object, False


def _is_valid_score(score):
    """Validates the string representation of the score.

    The acceptable formats is given below:

    1. X-X-X (three strikes in the last frame)

    2. X-X-<0-9> (two strikes and open frame in the last frame)

    3. X-<0-9>/ (strike and a spare in the last frame)

    4. X-<0-9>-<0-9> (strike and two open scores in the last frame)

    5. X (strike for any frame except the last frame)

    6. <0-9>/X (spare and a stike in the last last frame)

    7. <0-9>/<0-9> (spare and an additional try in the last frame)

    8. <0-9>/ (spare for any frame except the last frame)

    9. <0-9>-<0-9> for a open frame.
    """
    p = re.compile(('^(X-X-X|X-X-[0-9]|X-[0-9]/|X-[0-9]-[0-9]|X{1}|[0-9]/X|'
                    '[0-9]/[0-9]|[0-9]/|[0-9]-[0-9])$'))
    return True if p.match(score) else False


def _handle_strike(arr, score, number_of_played_frames):
    """Handles the scenario in which the bowling attempt is a strike.

    If any frame except the last one contains a strike, then there are no second
    and third attempts for the frame. In this case, values of the second and
    third attempts are equal to 0.

    Args:
       arr: array; array of scores
       score: string; representation of the bowling score
       number_of_played_frames: integer; number of played frames

    Returns:
       the array representing the values of 3 frames.
    """
    if ((number_of_played_frames == 10 and (len(arr) < 2 or len(arr) > 3)) or
        (number_of_played_frames < 10 and len(arr) != 1)):
            raise exceptions.InvalidScoreLengthForFrame(
                SCORING_TYPE_STRIKE, score, number_of_played_frames)
    if number_of_played_frames < 10 and len(arr) == 1:
        arr.extend([0, 0])
    # Strike in last frame followed by a spare
    elif number_of_played_frames == 10:
        if len(arr) == 2 and '/' in arr[1]:
            arr[1] = arr[1].split('/')[0]
            arr.extend([10 - int(arr[1])])
        elif len(arr) == 2:
            raise exceptions.InvalidScoreLengthForFrame(
                SCORING_TYPE_SPARE, score, number_of_played_frames)
    return arr


def _handle_spare(arr, score, number_of_played_frames):
    """
    If any frame except the last one contains a strike, then there are no third
    attempts for the frame. In this case, values of the third attempt is and
    considered to be 0. The value of the second attempt is the difference
    between "10" and first attempt score.

    Args:
        arr: array; array of scores
        score: string; representation of the bowling score
        number_of_played_frames: integer; number of played frames

    Returns:
        the array representing the values of 3 frames.
    """
    if number_of_played_frames == 10 and len(arr) == 2:
        if (arr[0] == 'X' and arr[1]) or (arr[0] != 'X' and not arr[1]):
            raise exceptions.InvalidScoreLengthForFrame(
                SCORING_TYPE_SPARE, score, number_of_played_frames)
        if arr[0] == 'X' and not arr[1]:
            # Last frame is a strike followed by a spare.
            arr[1] = 10
            arr.extend([0])
        elif arr[0] != 'X' and arr[1]:
            arr.insert(1, 10 - int(arr[0]))
        return arr
    elif len(arr) == 2:
        # For the last frame, if the attempt is a split, then an additional
        # attempt is required. (7/4)
        if not arr[1]:
            arr[1] = 10 - int(arr[0])
            arr.extend([0])
            return arr


def _parse_score(score, number_of_played_frames):
    """Parses the score and returns separate frame scores.

    The implementation returns an iterable of 3 elements representing the scores
    of maximum three attempts.

    If a strike was scored in last frame, then the iterable would consist
    of 'X', and the scores from the next two attempts.

    If a spare was scored in last frame, then the iterable would consist
    of spare strike and an additional attempt.
    """
    if not score:
        raise exceptions.MissingScoreException(number_of_played_frames)

    arr = score.split('-')
    # Check if a strike or an open frame.
    if arr[0] == 'X':
        return _handle_strike(arr, score, number_of_played_frames)
    elif len(arr) == 2:
        arr.extend([0])
        return arr

    arr = score.split('/')
    # If the split score is "7/", then the attempts per score are given as
    # [7, 3].
    return _handle_spare(arr, score, number_of_played_frames)
