import json

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from unittest.mock import patch

from resources.models import CatalogResource, CurriculumSubject, Programme


@pytest.mark.django_db
def test_catalog_models_keep_unverified_curriculum_explicit():
    programme = Programme.objects.create(
        source_key="culup:program:test-program",
        official_title="Test programme",
        level=Programme.LEVEL_UNDERGRADUATE,
        school="Test school",
        official_url="https://www.culko.in/programs",
    )

    assert programme.curriculum_status == Programme.CURRICULUM_NOT_PUBLICLY_VERIFIED
    assert CurriculumSubject.objects.filter(programme=programme).count() == 0


@pytest.mark.django_db
def test_catalog_resource_requires_approval_and_active_state_for_students():
    programme = Programme.objects.create(
        source_key="culup:program:visibility-test",
        official_title="Visibility test",
        level=Programme.LEVEL_UNDERGRADUATE,
        official_url="https://www.culko.in/programs",
    )
    resource = CatalogResource.objects.create(
        source_key="nptel:visibility-test",
        title="Verified supplementary course",
        canonical_url="https://nptel.ac.in/courses/visibility-test",
        source_organization="NPTEL",
        resource_type=CatalogResource.TYPE_COURSE,
        source_class=CatalogResource.SOURCE_EXTERNAL,
        programme=programme,
        link_status=CatalogResource.LINK_WORKING,
    )

    assert not resource.is_student_visible
    resource.review_status = CatalogResource.REVIEW_APPROVED
    resource.save(update_fields=["review_status"])
    assert resource.is_student_visible
    resource.is_active = False
    resource.save(update_fields=["is_active"])
    assert not resource.is_student_visible


@pytest.mark.django_db
def test_cuup_programme_import_is_idempotent_and_preserves_admin_choices():
    call_command("import_cuup_catalog", batch="programmes", stdout=None)
    first_count = Programme.objects.count()
    assert first_count == 83

    disabled = Programme.objects.get(official_title="B.Tech (CSE)")
    disabled.is_active = False
    disabled.save(update_fields=["is_active"])

    call_command("import_cuup_catalog", batch="programmes", stdout=None)

    assert Programme.objects.count() == first_count
    assert not Programme.objects.get(pk=disabled.pk).is_active


@pytest.mark.django_db
def test_verified_curriculum_snapshot_import_is_idempotent():
    with open("resources/data/cuup_curricula.json", encoding="utf-8") as source:
        curricula = json.load(source)
    call_command("import_cuup_catalog", batch="programmes")
    call_command("import_cuup_catalog", batch="curricula")

    expected_count = len(curricula["subjects"])
    assert expected_count > 0
    assert CurriculumSubject.objects.count() == expected_count
    assert Programme.objects.filter(
        curriculum_status=Programme.CURRICULUM_PARTIALLY_VERIFIED
    ).exists()
    assert Programme.objects.filter(
        curriculum_status=Programme.CURRICULUM_NOT_PUBLICLY_VERIFIED
    ).exists()
    assert not CurriculumSubject.objects.filter(
        subject_name__icontains="fee"
    ).exists()

    call_command("import_cuup_catalog", batch="curricula")
    assert CurriculumSubject.objects.count() == expected_count


@pytest.mark.django_db
def test_official_curriculum_links_import_and_keep_admin_disable_state():
    call_command("import_cuup_catalog", batch="programmes")
    call_command("import_cuup_catalog", batch="curricula")
    call_command("import_cuup_catalog", batch="resources")

    resources = CatalogResource.objects.filter(source_class=CatalogResource.SOURCE_CUUP_OFFICIAL)
    assert resources.count() == 80
    assert sum(resource.curriculum_subjects.count() for resource in resources) == 1242
    assert resources.filter(
        review_status=CatalogResource.REVIEW_APPROVED,
        link_status=CatalogResource.LINK_WORKING,
        is_active=True,
    ).count() == 80

    disabled = resources.first()
    disabled.is_active = False
    disabled.save(update_fields=["is_active"])
    call_command("import_cuup_catalog", batch="resources")

    assert CatalogResource.objects.count() == 83
    assert not CatalogResource.objects.get(pk=disabled.pk).is_active


@pytest.mark.django_db
def test_verified_c_programming_resources_are_linked_idempotently():
    call_command("import_cuup_catalog", batch="programmes")
    call_command("import_cuup_catalog", batch="curricula")
    call_command("import_cuup_catalog", batch="resources")

    external = CatalogResource.objects.filter(
        source_class=CatalogResource.SOURCE_EXTERNAL,
        curriculum_subjects__subject_name="Computer Programming Using C",
        review_status=CatalogResource.REVIEW_APPROVED,
        link_status=CatalogResource.LINK_WORKING,
        is_active=True,
    ).distinct()
    assert external.count() == 3
    assert sum(resource.curriculum_subjects.count() for resource in external) == 12

    call_command("import_cuup_catalog", batch="resources")
    assert CatalogResource.objects.filter(source_class=CatalogResource.SOURCE_EXTERNAL).count() == 3


