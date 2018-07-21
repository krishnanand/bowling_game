"""Encapsulates all instances of model serialisers."""
from rest_framework import serializers

from game import models

import collections


class BaseSerializer(serializers.Serializer, object):

    def to_representation(self, instance):
        """Return just errors if applicable, and exclude errors otherwise."""
        ret = super(BaseSerializer, self).to_representation(instance)
        # If error exists, then all fields should be removed.
        if 'errors' in ret and ret.get('errors'):
            return collections.OrderedDict(errors=ret['errors'])

        return collections.OrderedDict((k, v) for k, v in ret.items()
                                       if k != 'errors')


class ErrorSerializer(serializers.Serializer):
    """Representation of any errors."""
    error_code = serializers.IntegerField()
    error_message = serializers.CharField(max_length=200)


class GameRegistrationSerializer(BaseSerializer, serializers.ModelSerializer):
    """Serializer representation of game instance."""
    created = serializers.DateTimeField(source='created_timestamp',
                                        read_only=True)
    errors = ErrorSerializer(required=False, many=True, read_only=True)

    class Meta:
        model = models.GameRegistration
        fields = ('game_id', 'created', 'errors')
        read_only_fields = ('game_id', 'created', 'errors')


class ScorePerFrameSerializer(BaseSerializer, serializers.ModelSerializer):
    errors = ErrorSerializer(required=False, many=True)

    class Meta:
        model = models.ScorePerFrame
        fields = ('game', 'frame', 'frame_score', 'errors',
                  'total_score_for_frame')
        read_only_fields = ('frame_score', 'game', 'frame', 'errors',
                            'total_score_for_frame')


class ScoreSerializer(BaseSerializer):
    """Encapsulates the scores per frame and the total score."""
    total_score = serializers.IntegerField(required=True)
    game_id = serializers.CharField(max_length=16, min_length=16)
    errors = ErrorSerializer(required=False, many=True)
