from django.contrib import admin as dj_admin

from .models import URN, ActiveLink


class WorkAdmin(dj_admin.ModelAdmin):
    list_display = ("id", "name")


dj_admin.site.register(ActiveLink)
dj_admin.site.register(URN)
