import os
from dotenv import load_dotenv
import django
import sys

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
from legislater_populate import (
    populate_legislatures,
    populate_campaigns,
    add_legislator_with_bioguide,
    populate_donors,
)
from bill_populate import populate_sponsored_bills

def main():
    # adds total amount of legislators
    # populate_legislatures(congress_number=CONGRESS_NUMBER, total_legislators=-1)

    # adds terms and totals for terms
    # populate_campaigns()


    # #adds 20 most revent bills with their subjects, sponsors
    populate_sponsored_bills(total_pool=500, max_relevant=50)

    # #adds 50 top donors to each campaign
    populate_donors(max_donors_per_committee=50, max_donors_per_campaign=50)

main()
