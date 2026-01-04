from django.test import TestCase

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