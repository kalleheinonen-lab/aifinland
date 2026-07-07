"""Tests for remaining entity models (Consortium, AIProject, LumiJob, AuditLog, DocumentAsset, EnrichmentRecord).

# kills: missing column, wrong FK target, wrong table name, wrong nullable setting,
#        wrong default value, missing JSONB type, wrong enum type on status column,
#        AuditLog having deleted_at/updated_at (immutability violation),
#        wrong organization_id nullability per model
"""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
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
from app.db.types import uuid7

# ---------------------------------------------------------------------------
# AC-1: All 13 models importable and have correct tablenames
# ---------------------------------------------------------------------------


def test_ac1_all_13_models_importable() -> None:
    """AC-1: All 13 models must be importable from app.db.models."""
    import app.db.models as models_pkg

    expected_models = [
        "AIProject",
        "AuditLog",
        "BuyerNeedDescription",
        "Consortium",
        "DocumentAsset",
        "EnrichmentRecord",
        "LumiJob",
        "Membership",
        "Organization",
        "PilotMatch",
        "ProductCard",
        "ReferenceCard",
        "User",
    ]
    for name in expected_models:
        # AC-1: expect each model importable
        assert hasattr(models_pkg, name), f"{name} not found in app.db.models"


def test_ac1_all_tablenames() -> None:
    """AC-1: All models must have correct __tablename__."""
    expected = {
        AIProject: "ai_projects",
        AuditLog: "audit_logs",
        BuyerNeedDescription: "buyer_need_descriptions",
        Consortium: "consortia",
        DocumentAsset: "document_assets",
        EnrichmentRecord: "enrichment_records",
        LumiJob: "lumi_jobs",
        Membership: "memberships",
        Organization: "organizations",
        PilotMatch: "pilot_matches",
        ProductCard: "product_cards",
        ReferenceCard: "reference_cards",
        User: "users",
    }
    for model_cls, tablename in expected.items():
        # AC-1: expect correct tablename
        assert model_cls.__tablename__ == tablename, (
            f"{model_cls.__name__}.__tablename__ = {model_cls.__tablename__!r}, expected {tablename!r}"
        )


# ---------------------------------------------------------------------------
# AC-2: Consortium model structure
# ---------------------------------------------------------------------------


def test_ac2_consortium_inherits_entity_metadata() -> None:
    """AC-2: Consortium must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in Consortium.__mro__


def test_ac2_consortium_organization_id_nullable() -> None:
    """AC-2: Consortium.organization_id must be nullable (platform-scoped)."""
    col = Consortium.__table__.columns["organization_id"]
    # AC-2: expect nullable=True
    assert col.nullable is True


def test_ac2_consortium_columns_present() -> None:
    """AC-2: Consortium must have all required columns."""
    col_keys = {c.key for c in Consortium.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "problem_statement_id",
        "status",
        "participants",
        "candidate_organizations",
        "question_set_version",
        "match_summary",
        "finalized_by",
        "finalized_at",
    }
    # AC-2: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac2_consortium_problem_statement_id_fk() -> None:
    """AC-2: Consortium.problem_statement_id must FK to buyer_need_descriptions.id."""
    col = Consortium.__table__.columns["problem_statement_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-2: expect FK to buyer_need_descriptions.id
    assert "buyer_need_descriptions.id" in fk_targets
    assert col.nullable is True


def test_ac2_consortium_status_default() -> None:
    """AC-2: Consortium.status must default to 'ProblemStatementComplete'."""
    col = Consortium.__table__.columns["status"]
    # AC-2: expect default='ProblemStatementComplete'
    assert col.default is not None
    assert col.default.arg == "ProblemStatementComplete"  # type: ignore[union-attr]
    assert col.nullable is False


def test_ac2_consortium_jsonb_columns() -> None:
    """AC-2: JSONB columns must use JSONB type."""
    jsonb_cols = ["participants", "candidate_organizations", "match_summary"]
    for col_name in jsonb_cols:
        col = Consortium.__table__.columns[col_name]
        # AC-2: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


def test_ac2_consortium_question_set_version_default() -> None:
    """AC-2: Consortium.question_set_version must default to 'v1.0'."""
    col = Consortium.__table__.columns["question_set_version"]
    # AC-2: expect default='v1.0'
    assert col.default is not None
    assert col.default.arg == "v1.0"  # type: ignore[union-attr]


def test_ac2_consortium_finalized_by_fk() -> None:
    """AC-2: Consortium.finalized_by must FK to users.id."""
    col = Consortium.__table__.columns["finalized_by"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-2: expect FK to users.id
    assert "users.id" in fk_targets
    assert col.nullable is True


def test_ac2_consortium_finalized_at_timezone() -> None:
    """AC-2: Consortium.finalized_at must use DateTime(timezone=True)."""
    col = Consortium.__table__.columns["finalized_at"]
    # AC-2: expect timezone=True
    assert col.type.timezone is True
    assert col.nullable is True


# ---------------------------------------------------------------------------
# AC-3: AIProject model structure
# ---------------------------------------------------------------------------


def test_ac3_ai_project_inherits_entity_metadata() -> None:
    """AC-3: AIProject must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in AIProject.__mro__


