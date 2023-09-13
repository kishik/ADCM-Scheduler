import json
from typing import Iterable, Tuple

import jmespath
import requests

from myapp.loaders import BimModelLoader
from myapp.models import URN, ActiveLink, Storey, Wbs, WorkItem, WorkVolume


class RevitLoader(BimModelLoader):
    def load(self, project: ActiveLink, spec: Wbs, model: URN) -> Iterable[Tuple[WorkItem, WorkVolume]]:
        """Load data from Revit model"""
        for selection in spec.specs:
            path = "/".join([selection, "project", project.projectId, "model", model.urn])
            data = requests.get(f"http://4d-model.acceleration.ru:8000/acc/get_spec/{path}").json()
            if isinstance(data, str):
                data = json.loads(data)

            mapping = f"""
                data[*].{{
                work_type: '{model.type}',
                building: wbs2,
                level_name: wbs3_id,
                din: wbs3,
                value: value,
                name: name
                }}
            """

            for record in jmespath.search(mapping, data):
                item = WorkItem(
                    work_type=record["work_type"],
                    building=record["building"],
                    storey=Storey(record["level_name"]),
                    din=record["din"],
                    name=record["name"],
                )
                volume = WorkVolume(count=1, volume=record["value"])

                yield item, volume
