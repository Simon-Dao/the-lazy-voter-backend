from django.db import models
from core.db_models.constants import PARTY_CHOICES, STATE_CHOICES

# Create your models here.
class Legislator(models.Model):

  bioguide_id = models.CharField(primary_key=True, max_length=100)
  image_link = models.TextField(blank=True, null=True)
  first_name = models.CharField(max_length=100, default='')
  full_name = models.CharField(max_length=100, default='')
  last_name = models.CharField(max_length=100, default='')
  current_member = models.BooleanField(default=False)
  birth_year = models.IntegerField(null=True, blank=True)

  current_party = models.CharField(
    max_length=100,
    choices=PARTY_CHOICES,
    default=PARTY_CHOICES[0]
  )
  state = models.CharField(
    max_length=100,
    choices=STATE_CHOICES,
    default=STATE_CHOICES[0]
  )
  state_code = models.CharField(max_length=10, default="")
  district = models.IntegerField(default=-12)
  current_chamber = models.CharField(max_length=100)

  # candidate_status = models.CharField(max_length=100)