@pytest.mark.django_db
def test_library_lists_only_approved_active_catalog_links_for_students():
    user_model = get_user_model()
    student = user_model.objects.create_user(
        username="catalog-student",
        email="catalog-student@example.test",
        password="test-password-only",
    )
    programme = Programme.objects.create(
        source_key="culup:program:library-test",
        official_title="Library test programme",
        level=Programme.LEVEL_UNDERGRADUATE,
        official_url="https://www.culko.in/programs",
    )
    common = {
        "source_organization": "NPTEL",
        "resource_type": CatalogResource.TYPE_COURSE,
        "source_class": CatalogResource.SOURCE_EXTERNAL,
        "programme": programme,
        "link_status": CatalogResource.LINK_WORKING,
    }
    CatalogResource.objects.create(
        source_key="nptel:catalog-pending",
        title="Pending resource",
        canonical_url="https://nptel.ac.in/courses/catalog-pending",
        **common,
    )
    CatalogResource.objects.create(
        source_key="nptel:catalog-disabled",
        title="Disabled resource",
        canonical_url="https://nptel.ac.in/courses/catalog-disabled",
        review_status=CatalogResource.REVIEW_APPROVED,
        is_active=False,
        **common,
    )
    CatalogResource.objects.create(
        source_key="nptel:catalog-approved",
        title="Approved resource",
        canonical_url="https://nptel.ac.in/courses/catalog-approved",
        review_status=CatalogResource.REVIEW_APPROVED,
        **common,
    )

    client = Client()
    client.force_login(student)
    response = client.get(reverse("resources:library"))

    assert response.status_code == 200
    assert "Approved resource" in response.content.decode()
    assert "Pending resource" not in response.content.decode()
    assert "Disabled resource" not in response.content.decode()


@pytest.mark.django_db
def test_library_uses_reviewed_snapshot_when_database_is_unavailable():
    student = get_user_model().objects.create_user(
        username="snapshot-student", email="snapshot@example.test", password="test-password-only"
    )
    client = Client()
    client.force_login(student)
    with patch("resources.views._library_database", side_effect=__import__("django.db").db.OperationalError("offline")):
        response = client.get(reverse("resources:library"))

    assert response.status_code == 200
    assert response.context["database_fallback"] is True
    assert response.context["catalog_total"] == 83
    assert "reviewed catalogue snapshot" in response.content.decode()


@pytest.mark.django_db
def test_student_dashboard_shows_approved_catalog_links_when_no_uploaded_resources_exist():
    user_model = get_user_model()
    student = user_model.objects.create_user(
        username="dashboard-catalog-student",
        email="dashboard-catalog-student@example.test",
        password="test-password-only",
    )
    programme = Programme.objects.create(
        source_key="culup:program:dashboard-test",
        official_title="Dashboard test programme",
        level=Programme.LEVEL_UNDERGRADUATE,
        official_url="https://www.culko.in/programs",
    )
    CatalogResource.objects.create(
        source_key="nptel:dashboard-test",
        title="Dashboard catalogue resource",
        canonical_url="https://nptel.ac.in/courses/dashboard-test",
        source_organization="NPTEL",
        resource_type=CatalogResource.TYPE_COURSE,
        source_class=CatalogResource.SOURCE_EXTERNAL,
        programme=programme,
        review_status=CatalogResource.REVIEW_APPROVED,
        link_status=CatalogResource.LINK_WORKING,
    )

    client = Client()
    client.force_login(student)
    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 200
    assert "Dashboard catalogue resource" in response.content.decode()


def test_official_programme_data_has_distinct_titles_and_source_keys():
    with open("resources/data/cuup_programmes.json", encoding="utf-8") as source:
        programmes = json.load(source)

    assert len(programmes) == 83
    assert sum(row["level"] == "undergraduate" for row in programmes) == 63
    assert sum(row["level"] == "postgraduate" for row in programmes) == 20
    assert len({row["source_key"] for row in programmes}) == 83
    assert len({programme["official_title"] for programme in programmes}) == 83
    assert all(programme["official_url"].startswith("https://www.culko.in/") for programme in programmes)

    with open("resources/data/cuup_curricula.json", encoding="utf-8") as source:
        curricula = json.load(source)
    assert len(curricula["programmes"]) == 83
    assert len(curricula["subjects"]) == 1242
    assert all(row["year_of_study"] == 1 for row in curricula["subjects"])
    assert all(row["semester"] in (1, 2) for row in curricula["subjects"])
    assert all(not row["official_code"] for row in curricula["subjects"])
