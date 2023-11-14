"""protodjango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from rest_framework.urlpatterns import format_suffix_patterns

from myapp import views
from myapp.views import RuleUpdateView, WbsUpdateView
from registration import views as v

urlpatterns = [
    path("", views.work_in_progress),
    path("models/", views.urn_show),
    path("families/", views.families),
    path("sdrs/<int:id>/", views.sdrs),
    path("volumes/", views.volumes, name="volumes"),
    path("schedule/", views.schedule),
    # path('graph/', views.graph_show),
    path("rules/", views.rule_create),
    # path('rule_edit/<int:id>/', views.rule_edit),
    path("rule_edit/<int:pk>/", RuleUpdateView.as_view(), name="rule_edit"),
    # path('graph_info/', views.graph),
    path("new_graph/", views.new_graph),
    path("model_load/", views.urn_show),
    # path('file_upload/', views.file_upload),
    path("register/", v.register, name="register"),
    path("", include("django.contrib.auth.urls")),
    path("sdr/<int:pk>/", WbsUpdateView.as_view(), name="wbs_edit"),
    path("urn_index/", views.urn_index),
    path("projects/", views.projects),
    path("excel/", views.excel_upload),
    path("excel/", views.uploading, name="uploading"),
    path("urn_view/<int:id>/", views.urn_view),
    path("urn_ifc/<int:id>", views.urn_ifc),
    path("urn_create/", views.urn_create),
    path("project_create/", views.project_create),
    path("urn_edit/<int:id>/", views.urn_edit),
    path("project_edit/<int:id>/", views.project_edit),
    path("urn_delete/<int:id>/", views.urn_delete),
    path("upload/", views.upload, name="upload"),
    path("upload_gantt/", views.upload_gantt, name="upload_gantt"),
    path("add_link/", views.add_link, name="add_link"),
    path("add_node/", views.add_node, name="add_node"),
    path("model/<int:id>/", views.model),
    path("settings/", views.settings, name="settings"),
    path("save_model/", views.saveModel),
    path("family_delete/<int:id>/", views.rule_delete),
    path("sdr_delete/<int:id>/", views.sdr_delete),
    path("sdr_choose/<int:id>/", views.sdr),
    path("new_gantt/", views.new_gantt),
    path("hist_gantt/", views.hist_gantt),
    path("excel_export/", views.excel_export),
    re_path(r"^data/task/(?P<pk>[0-9]+)$", views.task_update),
    re_path(r"^data/task", views.task_add),
    re_path(r"^data/link/(?P<pk>[0-9]+)$", views.link_update),
    re_path(r"^data/link", views.link_add),
    re_path(r"^data/(.*)$", views.data_list),
    # path('__debug__/', include('debug_toolbar.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns = format_suffix_patterns(urlpatterns)
