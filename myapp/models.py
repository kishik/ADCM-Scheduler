from django.db import models
from django.db.models import signals
# Create your models here.
from datetime import datetime
from django_neomodel import DjangoNode
from neomodel import StructuredNode, StringProperty, DateTimeProperty, UniqueIdProperty, RelationshipFrom, RelationshipTo


class Work(DjangoNode):
    id = StringProperty(unique_index=True)
    name = StringProperty()
    incoming = RelationshipFrom('Work', 'WORK')
    outcoming = RelationshipFrom('Work', 'WORK')

    class Meta:
        app_label = 'myapp'


class URN(models.Model):
    name = models.CharField(max_length=30)
    urn = models.CharField(max_length=200)


# def your_signal_func(sender, instance, signal, created):
#     pass
#
#
# signals.post_save.connect(your_signal_func, sender=Work)
