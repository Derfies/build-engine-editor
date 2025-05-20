import json
import logging

from applicationframework.contentbase import ContentBase
from gameengines.build.duke3d import MapReader as Duke3dMapReader

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class Content(ContentBase):

    def __init__(self):
        self.map = None

    def load(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.map = Duke3dMapReader()(f)

    def save(self, file_path: str):
        raise NotImplementedError()
