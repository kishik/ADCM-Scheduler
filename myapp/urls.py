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
from django.urls import path, include
from myapp import views
from django.conf import settings
from django.conf.urls.static import static
from registration import views as v

urlpatterns = [
    path('', views.work_in_progress),
    # path('search', views.search),

    path('models/', views.urn_show),
    path('families/', views.families),
    path('sdrs/', views.sdrs),
    path('volumes/', views.volumes),
    path('timetable/', views.work_in_progress),

    path('graph/', views.graph_show),
    path('rules/', views.rule_create),

    # path('work/', views.get_works),
    path('work_index/', views.works_index),
    path('graph_info/', views.graph),
    path('work/<str:id>', views.work_by_id),
    path('search/', views.search),
    path('new_graph/', views.new_graph),
    path('model_load/', views.urn_show),
    path('file_upload/', views.file_upload),
    path('register/', v.register, name="register"),
    path('', include("django.contrib.auth.urls")),  # <-- added
    # path('update_urn/', views.update_urn),
    # path('file_upload/', views.file_upload),
    path('urn_index/', views.urn_index),
    path('urn_create/', views.urn_create),
    path('urn_edit/<int:id>/', views.urn_edit),
    path('urn_delete/<int:id>/', views.urn_delete),
    path('index/', views.index),
    path('upload/', views.upload, name="upload"),
    path('model/<int:id>/', views.model),
    path('settings/', views.settings, name="settings"),
    path('save_model/', views.saveModel),
    path('family_delete/<int:id>/', views.rule_delete),
    path('sdr_delete/<int:id>/', views.sdr_delete),
    path('sdr/<int:id>/', views.sdr),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
