import urllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from django.db import models
from django.urls import reverse


class URN(models.Model):
    type = models.CharField(max_length=30)
    urn = models.CharField(max_length=200)
    userId = models.IntegerField()
    isActive = models.BooleanField()

    def is_ifc(self):
        parts = urllib.parse.urlparse(self.urn)
        file = unquote(Path(parts.path).name)
        return "urn:" not in self.urn or (file and file.endswith(".ifc"))


class Rule(models.Model):
    name = models.CharField(max_length=99, blank=True)
    names = models.CharField(max_length=999, blank=True)
    fields = models.CharField(max_length=999, blank=True)
    unique_name = models.CharField(max_length=100, blank=True)
    filters = models.CharField(max_length=999, blank=True)
    group_by = models.CharField(max_length=999, blank=True)
    sum_by = models.CharField(max_length=999, blank=True)
    operations = models.CharField(max_length=9999, blank=True)
    userId = models.IntegerField()
    isActive = models.BooleanField()

    def get_absolute_url(self):  # Тут мы создали новый метод
        return reverse("rule_edit", args=[str(self.id)])


class ActiveLink(models.Model):
    userId = models.CharField(max_length=200)
    projectId = models.CharField(max_length=200)
    modelId = models.CharField(max_length=200)


class Wbs(models.Model):
    wbs_code = models.CharField(max_length=30)
    docsdiv = models.CharField(max_length=10)
    wbs1 = models.CharField(max_length=10)
    wbs2 = models.CharField(max_length=100)
    wbs3 = models.CharField(max_length=100)
    specs = models.JSONField()
    userId = models.IntegerField()
    isActive = models.BooleanField()

    def get_absolute_url(self):  # Тут мы создали новый метод
        return reverse("wbs_edit", args=[str(self.id)])


class Task(models.Model):
    my_id = models.BigAutoField(primary_key=True, editable=False)
    id = models.CharField(blank=True, max_length=100)
    text = models.CharField(blank=True, max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True)
    duration = models.IntegerField(blank=True)
    progress = models.FloatField(blank=True)
    parent = models.CharField(blank=True, max_length=100)
    type = models.CharField(blank=True, max_length=100)
    hype = models.CharField(blank=True, max_length=100)


class Task2(models.Model):
    my_id = models.BigAutoField(primary_key=True, editable=False)
    id = models.CharField(blank=True, max_length=100)
    text = models.CharField(blank=True, max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    progress = models.FloatField(null=True, blank=True)
    parent = models.CharField(null=True, blank=True, max_length=100)
    type = models.CharField(null=True, blank=True, max_length=100)


class Link(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    source = models.CharField(max_length=100)
    target = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    lag = models.IntegerField(blank=True, default=0)


@dataclass(frozen=True)
class Storey:
    name: str
    description: Optional[str]
    value: Optional[int] = field(init=False)

    def __post_init__(self):
        level = self.name
        if level and level.startswith("L"):
            if level.startswith("L-"):
                basement = True
                level = level[2:]
            else:
                level = level[1:]
            while level and level.startswith("0"):
                level = level[1:]
            self.value = int(level) * (-1 if basement else 1)
        else:
            self.value = None

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        if self.value is None or other.value is None:
            return self.name < other.name
        return self.value < other.value


@dataclass(frozen=True, order=True, eq=True)
class WorkItem:
    work_type: str
    building: str
    storey: Optional[Storey]
    din: str
    name: str


@dataclass(frozen=True)
class WorkVolume:
    count: int
    value: float

    def __add__(self, other):
        return WorkVolume(
            self.count + other.count,
            other.value if self.value is None else self.value + other.value if other.value is not None else self.value,
        )
