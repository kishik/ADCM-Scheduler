from django.contrib import admin as dj_admin
from django_neomodel import admin as neo_admin
from .models import Work, ActiveLink, URN


class WorkAdmin(dj_admin.ModelAdmin):
    list_display = ("id", "name")


neo_admin.register(Work, WorkAdmin)
dj_admin.site.register(ActiveLink)
dj_admin.site.register(URN)
