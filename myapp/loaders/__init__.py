from abc import ABC, abstractmethod
from typing import Iterable, Tuple

from myapp.models import URN, ActiveLink, Wbs, WorkItem, WorkVolume


class BimModelLoader(ABC):
    @abstractmethod
    def load(self, project: ActiveLink, spec: Wbs, model: URN) -> Iterable[Tuple[WorkItem, WorkVolume]]:
        pass