def test_ac3_ai_project_organization_id_not_nullable() -> None:
    """AC-3: AIProject.organization_id must NOT be nullable."""
    col = AIProject.__table__.columns["organization_id"]
    # AC-3: expect nullable=False
    assert col.nullable is False


def test_ac3_ai_project_columns_present() -> None:
    """AC-3: AIProject must have all required columns."""
    col_keys = {c.key for c in AIProject.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "name",
        "sector",
        "region",
        "maturity_stage",
        "technologies",
        "funding_sources",
        "public_description",
        "impact_metrics",
    }
    # AC-3: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac3_ai_project_name_not_nullable() -> None:
    """AC-3: AIProject.name must NOT be nullable."""
    col = AIProject.__table__.columns["name"]
    # AC-3: expect nullable=False
    assert col.nullable is False


def test_ac3_ai_project_jsonb_columns() -> None:
    """AC-3: JSONB columns must use JSONB type."""
    jsonb_cols = ["technologies", "funding_sources", "impact_metrics"]
    for col_name in jsonb_cols:
        col = AIProject.__table__.columns[col_name]
        # AC-3: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


def test_ac3_ai_project_nullable_string_columns() -> None:
    """AC-3: Optional string columns must be nullable."""
    for col_name in ("sector", "region", "maturity_stage"):
        col = AIProject.__table__.columns[col_name]
        # AC-3: expect nullable=True
        assert col.nullable is True, f"{col_name} must be nullable"


