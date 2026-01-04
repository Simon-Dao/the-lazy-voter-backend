from django.urls import path
from . import views

urlpatterns = [
    # GET /api/v1/legislatures/search/?q=...
    path("legislatures/search/", views.search_legislator, name="search_legislator"),
]