"""Model structure tests: cross-cutting verification of all 13 models.

# kills: missing model, wrong tablename, missing mixin column, AuditLog having
#        deleted_at/updated_at, UUIDv7 id without default, DateTime without
#        timezone=True, status column using String instead of ENUM, missing
#        JSONB column on expected model
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB

from app.db.mixins import EntityMetadataMixin
from app.db.models import (
    AIProject,
    AuditLog,
    BuyerNeedDescription,
    Consortium,
    DocumentAsset,
    EnrichmentRecord,
    LumiJob,
    Membership,
    Organization,
    PilotMatch,
    ProductCard,
    ReferenceCard,
    User,
)

# ---------------------------------------------------------------------------
# AC-1: All 13 models importable with correct __tablename__
# ---------------------------------------------------------------------------

_ALL_MODELS_AND_TABLES = [
    (AIProject, "ai_projects"),
    (AuditLog, "audit_logs"),
    (BuyerNeedDescription, "buyer_need_descriptions"),
    (Consortium, "consortia"),
    (DocumentAsset, "document_assets"),
    (EnrichmentRecord, "enrichment_records"),
    (LumiJob, "lumi_jobs"),
    (Membership, "memberships"),
    (Organization, "organizations"),
    (PilotMatch, "pilot_matches"),
    (ProductCard, "product_cards"),
    (ReferenceCard, "reference_cards"),
    (User, "users"),
]


def test_ac1_all_13_models_importable() -> None:
    """AC-1: all 13 models must be importable from app.db.models."""
    import app.db.models as models_pkg

    expected_names = [
        "AIProject", "AuditLog", "BuyerNeedDescription", "Consortium",
        "DocumentAsset", "EnrichmentRecord", "LumiJob", "Membership",
        "Organization", "PilotMatch", "ProductCard", "ReferenceCard", "User",
    ]
    for name in expected_names:
        # AC-1: expect each model importable
        assert hasattr(models_pkg, name), f"{name} not found in app.db.models"


@pytest.mark.parametrize(
    "model_cls,expected_tablename",
    _ALL_MODELS_AND_TABLES,
    ids=[m[0].__name__ for m in _ALL_MODELS_AND_TABLES],
)
def test_ac1_correct_tablename(model_cls: type, expected_tablename: str) -> None:
    """AC-1: each model must have the correct __tablename__."""
    # AC-1: expect correct tablename
    assert model_cls.__tablename__ == expected_tablename


# ---------------------------------------------------------------------------
# AC-2: EntityMetadataMixin models have required columns
# ---------------------------------------------------------------------------

_ENTITY_METADATA_MODELS = [
    User, Membership, BuyerNeedDescription, ProductCard, ReferenceCard,
    PilotMatch, Consortium, AIProject, LumiJob, DocumentAsset, EnrichmentRecord,
]

_ENTITY_METADATA_COLUMNS = {
    "id", "created_at", "updated_at", "deleted_at",
    "organization_id", "visibility", "created_by", "updated_by",
}


@pytest.mark.parametrize(
    "model_cls",
    _ENTITY_METADATA_MODELS,
    ids=[m.__name__ for m in _ENTITY_METADATA_MODELS],
)
def test_ac2_entity_metadata_mixin_columns(model_cls: type) -> None:
    """AC-2: models with EntityMetadataMixin must have all standard columns."""
    # AC-2: expect EntityMetadataMixin in MRO
    assert EntityMetadataMixin in model_cls.__mro__
    col_names = {c.name for c in model_cls.__table__.columns}
    missing = _ENTITY_METADATA_COLUMNS - col_names
    # AC-2: expect all metadata columns present
    assert not missing, f"{model_cls.__name__} missing columns: {missing}"


# ---------------------------------------------------------------------------
# AC-3: Organization does NOT inherit EntityMetadataMixin but has equivalent columns
# ---------------------------------------------------------------------------


def test_ac3_organization_no_entity_metadata_mixin() -> None:
    """AC-3: Organization must NOT inherit EntityMetadataMixin."""
    # AC-3: expect Organization does NOT have EntityMetadataMixin in MRO
    assert EntityMetadataMixin not in Organization.__mro__


def test_ac3_organization_has_equivalent_columns() -> None:
    """AC-3: Organization must have equivalent columns without organization_id FK."""
    col_names = {c.name for c in Organization.__table__.columns}
    expected = {"id", "created_at", "updated_at", "deleted_at", "created_by", "updated_by", "visibility"}
    missing = expected - col_names
    # AC-3: expect all equivalent columns present
    assert not missing, f"Organization missing columns: {missing}"
    # AC-3: expect NO organization_id column
    assert "organization_id" not in col_names


# ---------------------------------------------------------------------------
# AC-4: AuditLog does NOT have deleted_at or updated_at (append-only)
# ---------------------------------------------------------------------------


def test_ac4_audit_log_no_deleted_at() -> None:
    """AC-4: AuditLog must NOT have deleted_at (append-only, immutable)."""
    col_names = {c.name for c in AuditLog.__table__.columns}
    # AC-4: expect no deleted_at
    assert "deleted_at" not in col_names


def test_ac4_audit_log_no_updated_at() -> None:
    """AC-4: AuditLog must NOT have updated_at (append-only, immutable)."""
    col_names = {c.name for c in AuditLog.__table__.columns}
    # AC-4: expect no updated_at
    assert "updated_at" not in col_names


# ---------------------------------------------------------------------------
# AC-5: All UUIDv7 id columns have a Python-side default
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_cls",
    [m[0] for m in _ALL_MODELS_AND_TABLES],
    ids=[m[0].__name__ for m in _ALL_MODELS_AND_TABLES],
)
def test_ac5_uuid7_id_has_default(model_cls: type) -> None:
    """AC-5: all id columns must have a Python-side default producing UUIDv7."""
    col = model_cls.__table__.columns["id"]
    # AC-5: expect default is set and callable
    assert col.default is not None, f"{model_cls.__name__}.id has no default"
    assert col.default.is_callable, f"{model_cls.__name__}.id default is not callable"
    # Invoke the default and verify it produces a UUIDv7
    result = col.default.arg(None)  # type: ignore[misc]
    assert isinstance(result, uuid.UUID), f"{model_cls.__name__}.id default did not produce UUID"
    assert result.version == 7, f"{model_cls.__name__}.id default did not produce UUIDv7"


# ---------------------------------------------------------------------------
# AC-6: All DateTime columns use timezone=True
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_cls",
    [m[0] for m in _ALL_MODELS_AND_TABLES],
    ids=[m[0].__name__ for m in _ALL_MODELS_AND_TABLES],
)
def test_ac6_datetime_columns_have_timezone(model_cls: type) -> None:
    """AC-6: all DateTime columns must use timezone=True."""
    for col in model_cls.__table__.columns:
        if isinstance(col.type, DateTime):
            # AC-6: expect timezone=True on every DateTime column
            assert col.type.timezone is True, (
                f"{model_cls.__name__}.{col.name} uses DateTime without timezone=True"
            )


# ---------------------------------------------------------------------------
# AC-7: State machine status columns use PostgreSQL ENUM types
# ---------------------------------------------------------------------------

_STATUS_ENUM_MODELS = [
    (BuyerNeedDescription, "status"),
    (ProductCard, "status"),
    (PilotMatch, "status"),
    (Consortium, "status"),
    (User, "status"),
    (Membership, "role"),
    (Membership, "status"),
]


@pytest.mark.parametrize(
    "model_cls,col_name",
    _STATUS_ENUM_MODELS,
    ids=[f"{m[0].__name__}.{m[1]}" for m in _STATUS_ENUM_MODELS],
)
def test_ac7_status_columns_use_enum(model_cls: type, col_name: str) -> None:
    """AC-7: state machine status columns must use PostgreSQL ENUM types."""
    col = model_cls.__table__.columns[col_name]
    # AC-7: expect Enum type (not plain String)
    assert isinstance(col.type, Enum), (
        f"{model_cls.__name__}.{col_name} uses {type(col.type).__name__} instead of Enum"
    )


# ---------------------------------------------------------------------------
# AC-8: JSONB columns exist on expected models
# ---------------------------------------------------------------------------

_JSONB_EXPECTATIONS: list[tuple[type, list[str]]] = [
    (BuyerNeedDescription, [
        "specific_requirements", "success_criteria", "technical_constraints",
        "timeline", "budget_range", "vendor_priorities",
    ]),
    (ProductCard, ["demo", "price_range", "certifications", "readiness", "pilot_settings"]),
    (PilotMatch, ["signals"]),
    (Consortium, ["participants", "candidate_organizations", "match_summary"]),
    (AIProject, ["technologies", "funding_sources", "impact_metrics"]),
    (LumiJob, ["input", "filters", "results", "diagnostics"]),
    (AuditLog, ["before_state", "after_state"]),
    (Organization, ["location", "capabilities"]),
]


@pytest.mark.parametrize(
    "model_cls,jsonb_cols",
    _JSONB_EXPECTATIONS,
    ids=[m[0].__name__ for m in _JSONB_EXPECTATIONS],
)
def test_ac8_jsonb_columns_exist(model_cls: type, jsonb_cols: list[str]) -> None:
    """AC-8: expected JSONB columns must exist and use JSONB type."""
    for col_name in jsonb_cols:
        col = model_cls.__table__.columns[col_name]
        # AC-8: expect JSONB type
        assert isinstance(col.type, JSONB), (
            f"{model_cls.__name__}.{col_name} is {type(col.type).__name__}, expected JSONB"
        )
