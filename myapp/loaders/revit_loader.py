import json
from typing import Iterable, Tuple, List

import jmespath
import requests

from myapp.loaders import BimModelLoader
from myapp.models import URN, ActiveLink, Storey, Wbs, WorkItem, WorkVolume, Job, AutodeskExtractorRule


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


def load_revit(model: URN, job: Job, rule: AutodeskExtractorRule) -> List[WorkItem]:
    path = "/".join([rule.spec, "project", model.project.external_project.external_id, "model", model.uri])
    data = requests.get(f"http://4d-model.acceleration.ru:8000/acc/get_spec/{path}").json()
    if isinstance(data, str):
        data = json.loads(data)

    mapping = f"""
        data[*].{{ 
           group_0: {rule.group_0 or model.model_group.name},
           group_1: {rule.group_1},
           group_2: {rule.group_2},
           group_3: {rule.group_3}
           volume: value,
           name: name
        }}
    """

    yield from map(
        lambda item: WorkItem.objects.create(
            job=job,
            bim_model=model,
            group_0=item["group_0"],
            group_1=item.get("group_1"),
            group_2=item.get("group_2"),
            group_3=item.get("group_3"),
            name=item.get("name"),
            count=1,
            volume=item.get("volume"),
        ).id,
        jmespath.search(mapping, data)
    )
