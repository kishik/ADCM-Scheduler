import logging
from typing import Dict, Iterable

from myapp.loaders import BimModelLoader
from myapp.loaders.ifc_loader import IFCLoader
from myapp.loaders.revit_loader import RevitLoader
from myapp.models import URN, ActiveLink, Wbs, WorkItem, WorkVolume


logger = logging.getLogger(__name__)


class WorkAggregator:
    def __init__(self, project: ActiveLink, specs: Iterable[Wbs]) -> None:
        self.project = project
        self.specs = specs
        self._data = {}

    def loader(self, model: URN) -> BimModelLoader:
        return IFCLoader() if model.is_ifc() else RevitLoader()

    def load_models(self) -> None:
        for spec in self.specs:
            models = URN.objects.filter(type=spec.docsdiv)
            for model in models:
                try:
                    for item, volume in self.loader(model).load(self.project, spec, model):
                        self._data[item] = self._data.setdefault(item, WorkVolume(0, None)) + volume
                except Exception as e:
                    logger.exception(e)
        return self._data

    def get_data(self) -> Dict[WorkItem, WorkVolume]:
        return self._data
