import os
from dotenv import load_dotenv
import django
import sys
from constants import FEC_STATE_NAMES_TO_CODES
from urllib.parse import quote_plus
from utils import Request
from datetime import datetime

# 1. Make sure Python can find your project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Set the Django settings module **before calling django.setup()**
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "backend.settings"
)  # replace with actual project folder

# 3. Load environment variables
load_dotenv()

# 4. Initialize Django
django.setup()

from core.db_models.legislator import Legislator
from core.db_models.campaign import Campaign, Donor

req = Request()

CONGRESS_API_KEY = os.getenv("NEXT_PUBLIC_CONGRESS_API_KEY")
FEC_API_KEY = os.getenv("NEXT_PUBLIC_OPEN_FEC_API_KEY")
CONGRESS_BASE_URL = "https://api.congress.gov/v3"
FEC_BASE_URL = "https://api.open.fec.gov/v1"


def get_all_legislators(congress_number=None, offset=0, limit=1):
    """Fetch legislators for a given congress number or start date."""
    if not congress_number:
        raise ValueError("At least one of congress_number must be provided.")

    params = {
        "congress_number": congress_number,
        "offset": offset,
        "limit": limit,
        "api_key": CONGRESS_API_KEY,
    }

    data = req.safe_request_params(url=f"{CONGRESS_BASE_URL}/member", params=params)
    legislators = data.get("members", [])
    total = data.get("pagination", {}).get("count", 0)
    return legislators, total


def add_legislator_with_bioguide(bioguide_id):

    check = Legislator.objects.filter(bioguide_id=bioguide_id)

    if check.exists():
        return check.first()

    params = {"api_key": CONGRESS_API_KEY, "format": "json"}
    l = req.safe_request_params(
        url=f"{CONGRESS_BASE_URL}/member/{bioguide_id}", params=params
    ).get("member", {})

    key = l.get("bioguideId", "")

    legislator_obj = Legislator(
        bioguide_id=key,
        image_link=l.get("depiction", {}).get("imageUrl"),
        first_name=l.get("firstName", ""),
        full_name=l.get("directOrderName", ""),
        last_name=l.get("lastName", ""),
        birth_year=l.get("birthYear", 0),
        current_member=l.get("currentMember", False),
        current_party=max(
            l.get("partyHistory", []), key=lambda x: x.get("startYear", 0), default={}
        ).get("partyName", ""),
        state=l.get("state", ""),
        state_code=FEC_STATE_NAMES_TO_CODES.get(l.get("state", "")),
        current_chamber=max(
            l.get("terms", []), key=lambda x: x.get("startYear", 0), default={}
        ).get("chamber", ""),
        district=l.get("district", -1),
    )

    legislator_obj.save()

    return legislator_obj


def populate_donors(max_donors_per_committee=250, max_donors_per_campaign=50):
    campaigns = Campaign.objects.all()

    print('begun populating for',len(campaigns),'campaigns')

    for campaign in campaigns:

        fec_id = campaign.fec_id
        election_year = campaign.election_year
        donors_set = set()
        if election_year > datetime.now().year:
            continue

        # get all the committees associated
        params = {
            "api_key": FEC_API_KEY,
        }
        committees = req.safe_request_params(
            f"{FEC_BASE_URL}/candidate/{fec_id}/committees", params=params
        ).get("results", [])

        donorsToAdd = []
        for committee in committees:

            donor_objs = []
            if committee.get("committee_id") == None:
                continue

            params = {
                "committee_id": committee.get("committee_id"),
                "two_year_transaction_period": election_year,
                "per_page": max_donors_per_committee,
                "sort": "-contribution_receipt_amount",
                "api_key": FEC_API_KEY,
            }
            scheduleAs = req.safe_request_params(
                f"{FEC_BASE_URL}/schedules/schedule_a/", params=params
            ).get("results", [])
            for donor in scheduleAs:

                if (
                    donor.get("contributor_name") == None
                    or donor.get("committee").get("name") == None
                    or donor.get("contribution_receipt_date") == None
                ):
                    continue

                if donor.get("contribution_receipt_amount") == None:
                    continue

                donor_key = (
                    donor.get("contributor_name") or "",
                    donor.get("committee").get("name") or "",
                    donor.get("contribution_receipt_date") or "",
                )

                if donor_key in donors_set:
                    continue
                donors_set.add(donor_key)

                if Donor.objects.filter(
                    source_name=donor.get("contributor_name") or "",
                    recipient_name=donor.get("committee").get("name") or "",
                    campaign=campaign,
                    contribution_receipt_date=donor.get("contribution_receipt_date")
                    or "",
                ).exists():
                    continue

                donor_obj = Donor(
                    campaign=campaign,
                    recipient_name=donor.get("committee").get("name"),
                    source_name=donor.get("contributor_name") or "",
                    entity_type=donor.get("entity_type") or "",
                    contribution_receipt_amount=donor.get(
                        "contribution_receipt_amount", -1
                    ),
                    contribution_receipt_date=donor.get("contribution_receipt_date")
                    or "",
                )
                donor_objs.append(donor_obj)

            donorsToAdd += donor_objs

        donorsToAdd.sort(
            key=lambda donor: donor.contribution_receipt_amount,
            reverse=True,
        )
        donorsToAdd = donorsToAdd[: min(len(donorsToAdd), max_donors_per_campaign)]
        Donor.objects.bulk_create(donorsToAdd)


