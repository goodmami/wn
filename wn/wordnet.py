
from typing import List

from wn._api import synsets
from wn._models import Synset


class WordNet:
    """
    Class for interacting with WordNet data.
    """

    def __init__(self, project: str = None, version: str = None):
        self.project = project
        self.version = version

    def synsets(self,
                form: str = None,
                id: str = None,
                ili: str = None,
                pos: str = None) -> List[Synset]:
        return synsets(form=form,
                       id=id,
                       ili=ili,
                       pos=pos,
                       project=self.project)
