from rest_framework.urlpatterns import format_suffix_patterns
from django.conf.urls import url
from game import viewset

urlpatterns = format_suffix_patterns([
    url(r'^game/register$',
        viewset.BowlingViewSet.as_view({'post': 'register_game'}),
        name='register-game'),
    url(r'^game/(?P<game_id>[A-Za-z0-9\-]+)/score/(?P<score>X-X-X|X-X-[0-9]|X-[0-9]/|X-[0-9]-[0-9]|X{1}|[0-9]/X|[0-9]/[0-9]|[0-9]/|[0-9]-[0-9])$',      # NOQA: E501
        viewset.ScoreViewSet.as_view({'post': 'set_score'}), name='play-game'),
    url(r'^game/(?P<game_id>[A-Za-z0-9\-]+)/score$',
        viewset.ScoreViewSet.as_view({'get': 'get_score'}), name='get-score')
])
