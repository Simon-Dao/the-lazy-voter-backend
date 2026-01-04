import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import django
import sys
from utils import Request
from legislater_populate import add_legislator_with_bioguide

# 1. Make sure Python can find your project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# 3. Load env vars
load_dotenv()

# 4. Initialize Django
django.setup()

# 5. Import models
from core.db_models.constants import SPONSOR_TYPE
from core.db_models.bill import Bill, BillSponsor, BillSubject
from core.db_models.legislator import Legislator

req = Request()

API_KEY = os.getenv("NEXT_PUBLIC_CONGRESS_API_KEY")
BASE_URL = "https://api.congress.gov/v3"


# -------------------------------------------------------------------
# API HELPERS
# -------------------------------------------------------------------


def get_all_bills(congress_number=None, start_date=None, offset=0, limit=10):
    if not congress_number and not start_date:
        raise ValueError("congress_number or start_date required")

    url = f"{BASE_URL}/bill?offset={offset}&limit={limit}&api_key={API_KEY}"
    if congress_number:
        url += f"&congress={congress_number}"
    if start_date:
        url += f"&introducedDate={start_date}"

    data = req.safe_request(url)
    return data.get("bills", []), data.get("pagination", {}).get("count", 0)


def get_bill_info(congress, bill_type, number):
    url = f"{BASE_URL}/bill/{congress}/{bill_type.lower()}/{number}/?format=json&api_key={API_KEY}"
    data = req.safe_request(url).get("bill", {})

    subjects = []
    try:
        if data.get("subjects", {}).get("count", 0) > 0:
            subjects_url = data["subjects"]["url"] + f"&api_key={API_KEY}"
            subjects = get_subjects(subjects_url)
    except Exception:
        pass

    sponsors = [
        s["bioguideId"] for s in data.get("sponsors", []) if s.get("bioguideId")
    ]

    short_summary = ""
    try:
        if data.get("textVersions", {}).get("count", 0) > 0:
            short_summary_url = data["textVersions"]["url"] + f"&api_key={API_KEY}"
            short_summary = get_short_summary(short_summary_url)
    except Exception:
        pass

    return {
        "subjects": subjects,
        "short_summary": short_summary,
        "sponsors": sponsors,
    }


def get_subjects(url):
    data = req.safe_request(url)
    return [
        s.get("name")
        for s in data.get("subjects", {}).get("legislativeSubjects", [])
        if s.get("name")
    ]


def get_short_summary(url):
    data = req.safe_request(url)
    try:
        formatted_url = data["textVersions"][0]["formats"][2]["url"]
        resp = req.safe_request(formatted_url, headers={"Accept": "application/xml"})
        soup = BeautifulSoup(resp.text, "xml")
        tag = soup.find("official-title")
        return tag.text if tag else ""
    except Exception:
        return ""


# -------------------------------------------------------------------
# CORE LOGIC (FIXED)
# -------------------------------------------------------------------

