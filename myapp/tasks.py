from celery import shared_task
from celery_progress.backend import ProgressRecorder
import time
import logging
from myapp.models import WorkVolume, URN

logger = logging.getLogger(__name__)


# @shared_task(bind=True)
# def my_task(self, seconds):
#     progress_recorder = ProgressRecorder(self)
#     i = 0
#     for spec in self.specs:
#         models = URN.objects.filter(type=spec.docsdiv)
#         for model in models:
#             try:
#                 for item, volume in self.loader(model).load(self.project, spec, model):
#                     self._data[item] = self._data.setdefault(item, WorkVolume(0, None)) + volume
#             except Exception as e:
#                 logger.exception(e)
#             progress_recorder.set_progress(i + 1, seconds)
#     return self._data


# @shared_task(bind=True)
# def loadmodels(self, agg) -> None:
#     progress_recorder = ProgressRecorder(self)
#     i = 0
#     for spec in agg.specs:
#         models = URN.objects.filter(type=spec.docsdiv)
#         for model in models:
#             try:
#                 for item, volume in agg.loader(model).load(agg.project, spec, model):
#                     agg._data[item] = agg._data.setdefault(item, WorkVolume(0, None)) + volume
#             except Exception as e:
#                 logger.exception(e)
#             progress_recorder.set_progress(i + 1, models.count())
#     return agg._data