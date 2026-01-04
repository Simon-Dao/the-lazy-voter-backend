from django.contrib import admin
from core.db_models.bill import Bill
from core.db_models.legislator import Legislator
from core.db_models.vote import BillVote, VoteCast
from core.db_models.campaign import Campaign, Donor 

# Register your models here.
admin.site.register(Legislator)
admin.site.register(Bill)
admin.site.register(BillVote)
admin.site.register(VoteCast)
admin.site.register(Campaign)
admin.site.register(Donor)