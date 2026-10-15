from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("runs/<int:pk>/", views.run_detail, name="run_detail"),
    path("runs/<int:pk>/download/", views.download, name="download"),
]
