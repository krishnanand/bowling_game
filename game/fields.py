"""Encapsulates the all custom fields associated with the bowling game."""

from django.core import exceptions
from django.db import models
from django.utils.translation import gettext_lazy as _


def validate_score(value):
    try:
        if value != 'X':
            value = int(value)
            if value < 0 or value > 10:
                raise exceptions.ValidationError(
                    ('The bowling score %(value)s is invalid. '
                     'The score must be between 0 and 10.' % {'value': value}))
    except ValueError:
        raise exceptions.ValidationError(
            'The value must be between 0 and 10 or \'X\'.')


class BowlingScoreField(models.CharField):
    """Encapsulates a bowling score for any given attempt."""
    description = _('The score for an attempt in a frame.')
    empty_strings_allowed = False

    default_validators = [validate_score]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 2
        super(BowlingScoreField, self).__init__(*args, **kwargs)
