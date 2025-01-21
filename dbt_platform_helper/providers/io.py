from typing import Callable


class IOProvider:
    def __init__(
        self, warn: Callable[[str], str], error: Callable[[str], str], prompt: Callable[[str], bool]
    ):
        self.warn = warn
        self.error = error
        self.prompt = prompt
