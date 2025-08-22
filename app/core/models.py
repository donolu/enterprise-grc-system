from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Tenant(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class User(AbstractUser):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="users", null=True, blank=True)

class Subscription(models.Model):
    PLAN_CHOICES = [("free","Free"), ("basic","Basic"), ("ent","Enterprise")]
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default="free")
    seats = models.PositiveIntegerField(default=5)
    trial_item = models.CharField(max_length=40, null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    has_legacy = models.BooleanField(default=False)

class AuditEvent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True)
    event = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(default=timezone.now)
