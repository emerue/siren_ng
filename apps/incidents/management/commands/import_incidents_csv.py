"""
Import incidents from a CSV file into the database.

Usage:
    python manage.py import_incidents_csv data/incidents_import.csv
    python manage.py import_incidents_csv data/incidents_import.csv --update   # overwrite existing

CSV columns (all required except resolved_at):
    source, external_id, reporter_hash, incident_type, description, severity,
    status, location_lat, location_lng, address_text, zone_name, media_urls,
    ai_confidence, fraud_score, is_infrastructure, created_at, resolved_at
"""
import csv
import json
import uuid
from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from apps.incidents.models import Incident

VALID_TYPES     = {"FIRE", "FLOOD", "COLLAPSE", "RTA", "EXPLOSION", "DROWNING", "HAZARD"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_STATUSES  = {"VERIFIED", "RESOLVED", "RESPONDING", "AGENCY_NOTIFIED", "VERIFYING", "REJECTED", "CLOSED"}


def _parse_bool(val: str) -> bool:
    return val.strip().upper() in ("TRUE", "1", "YES", "T")


def _parse_dt(val: str):
    if not val or not val.strip():
        return None
    val = val.strip()
    # Handle +01 offset (Python's fromisoformat needs +01:00)
    if val.endswith("+01"):
        val += ":00"
    elif val.endswith("+02"):
        val += ":00"
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Fallback: strip timezone and assume UTC
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(val[:19], fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _parse_media_urls(val: str) -> list:
    val = val.strip()
    if not val or val in ("[]", ""):
        return []
    try:
        result = json.loads(val)
        if isinstance(result, list):
            return [str(u) for u in result if u]
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: treat as single URL
    if val.startswith("http"):
        return [val]
    return []


class Command(BaseCommand):
    help = "Import incidents from a CSV file. Skips duplicates by external_id unless --update is passed."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--update",
            action="store_true",
            default=False,
            help="Update existing incidents (matched by external_id) instead of skipping",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and validate only — do not write to database",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        do_update = options["update"]
        dry_run = options["dry_run"]

        try:
            f = open(csv_path, newline="", encoding="utf-8-sig")
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        created = updated = skipped = errors = 0

        with f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # row 1 = header
                ext_id = row.get("external_id", "").strip()
                if not ext_id:
                    self.stderr.write(f"  Row {row_num}: missing external_id — skipped")
                    errors += 1
                    continue

                # Validate incident_type
                itype = row.get("incident_type", "").strip().upper()
                if itype not in VALID_TYPES:
                    self.stderr.write(f"  Row {row_num} [{ext_id}]: invalid type '{itype}' — skipped")
                    errors += 1
                    continue

                severity = row.get("severity", "MEDIUM").strip().upper()
                if severity not in VALID_SEVERITIES:
                    severity = "MEDIUM"

                status_val = row.get("status", "RESOLVED").strip().upper()
                # CLOSED is a computed display status — store as RESOLVED with old date
                if status_val == "CLOSED":
                    status_val = "RESOLVED"
                if status_val not in VALID_STATUSES:
                    status_val = "RESOLVED"

                # Parse floats
                try:
                    lat = float(row["location_lat"]) if row.get("location_lat", "").strip() else None
                    lng = float(row["location_lng"]) if row.get("location_lng", "").strip() else None
                except (ValueError, KeyError):
                    lat = lng = None

                try:
                    ai_conf = float(row.get("ai_confidence", 0.9))
                    fraud   = float(row.get("fraud_score", 0.0))
                except ValueError:
                    ai_conf, fraud = 0.9, 0.0

                created_at = _parse_dt(row.get("created_at", ""))
                resolved_at = _parse_dt(row.get("resolved_at", ""))

                media_urls = _parse_media_urls(row.get("media_urls", "[]"))

                zone_name = row.get("zone_name", "Lagos").strip() or "Lagos"
                address_text = row.get("address_text", "").strip()
                reporter_hash = row.get("reporter_hash", "").strip() or "import"
                source = row.get("source", "WEB").strip() or "WEB"
                is_infra = _parse_bool(row.get("is_infrastructure", "FALSE"))
                description = row.get("description", "").strip()

                if dry_run:
                    self.stdout.write(
                        f"  [dry] Row {row_num}: {ext_id} | {itype} | {zone_name} | "
                        f"{severity} | {status_val} | media={len(media_urls)}"
                    )
                    created += 1
                    continue

                existing = Incident.objects.filter(external_id=ext_id).first()

                if existing:
                    if not do_update:
                        skipped += 1
                        continue
                    # Update
                    existing.incident_type   = itype
                    existing.description     = description
                    existing.severity        = severity
                    existing.status          = status_val
                    existing.location_lat    = lat
                    existing.location_lng    = lng
                    existing.address_text    = address_text
                    existing.zone_name       = zone_name
                    existing.media_urls      = media_urls
                    existing.ai_confidence   = ai_conf
                    existing.fraud_score     = fraud
                    existing.is_infrastructure = is_infra
                    existing.resolved_at     = resolved_at
                    if created_at:
                        existing.created_at  = created_at
                    existing.save()
                    updated += 1
                    self.stdout.write(f"  Updated: {ext_id}")
                else:
                    Incident.objects.create(
                        id=uuid.uuid4(),
                        source=source,
                        external_id=ext_id,
                        reporter_hash=reporter_hash,
                        reporter_phone="",
                        incident_type=itype,
                        description=description,
                        severity=severity,
                        status=status_val,
                        location_lat=lat,
                        location_lng=lng,
                        address_text=address_text,
                        zone_name=zone_name,
                        media_urls=media_urls,
                        ai_confidence=ai_conf,
                        fraud_score=fraud,
                        ai_raw_response={"source": "csv_import"},
                        vouch_count=0,
                        vouch_threshold=3,
                        total_donations_kobo=0,
                        donation_count=0,
                        is_infrastructure=is_infra,
                        created_at=created_at or datetime.now(timezone.utc),
                        resolved_at=resolved_at,
                    )
                    created += 1
                    self.stdout.write(f"  Created: {ext_id} [{zone_name}]")

        label = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{label}Done — created: {created}, updated: {updated}, "
            f"skipped (duplicate): {skipped}, errors: {errors}"
        ))
