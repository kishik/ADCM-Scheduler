import urllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django_celery_results.models import TaskResult


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
    name = models.TextField(max_length=99, blank=True)
    names = models.TextField(max_length=999, blank=True)
    fields = models.TextField(max_length=999, blank=True)
    unique_name = models.TextField(max_length=100, blank=True)
    filters = models.TextField(max_length=999, blank=True)
    group_by = models.TextField(max_length=999, blank=True)
    sum_by = models.TextField(max_length=999, blank=True)
    operations = models.TextField(max_length=9999, blank=True)
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

    # name = models.CharField(max_length=255, null=True)

    # yield (
    #     WorkItem(
    #         work_type=attrs.get("ADCM_RD"),
    #         building=attrs.get("ADCM_Title"),
    #         storey=Storey(level, description=storey),
    #         din=attrs.get("ADCM_DIN"),
    #         name=n.get("group_type"),
    #     ),


class EditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_updated_by")
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, related_name="%(app_label)s_%(class)s_deleted_by"
    )

    def is_active(self):
        return self.deleted_at is None

    class Meta:
        abstract = True


class Project(EditableModel):
    name = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    users = models.ManyToManyField(User, blank=True, related_name="projects")

    def __str__(self):
        return self.name


class Job(models.Model):
    class JobType(models.TextChoices):
        LOAD = "LOAD", "Load models"
        PLAN = "PLAN", "Generate plan"

    created_at = models.DateTimeField(auto_now_add=True)
    task_id = models.CharField(max_length=191, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="jobs")
    task_type = models.CharField(max_length=10, choices=JobType.choices)

    def tasks(self):
        return TaskResult.objects.filter(task_id=self.task_id)


class JobItem(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="work_items")
    model = models.ForeignKey(URN, on_delete=models.CASCADE, related_name="work_items")
    group_0 = models.CharField(max_length=100)
    group_1 = models.CharField(max_length=100, null=True)
    group_2 = models.CharField(max_length=100, null=True)
    group_3 = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=255, null=True)
    count = models.IntegerField(default=1)
    volume = models.FloatField(null=True)


class ModelGroup(EditableModel):
    name = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="model_groups")

    def __str__(self):
        return self.name


class AutodeskExtractorRule(EditableModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    model_group = models.ForeignKey(ModelGroup, on_delete=models.CASCADE, related_name="extractor_rules")
    name = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    group_0 = models.CharField(max_length=100, null=True)
    group_1 = models.CharField(max_length=100, null=True)
    group_2 = models.CharField(max_length=100, null=True)
    group_3 = models.CharField(max_length=100, null=True)
    spec = models.CharField(max_length=200)


class BimModel(EditableModel):
    class ModelType(models.TextChoices):
        REVIT = "REVIT", "Revit"
        IFC = "IFC", "IFC"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="bim_models")
    model_group = models.ForeignKey(ModelGroup, on_delete=models.CASCADE, related_name="bim_models")
    name = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    uri = models.CharField(max_length=1000)
    model_type = models.CharField(max_length=10, choices=ModelType.choices)

    def __str__(self):
        return f"{self.name}[{self.model_type}]"