def test_ac3_ai_project_organization_id_fk() -> None:
    """AC-3: AIProject.organization_id must FK to organizations.id."""
    col = AIProject.__table__.columns["organization_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-3: expect FK to organizations.id
    assert "organizations.id" in fk_targets


# ---------------------------------------------------------------------------
# AC-4: LumiJob model structure
# ---------------------------------------------------------------------------


def test_ac4_lumi_job_inherits_entity_metadata() -> None:
    """AC-4: LumiJob must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in LumiJob.__mro__


def test_ac4_lumi_job_columns_present() -> None:
    """AC-4: LumiJob must have all required columns."""
    col_keys = {c.key for c in LumiJob.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "request_id",
        "use_case",
        "caller_id",
        "input",
        "filters",
        "status",
        "model_version",
        "results",
        "diagnostics",
    }
    # AC-4: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac4_lumi_job_request_id_unique_not_null() -> None:
    """AC-4: LumiJob.request_id must be unique and not null."""
    col = LumiJob.__table__.columns["request_id"]
    # AC-4: expect unique and not nullable
    assert col.unique is True
    assert col.nullable is False


def test_ac4_lumi_job_use_case_not_nullable() -> None:
    """AC-4: LumiJob.use_case must NOT be nullable."""
    col = LumiJob.__table__.columns["use_case"]
    # AC-4: expect nullable=False
    assert col.nullable is False


def test_ac4_lumi_job_caller_id_fk() -> None:
    """AC-4: LumiJob.caller_id must FK to users.id and be NOT NULL."""
    col = LumiJob.__table__.columns["caller_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-4: expect FK to users.id
    assert "users.id" in fk_targets
    assert col.nullable is False


def test_ac4_lumi_job_input_not_nullable() -> None:
    """AC-4: LumiJob.input must be JSONB and NOT NULL."""
    col = LumiJob.__table__.columns["input"]
    # AC-4: expect JSONB and not nullable
    assert isinstance(col.type, JSONB)
    assert col.nullable is False


def test_ac4_lumi_job_status_default() -> None:
    """AC-4: LumiJob.status must default to 'pending'."""
    col = LumiJob.__table__.columns["status"]
    # AC-4: expect default='pending'
    assert col.default is not None
    assert col.default.arg == "pending"  # type: ignore[union-attr]
    assert col.nullable is False


def test_ac4_lumi_job_jsonb_nullable_columns() -> None:
    """AC-4: Optional JSONB columns must be nullable."""
    for col_name in ("filters", "results", "diagnostics"):
        col = LumiJob.__table__.columns[col_name]
        # AC-4: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


# ---------------------------------------------------------------------------
# AC-5: AuditLog model structure (append-only, no soft delete)
# ---------------------------------------------------------------------------


def test_ac5_audit_log_does_not_inherit_entity_metadata() -> None:
    """AC-5: AuditLog must NOT inherit EntityMetadataMixin (append-only)."""
    assert EntityMetadataMixin not in AuditLog.__mro__


def test_ac5_audit_log_inherits_base() -> None:
    """AC-5: AuditLog must inherit Base."""
    assert Base in AuditLog.__mro__


def test_ac5_audit_log_no_deleted_at() -> None:
    """AC-5: AuditLog must NOT have deleted_at column (immutable)."""
    col_keys = {c.key for c in AuditLog.__table__.columns}
    # AC-5: expect no deleted_at
    assert "deleted_at" not in col_keys


def test_ac5_audit_log_no_updated_at() -> None:
    """AC-5: AuditLog must NOT have updated_at column (immutable)."""
    col_keys = {c.key for c in AuditLog.__table__.columns}
    # AC-5: expect no updated_at
    assert "updated_at" not in col_keys


def test_ac5_audit_log_columns_present() -> None:
    """AC-5: AuditLog must have all required columns."""
    col_keys = {c.key for c in AuditLog.__table__.columns}
    expected = {
        "id",
        "timestamp",
        "actor_user_id",
        "actor_ip",
        "organization_id",
        "action_type",
        "entity_type",
        "entity_id",
        "before_state",
        "after_state",
        "result",
        "session_id",
    }
    # AC-5: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac5_audit_log_id_primary_key_uuid7() -> None:
    """AC-5: AuditLog.id must be UUID PK with uuid7 default."""
    col = AuditLog.__table__.columns["id"]
    # AC-5: expect primary key with uuid7 default
    assert col.primary_key is True
    assert col.default is not None
    assert col.default.is_callable
    result = col.default.arg(None)  # type: ignore[misc]
    assert isinstance(result, uuid.UUID)
    assert result.version == 7


def test_ac5_audit_log_timestamp_server_default() -> None:
    """AC-5: AuditLog.timestamp must have server_default=func.now()."""
    col = AuditLog.__table__.columns["timestamp"]
    # AC-5: expect server_default set and timezone=True
    assert col.server_default is not None
    assert col.type.timezone is True
    assert col.nullable is False


def test_ac5_audit_log_actor_user_id_fk() -> None:
    """AC-5: AuditLog.actor_user_id must FK to users.id and be nullable."""
    col = AuditLog.__table__.columns["actor_user_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-5: expect FK to users.id
    assert "users.id" in fk_targets
    assert col.nullable is True


def test_ac5_audit_log_organization_id_fk_nullable() -> None:
    """AC-5: AuditLog.organization_id must FK to organizations.id and be nullable."""
    col = AuditLog.__table__.columns["organization_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-5: expect FK to organizations.id
    assert "organizations.id" in fk_targets
    assert col.nullable is True


def test_ac5_audit_log_action_type_not_nullable() -> None:
    """AC-5: AuditLog.action_type must NOT be nullable."""
    col = AuditLog.__table__.columns["action_type"]
    # AC-5: expect nullable=False
    assert col.nullable is False


def test_ac5_audit_log_entity_type_not_nullable() -> None:
    """AC-5: AuditLog.entity_type must NOT be nullable."""
    col = AuditLog.__table__.columns["entity_type"]
    # AC-5: expect nullable=False
    assert col.nullable is False


def test_ac5_audit_log_entity_id_not_nullable() -> None:
    """AC-5: AuditLog.entity_id must NOT be nullable."""
    col = AuditLog.__table__.columns["entity_id"]
    # AC-5: expect nullable=False
    assert col.nullable is False


def test_ac5_audit_log_jsonb_columns() -> None:
    """AC-5: before_state and after_state must be JSONB and nullable."""
    for col_name in ("before_state", "after_state"):
        col = AuditLog.__table__.columns[col_name]
        # AC-5: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


# ---------------------------------------------------------------------------
# AC-6: DocumentAsset model structure
# ---------------------------------------------------------------------------


def test_ac6_document_asset_inherits_entity_metadata() -> None:
    """AC-6: DocumentAsset must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in DocumentAsset.__mro__


def test_ac6_document_asset_organization_id_not_nullable() -> None:
    """AC-6: DocumentAsset.organization_id must NOT be nullable."""
    col = DocumentAsset.__table__.columns["organization_id"]
    # AC-6: expect nullable=False
    assert col.nullable is False


def test_ac6_document_asset_columns_present() -> None:
    """AC-6: DocumentAsset must have all required columns."""
    col_keys = {c.key for c in DocumentAsset.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "object_storage_key",
        "filename",
        "mime_type",
        "size",
        "checksum",
        "uploader_user_id",
        "extraction_status",
        "extracted_text_ref",
    }
    # AC-6: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac6_document_asset_not_nullable_columns() -> None:
    """AC-6: Required columns must NOT be nullable."""
    for col_name in ("object_storage_key", "filename", "mime_type", "size"):
        col = DocumentAsset.__table__.columns[col_name]
        # AC-6: expect nullable=False
        assert col.nullable is False, f"{col_name} must not be nullable"


def test_ac6_document_asset_uploader_user_id_fk() -> None:
    """AC-6: DocumentAsset.uploader_user_id must FK to users.id and be NOT NULL."""
    col = DocumentAsset.__table__.columns["uploader_user_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-6: expect FK to users.id
    assert "users.id" in fk_targets
    assert col.nullable is False


def test_ac6_document_asset_size_is_biginteger() -> None:
    """AC-6: DocumentAsset.size must use BigInteger type."""
    from sqlalchemy import BigInteger

    col = DocumentAsset.__table__.columns["size"]
    # AC-6: expect BigInteger type
    assert isinstance(col.type, BigInteger)


def test_ac6_document_asset_nullable_columns() -> None:
    """AC-6: Optional columns must be nullable."""
    for col_name in ("checksum", "extraction_status", "extracted_text_ref"):
        col = DocumentAsset.__table__.columns[col_name]
        # AC-6: expect nullable=True
        assert col.nullable is True, f"{col_name} must be nullable"


# ---------------------------------------------------------------------------
# AC-7: EnrichmentRecord model structure
# ---------------------------------------------------------------------------


def test_ac7_enrichment_record_inherits_entity_metadata() -> None:
    """AC-7: EnrichmentRecord must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in EnrichmentRecord.__mro__


def test_ac7_enrichment_record_organization_id_not_nullable() -> None:
    """AC-7: EnrichmentRecord.organization_id must NOT be nullable."""
    col = EnrichmentRecord.__table__.columns["organization_id"]
    # AC-7: expect nullable=False
    assert col.nullable is False


def test_ac7_enrichment_record_columns_present() -> None:
    """AC-7: EnrichmentRecord must have all required columns."""
    col_keys = {c.key for c in EnrichmentRecord.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "field_path",
        "source_url",
        "extraction_timestamp",
        "confidence",
        "original_text",
        "normalized_value",
        "human_validation_status",
    }
    # AC-7: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac7_enrichment_record_field_path_not_nullable() -> None:
    """AC-7: EnrichmentRecord.field_path must NOT be nullable."""
    col = EnrichmentRecord.__table__.columns["field_path"]
    # AC-7: expect nullable=False
    assert col.nullable is False


def test_ac7_enrichment_record_extraction_timestamp_timezone() -> None:
    """AC-7: EnrichmentRecord.extraction_timestamp must use DateTime(timezone=True)."""
    col = EnrichmentRecord.__table__.columns["extraction_timestamp"]
    # AC-7: expect timezone=True and nullable
    assert col.type.timezone is True
    assert col.nullable is True


def test_ac7_enrichment_record_confidence_nullable() -> None:
    """AC-7: EnrichmentRecord.confidence must be nullable Float."""
    col = EnrichmentRecord.__table__.columns["confidence"]
    # AC-7: expect nullable=True
    assert col.nullable is True


def test_ac7_enrichment_record_human_validation_status_default() -> None:
    """AC-7: EnrichmentRecord.human_validation_status must default to 'pending'."""
    col = EnrichmentRecord.__table__.columns["human_validation_status"]
    # AC-7: expect default='pending' and nullable
    assert col.default is not None
    assert col.default.arg == "pending"  # type: ignore[union-attr]
    assert col.nullable is True


def test_ac7_enrichment_record_text_columns_nullable() -> None:
    """AC-7: Text columns must be nullable."""
    for col_name in ("original_text", "normalized_value"):
        col = EnrichmentRecord.__table__.columns[col_name]
        # AC-7: expect nullable=True
        assert col.nullable is True, f"{col_name} must be nullable"


# ---------------------------------------------------------------------------
# AC-1 (cont): Instantiation tests
# ---------------------------------------------------------------------------


def test_ac2_consortium_instantiation() -> None:
    """AC-2: Consortium can be instantiated without organization_id."""
    c = Consortium()
    # AC-2: expect no error, organization_id defaults to None
    assert c.organization_id is None


def test_ac3_ai_project_instantiation() -> None:
    """AC-3: AIProject can be instantiated with required fields."""
    org_id = uuid7()
    proj = AIProject(organization_id=org_id, name="Test AI Project")
    # AC-3: expect explicit fields set
    assert proj.organization_id == org_id
    assert proj.name == "Test AI Project"


def test_ac4_lumi_job_instantiation() -> None:
    """AC-4: LumiJob can be instantiated with required fields."""
    req_id = uuid7()
    caller = uuid7()
    job = LumiJob(request_id=req_id, use_case="matching", caller_id=caller, input={"query": "test"})
    # AC-4: expect explicit fields set
    assert job.request_id == req_id
    assert job.use_case == "matching"
    assert job.caller_id == caller
    assert job.input == {"query": "test"}


def test_ac5_audit_log_instantiation() -> None:
    """AC-5: AuditLog can be instantiated with required fields."""
    entity_id = uuid7()
    log = AuditLog(action_type="create", entity_type="organization", entity_id=entity_id)
    # AC-5: expect explicit fields set
    assert log.action_type == "create"
    assert log.entity_type == "organization"
    assert log.entity_id == entity_id


def test_ac6_document_asset_instantiation() -> None:
    """AC-6: DocumentAsset can be instantiated with required fields."""
    org_id = uuid7()
    user_id = uuid7()
    doc = DocumentAsset(
        organization_id=org_id,
        object_storage_key="docs/test.pdf",
        filename="test.pdf",
        mime_type="application/pdf",
        size=1024,
        uploader_user_id=user_id,
    )
    # AC-6: expect explicit fields set
    assert doc.organization_id == org_id
    assert doc.filename == "test.pdf"
    assert doc.size == 1024


def test_ac7_enrichment_record_instantiation() -> None:
    """AC-7: EnrichmentRecord can be instantiated with required fields."""
    org_id = uuid7()
    rec = EnrichmentRecord(organization_id=org_id, field_path="company.name")
    # AC-7: expect explicit fields set
    assert rec.organization_id == org_id
    assert rec.field_path == "company.name"
