"""
Provision the Coordinator group.

Idempotent and self-healing: permissions are `set()`, not `add()`, so re-running
after someone hand-added `delete_incident` in the admin UI removes it again.

    python manage.py setup_coordinator_group
    python manage.py setup_coordinator_group --create ada      # new volunteer
    python manage.py setup_coordinator_group --user musa       # existing account
    python manage.py setup_coordinator_group --dry-run

Never use `createsuperuser` for a coordinator: is_coordinator() excludes
superusers, so such an account would get the normal admin, not the console.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.incidents.coordinator import COORDINATOR_GROUP

# Least privilege. A coordinator reviews and decides; they never add or delete.
# Media is viewable so thumbnails render, but IncidentMediaAdmin.get_model_perms
# keeps it off the admin index.
PERMISSIONS = [
    ("incident", ["view", "change"]),
    ("incidentmedia", ["view"]),
    ("responselog", ["view"]),
]


class Command(BaseCommand):
    help = "Create/refresh the Coordinator group and optionally add users to it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", action="append", default=[], dest="users",
            help="Username to make a coordinator. Repeatable.",
        )
        parser.add_argument(
            "--create", action="append", default=[], dest="create",
            help="Create this username as a coordinator if it does not exist. "
                 "The account starts with no usable password — set one with "
                 "`manage.py changepassword <username>`. Repeatable.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would change without writing.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        wanted = []
        for model, actions in PERMISSIONS:
            try:
                ct = ContentType.objects.get(app_label="incidents", model=model)
            except ContentType.DoesNotExist:
                raise CommandError(
                    f"Content type incidents.{model} is missing — run `manage.py migrate` first."
                )
            for action in actions:
                codename = f"{action}_{model}"
                try:
                    wanted.append(Permission.objects.get(content_type=ct, codename=codename))
                except Permission.DoesNotExist:
                    raise CommandError(
                        f"Permission {codename} is missing — run `manage.py migrate` first."
                    )

        group, created = Group.objects.get_or_create(name=COORDINATOR_GROUP)
        existing = set(group.permissions.values_list("codename", flat=True))
        target = {p.codename for p in wanted}

        self.stdout.write(
            self.style.SUCCESS(f"Group '{COORDINATOR_GROUP}' "
                               + ("created" if created else "already exists"))
        )
        for codename in sorted(target - existing):
            self.stdout.write(f"  + {codename}")
        for codename in sorted(existing - target):
            self.stdout.write(self.style.WARNING(f"  - {codename} (revoking)"))
        if target == existing and not created:
            self.stdout.write("  permissions already correct")

        User = get_user_model()

        # --create: make the account first, then fall through to the same
        # promotion path below. Never a superuser: is_coordinator() excludes
        # them, so a superuser in this group would silently get nothing.
        for username in options["create"]:
            user, made = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": True, "is_superuser": False},
            )
            if made:
                # No usable password: the operator sets one via changepassword,
                # so it never lands in shell history.
                user.set_unusable_password()
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"  created user {username}"))
            else:
                self.stdout.write(f"  {username} already exists")
            if username not in options["users"]:
                options["users"].append(username)

        for username in options["users"]:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"No user named {username!r}.")
            if user.is_superuser:
                # is_coordinator() deliberately excludes superusers, so adding
                # one to the group would have no effect. Say so instead of
                # silently doing nothing.
                self.stdout.write(self.style.WARNING(
                    f"  {username} is a superuser — already has full access; "
                    "the Coordinator group does not apply to them."
                ))
                continue
            self.stdout.write(f"  → {username}: staff=True, in group")
            if not dry_run:
                user.is_staff = True
                user.save(update_fields=["is_staff"])
                user.groups.add(group)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run — rolling back."))
            transaction.set_rollback(True)
            return

        group.permissions.set(wanted)
        self.stdout.write(self.style.SUCCESS("\nDone."))
