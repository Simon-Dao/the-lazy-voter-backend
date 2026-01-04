from django.urls import path
from . import views

urlpatterns = [
    # GET /api/v1/legislatures/search/?q=...
    path("legislatures/search/", views.search_legislator, name="search_legislator"),
    path("legislature/get/", views.get_legislator, name="get_legislator"),
    path("legislature/sponsored/legislation/", views.get_sponsored_legislation, name="get_sponsored_legislation"),
    path("legislature/donors/", views.get_donors, name="get_donors"),
    path("legislature/totals/", views.get_totals, name="get_totals"),
]