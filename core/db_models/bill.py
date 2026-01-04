from django.db import models
from core.db_models.legislator import Legislator
from core.db_models.constants import STATUS_CHOICES, CHAMBER_CODE_CHOICES, SPONSOR_TYPE

# -----------------------------
# Models
# -----------------------------

class Bill(models.Model):
    congress = models.PositiveIntegerField()
    number = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_CHOICES[0]
    )
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    # introduced_date = models.DateField()
    update_date = models.DateField()
    introduction_date = models.DateField()
    short_summary = models.TextField(blank=True)
    ethics_score = models.FloatField(
        # validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

    class Meta:
        unique_together = ("number","type", "congress")

    def __str__(self):
        return f"{self.number} - {self.title}"

class BillSubject(models.Model):
    political_subject=models.CharField(max_length=100)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('bill', 'political_subject')

    def __str__(self):
        return f"{self.bill} - {self.political_subject}"


class BillSponsor(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)
    legislator = models.ForeignKey(Legislator, on_delete=models.CASCADE)
    sponsor_type = models.CharField(
        max_length=10,
        choices=SPONSOR_TYPE,
        default=SPONSOR_TYPE[0]
    )

    class Meta:
        unique_together = ('bill', 'legislator')

    def __str__(self):
        return f"{self.legislator} sponsors {self.bill}"

from django.db import models