def populate_campaigns():
    legislators = Legislator.objects.all()

    print("populating campaigns has begun for ", len(legislators), "legislators")

    for l in legislators:

        # create term object
        fec_params = {
            # "name": l['name'],
            "name": quote_plus(l.full_name),
            "api_key": FEC_API_KEY,
        }

        #TODO remove dis pls
        if Campaign.objects.filter(bioguide_id=l.bioguide_id).exists():
            print('skipping', l.full_name)
            continue

        offices = req.safe_request_params(
            url=f"{FEC_BASE_URL}/candidates/search/", params=fec_params
        ).get("results", [])


        campaigns = []

        for o in offices:

            election_years = o["election_years"]
            total_params = {"api_key": FEC_API_KEY}

            if "candidate_id" not in o:
                continue

            totals = req.safe_request_params(
                url=f"{FEC_BASE_URL}/candidate/{o.get('candidate_id')}/totals",
                params=total_params,
            )["results"]

            totals_map = {total["candidate_election_year"]: total for total in totals}

            for year in election_years:
                exists = Campaign.objects.filter(
                        fec_id=o["candidate_id"],
                        election_year=year,
                ).exists()

                if exists:
                    continue

                fec_params = {"api_key": FEC_API_KEY}

                campaign_obj = Campaign(
                    fec_id=o.get("candidate_id", ""),
                    bioguide_id=l,
                    election_year=year,
                    office_full=o.get("office_full", ""),
                    other_political_committee_contributions=totals_map.get(
                        year, {}
                    ).get("other_political_committee_contributions", -1),
                    individual_itemized_contributions=totals_map.get(year, {}).get(
                        "individual_itemized_contributions", -1
                    ),
                    individual_unitemized_contributions=totals_map.get(year, {}).get(
                        "individual_unitemized_contributions", -1
                    ),
                    disbursements=totals_map.get(year, {}).get("disbursements", -1),
                    contributions=totals_map.get(year, {}).get("contributions", -1),
                )
                campaigns.append(campaign_obj)
        print("adding ", len(campaigns), " campaigns for ", l.full_name)
        Campaign.objects.bulk_create(campaigns)


def populate_legislatures(congress_number=119, total_legislators=-1):
    limit_per_request = 250
    if total_legislators == -1:
        _, total_legislators = get_all_legislators(
            congress_number=congress_number, limit=1
        )

    print("population has begun for", total_legislators, "legislators")

    ids = set()

    for offset in range(0, total_legislators, limit_per_request):

        if total_legislators - offset < limit_per_request:
            limit_per_request = total_legislators - offset

        legislators, _ = get_all_legislators(
            congress_number=congress_number, limit=limit_per_request, offset=offset
        )
        relevant = []

        for l in legislators:

            key = l.get("bioguideId")

            if key in ids:
                continue

            legislator_exists = Legislator.objects.filter(bioguide_id=key).exists()

            if legislator_exists:
                continue

            # Congress member more info
            more_info_params = {"api_key": CONGRESS_API_KEY}
            more_info_link = l["url"]
            more_info = req.safe_request_params(
                url=more_info_link, params=more_info_params
            ).get("member", {})

            if more_info.get("firstName") == None or more_info.get("lastName") == None:
                continue

            legislator_obj = Legislator(
                bioguide_id=key,
                image_link=l.get("depiction", {}).get("imageUrl") or "",
                first_name=more_info.get("firstName"),
                full_name=more_info.get("directOrderName") or "",
                last_name=more_info.get("lastName"),
                birth_year=more_info.get("birthYear") or -1,
                current_member=more_info.get("currentMember") or False,
                current_party=l.get("partyName") or "",
                state=l.get("state") or "",
                state_code=FEC_STATE_NAMES_TO_CODES.get(l.get("state"), "N/A"),
                current_chamber=max(
                    more_info.get("terms", []),
                    key=lambda x: x.get("startYear", 0),
                    default={},
                ).get("chamber", ""),
                district=l.get("district", -1),
            )

            relevant.append(legislator_obj)
            ids.add(key)
        print("adding", len(relevant), "legislators to the database")
        Legislator.objects.bulk_create(relevant)

# FEC API call: put all query params in params dictionary
