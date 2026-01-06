from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from core.db_models.constants import PARTY_CHOICES, STATE_CHOICES
from core.db_models.legislator import Legislator

# -----------------------------
# Models
# -----------------------------

class Campaign(models.Model):
    fec_id = models.CharField(max_length=100)
    legislator = models.ForeignKey(Legislator, on_delete=models.CASCADE)
    election_year = models.IntegerField(validators=[MinValueValidator(1776)], default=-1)
    # end_year = models.IntegerField(validators=[MinValueValidator(1776)], default=-1)
    office_full = models.CharField(max_length=100, default="")
    # PAC contributions
    other_political_committee_contributions = models.FloatField(default=0)

    # Individual Contributions > $200
    individual_itemized_contributions = models.FloatField(default=0)

    # Individual Contributions < $200
    individual_unitemized_contributions = models.FloatField(default=0)

    # Total Spent
    disbursements = models.FloatField(default=0)

    # Total Raised
    contributions = models.FloatField(default=0)

    class Meta:
        unique_together = ('fec_id', 'election_year')
        
    def __str__(self):
        return f"{self.bioguide_id} ({self.start_year})"

class Donor(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    source_name = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=10)
    contribution_receipt_amount = models.FloatField()
    contribution_receipt_date = models.DateField()

    class Meta:
        unique_together = ('campaign','source_name', 'recipient_name', 'contribution_receipt_date')

    def __str__(self):
        return f"{self.name} - ${self.contribution_receipt_amount}"
