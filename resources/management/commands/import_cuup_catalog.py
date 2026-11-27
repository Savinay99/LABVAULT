"""Idempotently import the versioned CU-UP academic catalogue snapshot."""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from resources.models import CatalogResource, CurriculumSubject, Programme


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_FILES = {
    "programmes": DATA_DIR / "cuup_programmes.json",
    "curricula": DATA_DIR / "cuup_curricula.json",
    "resources": DATA_DIR / "cuup_catalog_resources.json",
}
OFFICIAL_HOST = "www.culko.in"


def _read_json(path):
    if not path.is_file():
        raise CommandError(f"Catalogue data file is missing: {path.name}.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError(f"Catalogue data file could not be read: {path.name}.") from exc


def _is_official_url(value):
    parts = urlsplit(value)
    return parts.scheme == "https" and parts.hostname == OFFICIAL_HOST and not parts.username


def _validate_unique_records(records, key, batch_label):
    keys = [record.get(key) for record in records]
    if not records or any(not value for value in keys) or len(set(keys)) != len(keys):
        raise CommandError(f"{batch_label} data contains missing or duplicate identifiers.")


class Command(BaseCommand):
    help = "Import the CU-UP programmes, verified curriculum rows, and curated resource links."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            choices=("programmes", "curricula", "resources", "all"),
            default="programmes",
            help="Catalogue batch to import (default: programmes).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        batch = options["batch"]
        batches = ("programmes", "curricula", "resources") if batch == "all" else (batch,)
        for selected in batches:
            counts = getattr(self, f"_import_{selected}")()
            summary = ", ".join(f"{name} {count}" for name, count in counts.items())
            self.stdout.write(self.style.SUCCESS(f"{selected.title()} import complete: {summary}."))

    def _import_programmes(self):
        records = _read_json(DATA_FILES["programmes"])
        _validate_unique_records(records, "source_key", "Programme")
        if len(records) != 83:
            raise CommandError(f"Expected all 83 official CU-UP programmes; found {len(records)}.")
        levels = {Programme.LEVEL_UNDERGRADUATE, Programme.LEVEL_POSTGRADUATE}
        if sum(row.get("level") == Programme.LEVEL_UNDERGRADUATE for row in records) != 63:
            raise CommandError("The official catalogue snapshot must contain 63 undergraduate programmes.")
        if sum(row.get("level") == Programme.LEVEL_POSTGRADUATE for row in records) != 20:
            raise CommandError("The official catalogue snapshot must contain 20 postgraduate programmes.")

        created_count = 0
        updated_count = 0
        for record in records:
            url = record.get("official_url", "").strip()
            if not _is_official_url(url):
                raise CommandError("A programme URL is outside the verified CU-UP website.")
            if record.get("level") not in levels:
                raise CommandError("A programme has an invalid academic level.")
            if record.get("curriculum_status") not in dict(Programme.CURRICULUM_STATUS_CHOICES):
                raise CommandError("A programme has an invalid curriculum verification status.")

            verified_at = record.get("curriculum_last_verified_date")
            defaults = {
                "official_title": record["official_title"],
                "level": record["level"],
                "school": record.get("school", ""),
                "official_url": url,
                "curriculum_url": record.get("curriculum_url", ""),
                "curriculum_status": record["curriculum_status"],
                "curriculum_last_verified_at": (
                    datetime.fromisoformat(f"{verified_at}T00:00:00+00:00")
                    if verified_at
                    else None
                ),
            }
            _, created = Programme.objects.update_or_create(
                source_key=record["source_key"], defaults=defaults
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        return {"created": created_count, "updated": updated_count, "total": len(records)}

    def _import_curricula(self):
        data = _read_json(DATA_FILES["curricula"])
        programme_records = data.get("programmes", [])
        subject_records = data.get("subjects", [])
        _validate_unique_records(programme_records, "source_key", "Curriculum programme")
        source_keys = set(Programme.objects.values_list("source_key", flat=True))
        absent = {row["source_key"] for row in programme_records} - source_keys
        if absent:
            raise CommandError("Import programmes before curriculum subjects.")
        subject_keys = [
            (
                row.get("programme_source_key"),
                row.get("year_of_study"),
                row.get("semester"),
                row.get("subject_name", "").strip().casefold(),
            )
            for row in subject_records
        ]
        if any(not key[0] or not key[1] or not key[2] or not key[3] for key in subject_keys):
            raise CommandError("A curriculum subject is missing its verified programme, year, semester, or title.")
        if len(set(subject_keys)) != len(subject_keys):
            raise CommandError("Curriculum data contains duplicate programme/term/subject rows.")

        for record in programme_records:
            programme = Programme.objects.get(source_key=record["source_key"])
            curriculum_url = record.get("curriculum_url", "")
            if curriculum_url and not _is_official_url(curriculum_url):
                raise CommandError("A curriculum URL is outside the verified CU-UP website.")
            programme.curriculum_url = curriculum_url
            programme.curriculum_status = record["curriculum_status"]
            programme.save(update_fields=["curriculum_url", "curriculum_status", "updated_at"])

        created_count = 0
        updated_count = 0
        for record in subject_records:
            programme = Programme.objects.get(source_key=record["programme_source_key"])
            curriculum_url = record.get("curriculum_url", "").strip()
            if not _is_official_url(curriculum_url):
                raise CommandError("A curriculum subject is not backed by an official CU-UP page.")
            _, created = CurriculumSubject.objects.update_or_create(
                programme=programme,
                year_of_study=record["year_of_study"],
                semester=record["semester"],
                subject_name=record["subject_name"],
                defaults={
                    "official_code": record.get("official_code", ""),
                    "curriculum_url": curriculum_url,
                    "sequence": record.get("sequence", 0),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        return {"subjects_created": created_count, "subjects_updated": updated_count, "total": len(subject_records)}

    def _import_resources(self):
        records = _read_json(DATA_FILES["resources"])
        _validate_unique_records(records, "source_key", "Catalog resource")
        source_keys = set(Programme.objects.values_list("source_key", flat=True))
        created_count = 0
        updated_count = 0
        relation_count = 0
        for record in records:
            parts = urlsplit(record.get("canonical_url", "").strip())
            if parts.scheme != "https" or not parts.hostname or parts.username:
                raise CommandError("A catalogue resource must use a valid HTTPS URL without embedded credentials.")
            if record.get("source_class") not in dict(CatalogResource.SOURCE_CLASS_CHOICES):
                raise CommandError("A catalogue resource has an invalid source classification.")
            if record.get("resource_type") not in dict(CatalogResource.RESOURCE_TYPE_CHOICES):
                raise CommandError("A catalogue resource has an invalid resource type.")

            programme_key = record.get("programme_source_key")
            if programme_key and programme_key not in source_keys:
                raise CommandError("A catalogue resource refers to an unknown programme.")
            defaults = {
                "title": record["title"],
                "canonical_url": record["canonical_url"],
                "source_organization": record["source_organization"],
                "resource_type": record["resource_type"],
                "source_class": record["source_class"],
                "programme": Programme.objects.get(source_key=programme_key) if programme_key else None,
                "language": record.get("language", ""),
                "access_type": record.get("access_type", CatalogResource.ACCESS_UNKNOWN),
                "description": record.get("description", ""),
            }
            if record.get("link_status") in dict(CatalogResource.LINK_STATUS_CHOICES):
                defaults["link_status"] = record["link_status"]
            if record.get("last_verified_at"):
                defaults["last_verified_at"] = datetime.fromisoformat(record["last_verified_at"])

            resource, created = CatalogResource.objects.update_or_create(
                source_key=record["source_key"], defaults=defaults
            )
            if created:
                created_count += 1
                if (
                    record.get("review_status") == CatalogResource.REVIEW_APPROVED
                    and resource.link_status == CatalogResource.LINK_WORKING
                ):
                    resource.review_status = CatalogResource.REVIEW_APPROVED
                    resource.save(update_fields=["review_status", "updated_at"])
            else:
                updated_count += 1
            for subject_key in record.get("subjects", []):
                try:
                    programme_key, year, semester, subject_name = subject_key
                    subject = CurriculumSubject.objects.get(
                        programme__source_key=programme_key,
                        year_of_study=year,
                        semester=semester,
                        subject_name=subject_name,
                    )
                except (ValueError, CurriculumSubject.DoesNotExist) as exc:
                    raise CommandError("A catalogue resource refers to an unknown curriculum subject.") from exc
                already_linked = resource.curriculum_subjects.filter(pk=subject.pk).exists()
                resource.curriculum_subjects.add(subject)
                relation_count += int(not already_linked)
        return {"created": created_count, "updated": updated_count, "subject_links_added": relation_count, "total": len(records)}
