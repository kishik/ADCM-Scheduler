from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from rest_framework.urlpatterns import format_suffix_patterns

from myapp import views
from registration import views as v

urlpatterns = [
    path("", views.projects),
    path("volumes/<int:project_id>/", views.volumes, name="volumes"),
    path("adcm_volumes/<int:project_id>/", views.adcm_volumes, name="adcm_volumes"),
    path("schedule/", views.schedule),
    path("adcm_schedule/", views.adcm_schedule),
    path("new_graph/", views.new_graph),
    path("register/", v.register, name="register"),
    path("", include("django.contrib.auth.urls")),
    path("projects/", views.projects),
    path("project_create/", views.project_create),
    path("project_edit/<int:id>/", views.project_edit),
    path("project_delete/<int:id>/", views.project_delete),
    path("excel/", views.excel_upload, name="excel"),
    path("upload/", views.upload, name="upload"),
    path("upload_gantt/", views.upload_gantt, name="upload_gantt"),
    path("add_link/", views.add_link, name="add_link"),
    path("add_node/", views.add_node, name="add_node"),
    path("new_gantt/", views.new_gantt),
    path("hist_gantt/", views.hist_gantt),
    path("adcm_projects/", views.adcm_projects),
    re_path(r"^data/(.*)$", views.data_list),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns = format_suffix_patterns(urlpatterns)
