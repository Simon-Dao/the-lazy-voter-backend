from django.http import JsonResponse
from django.views.decorators.http import require_GET

from django.contrib.postgres.search import TrigramSimilarity
from core.db_models.legislator import Legislator

@require_GET
def search_legislator(request):
    
    return JsonResponse({"query": 'testing', "results": []})
