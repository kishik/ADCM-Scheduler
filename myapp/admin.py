from django.contrib import admin as dj_admin
from django.contrib import admin
from myapp.models import Project, ModelGroup, AutodeskExtractorRule, BimModel, Job
from myapp.models import URN, ActiveLink


class WorkAdmin(dj_admin.ModelAdmin):
    list_display = ("id", "name")


class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )


class ModelGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )


class AutodeskExtractorRuleAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "model_group",
        "name",
        "description",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )


class BimModelAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "model_group",
        "name",
        "description",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )


class JobAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "task_type",
        "created_at",
        "task_id",
    )


admin.site.register(Project, ProjectAdmin)
admin.site.register(ModelGroup, ModelGroupAdmin)
admin.site.register(AutodeskExtractorRule, AutodeskExtractorRuleAdmin)
admin.site.register(BimModel, BimModelAdmin)
admin.site.register(Job, JobAdmin)

dj_admin.site.register(ActiveLink)
dj_admin.site.register(URN)
