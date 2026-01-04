from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from core.db_models.constants import PARTY_CHOICES, STATE_CHOICES, CHAMBER_CHOICES
from core.db_models.legislator import Legislator

# -----------------------------
# Models
# -----------------------------

class BillVote(models.Model):
    bill = models.ForeignKey('Bill', on_delete=models.CASCADE)
    chamber = models.CharField(
        max_length=10,
        choices=CHAMBER_CHOICES,
        default=CHAMBER_CHOICES[0]
    )
    vote_question = models.CharField(max_length=100)
    vote_result = models.CharField(max_length=10)
    nay_count = models.IntegerField(default=0)
    yea_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.bill} - {self.vote_question}"

class VoteCast(models.Model):
    bill_vote = models.ForeignKey(BillVote, on_delete=models.CASCADE)
    legislator = models.ForeignKey(Legislator, on_delete=models.CASCADE)
    vote = models.CharField(max_length=10)

    class Meta:
        unique_together = ('bill_vote', 'legislator')  # replaces CompositePrimaryKey

    def __str__(self):
        return f"{self.legislator} voted {self.vote} on {self.bill_vote}"