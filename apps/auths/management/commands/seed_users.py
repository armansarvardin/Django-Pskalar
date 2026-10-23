import random
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.auths.models import User


class Command(BaseCommand):
    """Fill the database with test customer accounts."""

    help = "Create test users (customers) that share one password."

    MIN_PASSWORD_LEN = 8

    PEOPLE: list[tuple[str, str]] = [
        ("Arman", "Sarvardin"),
        ("Daniyal", "Karimov"),
        ("Sardor", "Aliev"),
        ("Jasur", "Rakhimov"),
        ("Aziz", "Umarov"),
        ("Nilufar", "Nazarova"),
        ("Madina", "Kholmatova"),
        ("Kamila", "Toshmatova"),
        ("Shakhzod", "Mirzaev"),
        ("Bobur", "Yusupov"),
    ]
    ADDRESSES: list[str] = [
        "Tashkent, Yunusabad 4, Block 12",
        "Tashkent, Chilanzar 9, Apt 45",
        "Samarkand, Registan St 7",
        "Tashkent, Mirzo Ulugbek, Block 3",
        "Bukhara, Naqshbandi 15",
        "Fergana, Mustaqillik 33",
    ]

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--password",
            type=str,
            default="testpass123",
            help="Password for every new user (default: testpass123)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Command entry point."""
        password: str = options["password"]
        if len(password) < self.MIN_PASSWORD_LEN:
            raise CommandError(
                f"--password must be at least {self.MIN_PASSWORD_LEN} characters"
            )

        users: list[User] = self.__create_users(password)

        if users:
            self.stdout.write(self.style.SUCCESS(f"Created {len(users)} users."))
        else:
            self.stdout.write(self.style.WARNING("Nothing new to create."))

    def __create_users(self, password: str) -> list[User]:
        """Create users that don't exist yet. Skip known usernames."""
        # Usernames are unique across soft-deleted users too, so check all of them.
        used_usernames: set[str] = set(
            User.objects.values_list("username", flat=True)
        )
        # Hash once instead of per user: hashing is slow on purpose.
        hashed_password: str = make_password(password)

        new_users: list[User] = []
        for first_name, last_name in self.PEOPLE:
            username: str = f"{first_name.lower()}.{last_name.lower()}"
            if username in used_usernames:
                continue
            used_usernames.add(username)
            new_users.append(
                User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{username}@example.com",
                    phone_number=f"+99890{random.randint(1000000, 9999999)}",
                    address=random.choice(self.ADDRESSES),
                    password=hashed_password,
                )
            )

        User.objects.bulk_create(new_users)
        return new_users