def process_bills(bills, existing_bills, max_relevant=100):
    bills_to_create = []
    sponsor_refs = []      # (bill_key, bioguide)
    bill_subjects = {}     # bill_key -> subjects

    VALID_TYPES = {"HR", "S", "HJRES", "SJRES", "HCONRES", "SCONRES"}

    # 1️⃣ Filter invalid bills FIRST
    valid_bills = []
    for bill in bills:
        if bill.get("type") not in VALID_TYPES:
            continue

        if not bill.get("introducedDate"):
            continue

        if not bill.get("title") or bill["title"] in {
            "Reserved for the Speaker.",
            "Reserved for the Minority Leader.",
        }:
            continue

        key = (bill["congress"], bill["type"], bill["number"])
        if key in existing_bills:
            continue

        valid_bills.append(bill)

    # 2️⃣ Sort by introducedDate (latest first)
    valid_bills = sorted(
        valid_bills,
        key=lambda b: b["introducedDate"],
        reverse=True
    )[:min(len(valid_bills), max_relevant)]

    print("valid bills after filtering:", len(valid_bills))

    # 3️⃣ Process only the TOP 100 latest bills
    for bill in valid_bills:

        exists = Bill.objects.filter(
            congress=bill["congress"],
            type=bill["type"],
            number=bill["number"],
        ).exists()

        if exists:
            continue

        key = (bill["congress"], bill["type"], bill["number"])

        bill_info = get_bill_info(
            congress=bill["congress"],
            bill_type=bill["type"],
            number=bill["number"],
        )

        bill_subjects[key] = bill_info["subjects"]

        bill_obj = Bill(
            congress=bill["congress"],
            number=bill["number"],
            type=bill["type"],
            title=bill["title"],
            update_date=bill.get("latestAction", {}).get("actionDate"),
            introduction_date=bill["introducedDate"],
            short_summary=bill_info["short_summary"],
            ethics_score=1,
        )

        bills_to_create.append(bill_obj)

        for bioguide in bill_info["sponsors"]:
            sponsor_refs.append((key, bioguide))

        existing_bills.add(key)

    # 4️⃣ Save Bills
    print("bill to add count:", len(bills_to_create))
    Bill.objects.bulk_create(bills_to_create)

    # 5️⃣ Fetch saved Bills
    saved_bills = {
        (b.congress, b.type, b.number): b
        for b in Bill.objects.filter(
            congress__in={b.congress for b in bills_to_create}
        )
    }

    # 6️⃣ Build sponsors
    sponsors = []
    for bill_key, bioguide in sponsor_refs:
        bill = saved_bills.get(bill_key)
        if not bill:
            continue

        legislator = add_legislator_with_bioguide(bioguide)

        sponsors.append(
            BillSponsor(
                bill=bill,
                legislator=legislator,
                sponsor_type=SPONSOR_TYPE[1],
            )
        )

    print("sponsors to add:", len(sponsors))
    BillSponsor.objects.bulk_create(sponsors)

    print("subjects to add:", len(bill_subjects))
    print("##########################################")
    add_bill_subjects(bill_subjects)

    return bills_to_create

def add_bill_subjects(bill_subjects):
    subjects_to_create = []

    for (congress, bill_type, number), subjects in bill_subjects.items():
        bill = Bill.objects.filter(
            congress=congress,
            type=bill_type,
            number=number,
        ).first()

        if not bill:
            continue

        for subject in subjects:

            exists = BillSubject.objects.filter(
                bill=bill, political_subject=subject
            ).exists()

            if exists:
                continue

            subjects_to_create.append(
                BillSubject(
                    bill=bill,
                    political_subject=subject,
                )
            )
    BillSubject.objects.bulk_create(subjects_to_create)


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------


def populate_sponsored_bills(total_pool=-1, max_relevant=100):
    limit_per_request = 250
    legislators = Legislator.objects.all()
    billsToAdd = []

    print("begun populating bills for", len(legislators), "legislators")

    # get 100 most recent sponsored bills from each legislator
    for legislator in legislators:
        existing_bills = set()

        #TODO add a feature to turn this on or off im lazy
        if BillSponsor.objects.filter(legislator=legislator).exists():
            print("skipping",legislator.full_name)
            continue


        if total_pool == -1:
            _, total_pool = get_sponsored_bills(legislator.bioguide_id, 0, 1)

        for offset in range(0, total_pool, limit_per_request):

            limit = (
                total_pool - offset
                if total_pool - offset < limit_per_request
                else limit_per_request
            )

            bills, _ = get_sponsored_bills(legislator.bioguide_id, offset, limit)
            billsToAdd += bills

        # add the 100 bills to the database
        print("##########################################")
        print("adding bills for", legislator.full_name, end="")
        process_bills(billsToAdd, existing_bills, max_relevant=max_relevant)


def get_sponsored_bills(bioguide_id, offset=0, limit=10):
    url = (
        f"{BASE_URL}/member/{bioguide_id}/sponsored-legislation"
        f"?offset={offset}&limit={limit}&api_key={API_KEY}"
    )
    data = req.safe_request(url)
    return data.get("sponsoredLegislation", []), data.get("pagination", {}).get(
        "count", 0
    )
