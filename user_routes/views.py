from typing import Tuple
from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core import serializers
import json
from django.forms.models import model_to_dict
from core.db_models.legislator import Legislator
from core.db_models.bill import Bill, BillSponsor, BillSubject
from django.db.models import Q, Case, When, Value, IntegerField

# -----------------------------
# Helpers
# -----------------------------

def _get_legislator(bioguide_id):

    result = Legislator.objects.filter(bioguide_id=bioguide_id)

    if not result.exists():
        return None, JsonResponse({"result": {}, "error": "bioguide_id does not exist"})

    return result.first(), None

def _load_body(request):
    """
    Returns (data, error_response).
    If parsing succeeds: (dict, None)
    If it fails: (None, JsonResponse)
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)

    if not isinstance(data, dict):
        return None, JsonResponse({"error": "Expected a JSON object (dict)"}, status=400)

    return data, None

def _search_legislator_simple(query: str, limit: int = 25):
    q = (query or "").strip()
    if not q:
        return Legislator.objects.none()

    tokens = [t for t in q.replace(",", " ").split() if t]

    # filter: any token matches first/last OR full_name contains the whole query
    cond = Q(full_name__icontains=q)
    for t in tokens:
        cond |= (
            Q(first_name__icontains=t) |
            Q(last_name__icontains=t) |
            Q(full_name__icontains=t)
        )

    # lightweight ranking: exact > startswith > contains (using whole query)
    return (
        Legislator.objects
        .filter(cond | Q(bioguide_id__iexact=q))
        .annotate(
            rank=Case(
                When(full_name__iexact=q, then=Value(0)),
                When(last_name__iexact=q, then=Value(1)),
                When(first_name__iexact=q, then=Value(2)),
                When(full_name__istartswith=q, then=Value(3)),
                When(last_name__istartswith=q, then=Value(4)),
                When(first_name__istartswith=q, then=Value(5)),
                default=Value(9),
                output_field=IntegerField(),
            )
        )
        .order_by("rank", "last_name", "first_name")[:limit]
    )

# -----------------------------
# Views
# -----------------------------
@require_GET
def search_legislator(request):
    """
    SQLite-safe search.

    GET params:
      - q : search string by partial name or exact bioguide_id
      - limit: optional limits results length
    """
    q = request.GET.get("q") or ""
    limit = request.GET.get("limit") or None

    results = list(_search_legislator_simple(query=q, limit=limit).values())

    return JsonResponse({"query": q, "results": results})


@require_GET
def get_legislator(request):
    """
    GET params:
      - bioguide_id OR id
    """
    bioguide_id = request.GET.get("bioguide_id") or ""

    legislator, err = _get_legislator(bioguide_id)

    if err:
        return err

    return JsonResponse({"result": model_to_dict(legislator)})


@require_GET
def get_sponsored_legislation(request):
    """
    GET params:
      - bioguide_id OR id (required)
      - limit (optional, default 25)
    
    BODY params:
      - keywords (optional filter)
    """
    bioguide_id = request.GET.get("bioguide_id") or ""
    limit = request.GET.get("limit") or 25

    # data, err = _load_body(request)
    # if err:
    #     return err
    
    # if "keywords" in data:
    #     pass
    
    legislator, err = _get_legislator(bioguide_id)
    print(legislator.full_name)
    # get sponsored bills now
    sponsors = BillSponsor.objects.filter(legislator=legislator).select_related("bill")
    bills = Bill.objects.filter(billsponsor__in=sponsors).distinct()
    bills = list(bills.values())

    return JsonResponse({"bioguide_id": bioguide_id, "results": bills})


@require_GET
def get_donors(request):
    """
    GET params:
      - bioguide_id OR id (required)
      - limit (optional, default 25)

    NOTE: This depends on your schema. This tries to find a Donor-like model automatically.
    """

    return JsonResponse({"bioguide_id": leg.bioguide_id, "results": list(qs.values(*fields))})

@require_GET
def get_totals(request):
    """
    GET params:
      - bioguide_id OR id (required)

    NOTE: This depends on your schema. This tries to find a Total-like model automatically.
    """

    return JsonResponse({"bioguide_id": leg.bioguide_id, "results": list(qs.values(*fields))})