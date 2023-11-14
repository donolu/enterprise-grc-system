from django.db import models
from django.utils import timezone
from django_tenants.models import TenantMixin, DomainMixin
import datetime


# Create your models here.
class Client(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField(
        default=lambda: timezone.now() + timezone.timedelta(days=30)
    )
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass
