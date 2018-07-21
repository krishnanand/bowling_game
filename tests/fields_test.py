"""Unit tests for fields."""
from game import fields

from django.core import exceptions

import pytest


def test_validate_score_zero():
    fields.validate_score('0') is None


def test_validate_score_ten():
    fields.validate_score('10') is None


def test_validate_score__negative_number():
    with pytest.raises(
            exceptions.ValidationError,
            match=('The bowling score -1 is invalid. '
                   'The score must be between 0 and 10.')):
        fields.validate_score('-1')


def test_validate_score__out_of_range_number():
    with pytest.raises(
            exceptions.ValidationError,
            match=('The bowling score 15 is invalid. '
                   'The score must be between 0 and 10.')):
        fields.validate_score('15')


def test_validate_score__XX():
    with pytest.raises(
            exceptions.ValidationError,
            match='The value must be between 0 and 10 or \'X\'.'):
        fields.validate_score('XX')


def test_validate_score__X():
    fields.validate_score('X') is None
