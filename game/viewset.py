"""
Encapsulates all the view sets required to play the bowling game.
"""

from game import models
from game import serializers
from game import services as bowling_services

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets


def serialized_object(serializer_class, obj, http_status):
    serialized_instance = serializer_class(obj)
    return Response(serialized_instance.data, status=http_status)


class BowlingViewSet(viewsets.ModelViewSet):
    queryset = models.GameRegistration.objects.all()
    serializer_class = serializers.GameRegistrationSerializer

    @action(detail=True)
    def register_game(self, request, *args, **kwargs):
        """Registers the game."""
        game_object = bowling_services.register_game()
        return serialized_object(self.get_serializer_class(), game_object,
                                 status.HTTP_201_CREATED)


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = models.ScorePerFrame.objects.select_related('game')

    def get_serializer_class(self):
        if self.action == 'get_score':
            return serializers.ScoreSerializer
        else:
            return serializers.ScorePerFrameSerializer

    @action(detail=True)
    def set_score(self, request, game_id, score):
        """Sets the score of the given frame."""
        response = bowling_services.set_frame_score(
            self.get_queryset(), game_id, score)
        return serialized_object(self.get_serializer_class(), response,
                                 status.HTTP_200_OK)

    @action(detail=True)
    def get_score(self, request, game_id):
        """Returns the total score by the latest frame."""
        response = bowling_services.get_frame_score(
            self.get_queryset(), game_id)
        clazz = self.get_serializer_class()
        serializer_instance = clazz(response)
        return Response(serializer_instance.data, status=status.HTTP_200_OK)
