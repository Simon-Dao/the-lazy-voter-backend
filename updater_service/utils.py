import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEXT_PUBLIC_CONGRESS_API_KEY")
BASE_URL = "https://api.congress.gov/v3"


def safe_request(url):
    """Perform a GET request and handle HTTP errors."""
    try:
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e} | URL: {url}")
        return {}
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from URL: {url}")
        return {}


def get_all_bills(congress_number=None, start_date=None, offset=0, limit=10):
    """Fetch bills for a given congress number or start date."""
    if not congress_number and not start_date:
        raise ValueError("At least one of congress_number or start_date must be provided.")

    url = f"{BASE_URL}/bill?offset={offset}&limit={limit}&api_key={API_KEY}"
    if congress_number:
        url += f"&congress={congress_number}"
    if start_date:
        url += f"&introducedDate={start_date}"

    data = safe_request(url)
    return data.get("bills", [])


def get_bill_info(congress, bill_type, number):
    """Fetch detailed info for a single bill with error handling."""
    bill_info_url = f"{BASE_URL}/bill/{congress}/{bill_type.lower()}/{number}/?format=json&api_key={API_KEY}"
    data = safe_request(bill_info_url).get("bill", {})

    # Subjects
    subjects = []
    try:
        if data.get("subjects", {}).get("count", 0) > 0:
            subjects_url = data["subjects"]["url"] + f"&api_key={API_KEY}"
            subjects = get_subjects(subjects_url)
    except Exception as e:
        print(f"Error fetching subjects for bill {number}: {e}")

    policyArea = ""
    try:
        policyArea = data.get("policyArea").get("name")
    except Exception as e:
        print(f"Error fetching policy area for bill {number}: {e}")

    # Short summary
    short_summary = ""
    try:
        if data.get("textVersions", {}).get("count", 0) > 0:
            short_summary_url = data["textVersions"]["url"] + f"&api_key={API_KEY}"
            short_summary = get_short_summary(short_summary_url)
    except Exception as e:
        print(f"Error fetching short summary for bill {number}: {e}")

    # Sponsors
    sponsors = []
    try:
        sponsors = [s.get("bioguideId") for s in data.get("sponsors", []) if s.get("bioguideId")]
    except Exception as e:
        print(f"Error fetching sponsors for bill {number}: {e}")

    return {
        "subjects": subjects,
        "short_summary": short_summary,
        "sponsors": sponsors,
        "policyArea": policyArea
    }


def get_subjects(subjects_url):
    """Fetch subjects with error handling."""
    data = safe_request(subjects_url)
    subjects = []
    try:
        subjects_list = data.get("subjects", {}).get("legislativeSubjects", [])
        subjects = [s.get("name") for s in subjects_list if s.get("name")]
    except Exception as e:
        print(f"Error parsing subjects: {e}")
    return subjects


def get_short_summary(short_summary_url):
    """Fetch the short summary safely."""
    data = safe_request(short_summary_url)
    try:
        formatted_url = data["textVersions"][0]["formats"][2]["url"]
        resp = requests.get(formatted_url, headers={"Accept": "application/xml"}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        title_tag = soup.find("official-title")
        return title_tag.text if title_tag else ""
    except (IndexError, KeyError, requests.RequestException) as e:
        print(f"Error fetching short summary: {e}")
        return ""


def process_bills(bills, congress_number):

  relevant = []

  for bill in bills:
      
    if bill.get("congress") != congress_number:
      continue
    if bill.get("title") == "Reserved for the Speaker." or not bill.get("title") or bill.get("title") == "Reserved for the Minority Leader.":
      continue

    try:
      print(f"Congress: {bill.get('congress')}")
      print(f"Number: {bill.get('number')}")
      print(f"Chamber: {bill.get('originChamber')} ({bill.get('originChamberCode')})")
      print(f"Title: {bill.get('title')}")
      print(f"Type: {bill.get('type', '').lower()}")
      print(f"Update Date: {bill.get('updateDate')}")

      bill_info = get_bill_info(
          congress=bill.get("congress"),
          bill_type=bill.get("type"),
          number=bill.get("number")
      )
      print(f"Subjects: {bill_info.get('subjects', []) + [bill_info['policyArea']]}")
      print(f"Short Summary: {bill_info.get('short_summary', '')}")
      print(f"Sponsors: {bill_info.get('sponsors', [])}")
      print("-" * 80)
      relevant.append(bill)

    except Exception as e:
        print(f"Error processing bill {bill.get('number')}: {e}")
    

  return relevant

if __name__ == "__main__":
    congress_number = 119
    bills = get_all_bills(congress_number=congress_number, offset=0, limit=50)
    bills = process_bills(bills, congress_number)
