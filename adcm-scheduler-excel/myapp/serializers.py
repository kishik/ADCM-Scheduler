from rest_framework import serializers

from .models import Link, Task, Task2


class TaskSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    end_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    class Meta:
        model = Task2
        fields = ("id", "text", "start_date", "end_date", "duration", "progress", "parent")


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = ("id", "source", "target", "type", "lag")
