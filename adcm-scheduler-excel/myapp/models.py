import urllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from django.db import models
from django.urls import reverse
    

class Project(models.Model):
    name = models.TextField(max_length=99, blank=True)
    link = models.CharField(max_length=200)
    userId = models.IntegerField()
    isActive = models.BooleanField()


class ActiveLink(models.Model):
    userId = models.CharField(max_length=200)
    projectId = models.CharField(max_length=200)
    modelId = models.CharField(max_length=200)


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
    value: Optional[int] = field(init=False, default=None)

    def __post_init__(self):
        level = self.name
        if level and level.startswith("L"):
            basement = False
            if level.startswith("L-"):
                basement = True
                level = level[2:]
            else:
                level = level[1:]
            while level and level.startswith("0"):
                level = level[1:]
            object.__setattr__(self, "value", int(level) * (-1 if basement else 1))


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
