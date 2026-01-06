from typing import Tuple
from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import json
from core.db_models.legislator import Legislator
from core.db_models.bill import Bill, BillSponsor
from core.db_models.campaign import Campaign, Donor
from django.db.models import Q, Case, When, Value, IntegerField


# -----------------------------
# Explicit serializers
# -----------------------------

def _serialize_legislator(l: Legislator):
    return {
        "bioguide_id": l.bioguide_id,
        "image_link": l.image_link,
        "first_name": l.first_name,
        "full_name": l.full_name,
        "last_name": l.last_name,
        "current_member": l.current_member,
        "birth_year": l.birth_year,
        "current_party": l.current_party,
        "state": l.state,
        "state_code": l.state_code,
        "district": l.district,
        "current_chamber": l.current_chamber,
    }


def _serialize_campaign(c: Campaign):
    return {
        "id": c.id,
        "fec_id": c.fec_id,
        "election_year": c.election_year,
        "office_full": c.office_full,
        "other_political_committee_contributions": c.other_political_committee_contributions,
        "individual_itemized_contributions": c.individual_itemized_contributions,
        "individual_unitemized_contributions": c.individual_unitemized_contributions,
        "disbursements": c.disbursements,
        "contributions": c.contributions,
    }


def _serialize_donor(d: Donor):
    return {
        "source_name": d.source_name,
        "recipient_name": d.recipient_name,
        "entity_type": d.entity_type,
        "contribution_receipt_amount": d.contribution_receipt_amount,
        "contribution_receipt_date": d.contribution_receipt_date.isoformat() if d.contribution_receipt_date else None,
    }

# -----------------------------
# Helpers
# -----------------------------

def _get_donors(campaign, limit):
    donors = Donor.objects.filter(campaign=campaign)

    if not donors.exists():
        return Donor.objects.none()
    
    return donors



def _get_legislator(bioguide_id):

    result = Legislator.objects.filter(bioguide_id=bioguide_id)

    if not result.exists():
        return None, JsonResponse({"result": {}, "error": "bioguide_id does not exist"})

    return result.first(), None

def _get_campaigns(bioguide_id):

    legislator,err = _get_legislator(bioguide_id)

    if err:
        return None, JsonResponse({"result": {"campaigns":[]}, "error":err["error"]})
    
    campaigns = Campaign.objects.filter(legislator=legislator)

    if not campaigns.exists():
        return None, JsonResponse({"result": {"campaigns":[]}, "error": "no campaigns exist for legislature:"+bioguide_id})

    return campaigns, None

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

    return JsonResponse({"result": _serialize_legislator(legislator)})


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

    data, err = _load_body(request)
    if err:
        return err
    
    if "keywords" in data:
        #TODO use some kind of ml model to match bills with sim keywords
        for keyword in data["keywords"]:
            #check if any keywords in bill match keyword in keyword
            
            pass
    
    legislator, err = _get_legislator(bioguide_id)
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
    bioguide_id = request.GET.get('bioguide_id') or ""
    limit = request.GET.get('limit') or 25

    campaigns,err = _get_campaigns(bioguide_id)

    if err:
        return err

    result_obj = {'campaigns':[]}

    for campaign in campaigns:
        campaign_obj = _serialize_campaign(campaign)

        donors = _get_donors(campaign, limit)

        campaign_obj['donors'] = [_serialize_donor(d) for d in donors]

        result_obj['campaigns'].append(campaign_obj)

    return JsonResponse(result_obj)

@require_GET
def get_totals(request):
    """
    GET params:
      - bioguide_id OR id (required)

    NOTE: This depends on your schema. This tries to find a Total-like model automatically.
    """
    bioguide_id = request.GET.get("bioguide_id") or ""
    limit = request.GET.get("limit") or 25

    # data, err = _load_body(request)
    # if err:
    #     return err
    
    # if "keywords" in data:
    #     pass
    
    legislator, err = _get_legislator(bioguide_id)

    campaigns,err = _get_campaigns(bioguide_id)

    if err:
        return err

    result_obj = {'campaigns':[]}

    for campaign in campaigns:
        campaign_obj = _serialize_campaign(campaign)

        result_obj['campaigns'].append(campaign_obj)

    return JsonResponse(result_obj)