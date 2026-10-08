from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, EmailField

from apps.abstracts.models import AbstractBaseModel


class User(AbstractUser, AbstractBaseModel):
    """Custom user model extending Django's AbstractUser with soft-delete."""

    phone_number = CharField(max_length=20, blank=True)
    address = CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['date_joined']

    def __str__(self):
        return self.get_full_name() or self.username
