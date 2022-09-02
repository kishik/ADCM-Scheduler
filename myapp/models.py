from django.db import models
from django.db.models import signals
# Create your models here.
from datetime import datetime
from django_neomodel import DjangoNode
from neomodel import StructuredNode, StringProperty, DateTimeProperty, UniqueIdProperty, RelationshipFrom, \
    RelationshipTo


class Work(DjangoNode):
    id = StringProperty(unique_index=True)
    name = StringProperty()
    incoming = RelationshipFrom('Work', 'WORK')
    outcoming = RelationshipFrom('Work', 'WORK')
    isActive = models.BooleanField()

    class Meta:
        app_label = 'myapp'


class URN(models.Model):
    type = models.CharField(max_length=30)
    urn = models.CharField(max_length=200)
    userId = models.IntegerField()
    isActive = models.BooleanField()


class Rule(models.Model):
    name = models.CharField(max_length=30)
    rule = models.CharField(max_length=9999)
    userId = models.IntegerField()
    isActive = models.BooleanField()


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
    specs = models.CharField(max_length=200)
    userId = models.IntegerField()
    isActive = models.BooleanField()
