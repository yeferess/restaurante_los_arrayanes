from django.urls import re_path

from apps.menu.consumers import MenuConsumer

websocket_urlpatterns = [
    re_path(r"^ws/menu/$", MenuConsumer.as_asgi()),
]
