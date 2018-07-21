"""Encapsulates all exceptions raised by bowling game."""


class ScoringException(Exception):
    """Base class for all scoring exceptions."""


class MissingScoreException(ScoringException):
    def __init__(self, frame):
        super(MissingScoreException, self).__init__(
            'Scoring is not available for frame: {}.'.format(frame))


class InvalidScoreLengthForFrame(ScoringException):
    """Every frame should have
       1. in case of a strike, a minimum of 1 attemptfor all frames except
          the last frame in which case it will have 3 attempts.
       2. in case of a spare, a minimum of 2 attemptfor all frames except
          the last frame in which case it will have 3 attempts.
       3. exactly 2 attempts for all frames in case of an open frame.
    """
    def __init__(self, score_type, score, frame):
        super(InvalidScoreLengthForFrame, self).__init__(
            ('{type} {score} has incorrect number of tries for '
             'frame: {frame}.'.format(type=score_type, score=score,
                                      frame=frame)))
