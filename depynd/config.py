import pathlib
from dataclasses import dataclass


@dataclass
class Config():
    cache_directory: str = './cache'

    def prepare(self):
        pathlib.Path(self.cache_directory).mkdir(parents=True, exist_ok=True)


config = Config()
