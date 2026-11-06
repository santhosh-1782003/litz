from django.db import models


class AadhaarDetails(models.Model):
    name = models.CharField(max_length=150, blank=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name