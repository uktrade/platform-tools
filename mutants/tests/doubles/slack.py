from unittest.mock import Mock


class WebClient:
    def __init__(self, token: str):
        self.token = token
        self.chat_update = Mock(return_value={"ts": "updated-message"})
        self.chat_postMessage = Mock(return_value={"ts": "first-message"})
