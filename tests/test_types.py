"""Tests for db types, enums, and EntityMetadataMixin column naming.

# kills: wrong enum member name, missing enum member, camelCase column key
"""

from __future__ import annotations

import uuid

from app.db.types import (
    ConsortiumStatus,
    DataQualityStatus,
    MembershipRole,
    MembershipStatus,
    NeedStatus,
    OrganizationType,
    PilotMatchStatus,
    ProductStatus,
    UserStatus,
    Visibility,
    uuid7,
)

# ---------------------------------------------------------------------------
# AC-1: uuid7() returns a stdlib uuid.UUID (not uuid_utils.UUID)
# ---------------------------------------------------------------------------


def test_ac1_uuid7_returns_stdlib_uuid() -> None:
    """AC-1: uuid7() must return stdlib uuid.UUID for SQLAlchemy compatibility."""
    result = uuid7()
    # AC-1: expect stdlib uuid.UUID instance
    assert isinstance(result, uuid.UUID)


def test_ac1_uuid7_is_version_7() -> None:
    """AC-1: uuid7() must produce version-7 UUIDs."""
    result = uuid7()
    # AC-1: expect UUID version 7
    assert result.version == 7


def test_ac1_uuid7_unique() -> None:
    """AC-1: successive uuid7() calls must return distinct values."""
    a, b = uuid7(), uuid7()
    # AC-1: expect distinct UUIDs
    assert a != b


# ---------------------------------------------------------------------------
# AC-2: NeedStatus enum values
# ---------------------------------------------------------------------------


def test_ac2_need_status_members() -> None:
    """AC-2: NeedStatus must contain all required state machine values."""
    expected = {
        "Draft",
        "ConversationStarted",
        "StructuredDraft",
        "NeedsUserReview",
        "ReadyForMatching",
        "MatchmakingRequested",
        "MatchResultsAvailable",
        "Completed",
        "Archived",
    }
    # AC-2: expect all 9 members present
    assert {m.value for m in NeedStatus} == expected


# ---------------------------------------------------------------------------
# AC-3: ProductStatus enum values
# ---------------------------------------------------------------------------


def test_ac3_product_status_members() -> None:
    """AC-3: ProductStatus must contain all required state machine values."""
    expected = {"Draft", "AIParsed", "VendorReview", "ReadyForAdminReview", "Published", "Archived"}
    # AC-3: expect all 6 members present
    assert {m.value for m in ProductStatus} == expected


# ---------------------------------------------------------------------------
# AC-4: PilotMatchStatus enum values
# ---------------------------------------------------------------------------


def test_ac4_pilot_match_status_members() -> None:
    """AC-4: PilotMatchStatus must contain all required state machine values."""
    expected = {
        "Candidate",
        "ShownToDemand",
        "AcceptedByDemand",
        "ContactShared",
        "SupplyNotified",
        "ClosedPlatformRole",
        "RejectedByDemand",
        "SuppressedCapacityFull",
    }
    # AC-4: expect all 8 members present
    assert {m.value for m in PilotMatchStatus} == expected


# ---------------------------------------------------------------------------
# AC-5: ConsortiumStatus enum values
# ---------------------------------------------------------------------------


def test_ac5_consortium_status_members() -> None:
    """AC-5: ConsortiumStatus must contain all required state machine values."""
    expected = {
        "ProblemStatementComplete",
        "ReadinessCheck",
        "CandidateSearchRequested",
        "LumiCandidatesReceived",
        "AdminReview",
        "InvitationsSent",
        "InterestedOrganizations",
        "QuestionSetCompleted",
        "ConsortiumProposal",
        "FinalCompositionConfirmed",
        "ContactShared",
        "ClosedPlatformRole",
    }
    # AC-5: expect all 12 members present
    assert {m.value for m in ConsortiumStatus} == expected


# ---------------------------------------------------------------------------
# AC-6: OrganizationType enum values (15 types)
# ---------------------------------------------------------------------------


def test_ac6_organization_type_has_15_members() -> None:
    """AC-6: OrganizationType must have exactly 15 members per spec."""
    # AC-6: expect exactly 15 organization types
    assert len(OrganizationType) == 15


def test_ac6_organization_type_members() -> None:
    """AC-6: OrganizationType must contain all specified types."""
    expected = {
        "University",
        "ResearchInstitute",
        "LargeEnterprise",
        "SME",
        "Startup",
        "PublicSector",
        "Municipality",
        "Hospital",
        "NGO",
        "TradeAssociation",
        "Accelerator",
        "InvestmentFund",
        "MediaOrganization",
        "InternationalOrganization",
        "Other",
    }
    # AC-6: expect all 15 members present
    assert {m.value for m in OrganizationType} == expected


# ---------------------------------------------------------------------------
# AC-7: MembershipRole enum values
# ---------------------------------------------------------------------------


def test_ac7_membership_role_members() -> None:
    """AC-7: MembershipRole must contain all required role values."""
    expected = {
        "SuperAdmin",
        "Admin",
        "AOCAdmin",
        "AOCViewer",
        "OrganizationAdmin",
        "OrganizationUser",
        "Viewer",
        "VendorManager",
        "DemandManager",
        "ConsortiumParticipant",
    }
    # AC-7: expect all 10 members present
    assert {m.value for m in MembershipRole} == expected


# ---------------------------------------------------------------------------
# AC-8: Supporting enums exist with expected values
# ---------------------------------------------------------------------------


def test_ac8_membership_status_members() -> None:
    """AC-8: MembershipStatus must contain expected values."""
    assert {m.value for m in MembershipStatus} == {"Active", "Invited", "Suspended", "Revoked"}


def test_ac8_user_status_members() -> None:
    """AC-8: UserStatus must contain expected values."""
    assert {m.value for m in UserStatus} == {"Active", "Inactive", "PendingVerification", "Suspended"}


def test_ac8_data_quality_status_members() -> None:
    """AC-8: DataQualityStatus must contain expected values."""
    assert {m.value for m in DataQualityStatus} == {"Unverified", "Verified", "Flagged", "Enriched"}


def test_ac8_visibility_members() -> None:
    """AC-8: Visibility must contain expected values."""
    assert {m.value for m in Visibility} == {"Public", "Private", "Internal"}


# ---------------------------------------------------------------------------
# AC-9: EntityMetadataMixin column naming (snake_case, not camelCase)
# ---------------------------------------------------------------------------


def test_ac9_entity_metadata_mixin_column_names() -> None:
    """AC-9: EntityMetadataMixin columns must use snake_case names.

    The RLS CI gate inspects __table__.columns for 'organization_id'.
    This test verifies the mixin defines the attribute as 'organization_id',
    not 'organizationId' or any other camelCase variant.
    """
    from app.db.base import Base
    from app.db.mixins import EntityMetadataMixin

    # Build a concrete model to trigger column resolution
    class SampleModel(EntityMetadataMixin, Base):
        __tablename__ = "sample_model_test"

    # AC-9: expect snake_case column keys in __table__.columns
    column_keys = {c.key for c in SampleModel.__table__.columns}

    assert "organization_id" in column_keys, "'organization_id' must be a column key (not 'organizationId')"
    assert "created_at" in column_keys, "'created_at' must be a column key"
    assert "updated_at" in column_keys, "'updated_at' must be a column key"
    assert "created_by" in column_keys, "'created_by' must be a column key"
    assert "updated_by" in column_keys, "'updated_by' must be a column key"
    assert "deleted_at" in column_keys, "'deleted_at' must be a column key"
    assert "visibility" in column_keys, "'visibility' must be a column key"
    assert "id" in column_keys, "'id' must be a column key"

    # Negative: camelCase variants must NOT be present
    assert "organizationId" not in column_keys
    assert "createdAt" not in column_keys
    assert "updatedAt" not in column_keys
    assert "createdBy" not in column_keys
    assert "updatedBy" not in column_keys
    assert "deletedAt" not in column_keys


# ---------------------------------------------------------------------------
# AC-10: RLS CI gate -- every EntityMetadataMixin subclass exposes organization_id
# ---------------------------------------------------------------------------


def test_ac10_all_mixin_subclasses_expose_organization_id() -> None:
    """AC-10: Every registered subclass of EntityMetadataMixin must expose
    'organization_id' in __table__.columns.

    This is the RLS CI gate: the check_rls_coverage script inspects
    __table__.columns for 'organization_id' to determine which tables need
    Row-Level Security policies.  If a model uses EntityMetadataMixin but
    somehow loses the column (e.g. a bad override or rename), the RLS gate
    would silently miss that table.

    # kills: model that overrides organization_id with a differently-named
    #        column, model that removes organization_id entirely, new model
    #        added without the mixin column
    """
    import app.db.models  # noqa: F401  (side-effect: registers all concrete models)
    from app.db.mixins import EntityMetadataMixin

    def _all_subclasses(cls: type) -> list[type]:
        """Recursively collect all subclasses (handles multi-level inheritance)."""
        result: list[type] = []
        for sub in cls.__subclasses__():
            result.append(sub)
            result.extend(_all_subclasses(sub))
        return result

    mixin_subclasses = _all_subclasses(EntityMetadataMixin)

    # Filter to concrete models that have a __table__ attribute (i.e. are
    # fully mapped SQLAlchemy models, not abstract intermediate classes).
    concrete_models = [cls for cls in mixin_subclasses if hasattr(cls, "__table__")]

    # AC-10: there must be at least one concrete model using the mixin
    assert concrete_models, (
        "No concrete SQLAlchemy models found that inherit EntityMetadataMixin. "
        "Ensure app.db.models is imported so all models are registered."
    )

    missing: list[str] = []
    for model in concrete_models:
        column_names = {col.name for col in model.__table__.columns}
        if "organization_id" not in column_names:
            missing.append(
                f"{model.__name__} (table: {model.__table__.name!r}) -- "
                f"columns: {sorted(column_names)}"
            )

    # AC-10: expect 'organization_id' present in every mixin model's table
    assert not missing, (
        "The following EntityMetadataMixin subclasses are missing 'organization_id' "
        "in __table__.columns -- the RLS CI gate would silently skip them:\n"
        + "\n".join(f"  - {m}" for m in missing)
    )


def test_ac9_entity_metadata_mixin_no_duplicate_fk_constraint_names() -> None:
    """AC-9: Two models using EntityMetadataMixin must not produce duplicate FK constraint names.

    The duplicate FK constraint name bug only manifests when a SECOND model uses
    the mixin. Without the %(table_name)s naming convention in Base.metadata, both
    models would register the same FK constraint names (e.g. 'fk_organization_id')
    and fail at DDL time with a duplicate-name error.

    This test verifies that the naming convention fix works correctly by confirming:
    1. Both models can be defined without raising an error.
    2. All FK constraint names across both tables are unique.
    3. Each FK constraint name is scoped to its own table (contains the table name).
    """
    from app.db.base import Base
    from app.db.mixins import EntityMetadataMixin

    # Define two concrete models that both use EntityMetadataMixin.
    # If the naming convention is missing or broken, registering the second
    # model would raise an InvalidRequestError about duplicate constraint names.
    class SampleModel1(EntityMetadataMixin, Base):
        __tablename__ = "sample_model_test_1"

    class SampleModel2(EntityMetadataMixin, Base):
        __tablename__ = "sample_model_test_2"

    # AC-9: collect all FK constraint names from both tables
    def fk_constraint_names(table: object) -> set[str]:
        from sqlalchemy import Table

        assert isinstance(table, Table)
        return {
            fk.constraint.name
            for col in table.columns
            for fk in col.foreign_keys
            if fk.constraint is not None and fk.constraint.name is not None
        }

    names1 = fk_constraint_names(SampleModel1.__table__)
    names2 = fk_constraint_names(SampleModel2.__table__)

    # AC-9: expect no overlap between the two sets of FK constraint names
    overlap = names1 & names2
    assert not overlap, (
        f"Duplicate FK constraint names detected across two mixin models: {overlap!r}. "
        "The naming convention fix (%(table_name)s interpolation) is not working."
    )

    # AC-9: each FK constraint name must reference its own table name
    for name in names1:
        assert "sample_model_test_1" in name, (
            f"FK constraint '{name}' on sample_model_test_1 does not include the table name. "
            "Expected %(table_name)s interpolation."
        )
    for name in names2:
        assert "sample_model_test_2" in name, (
            f"FK constraint '{name}' on sample_model_test_2 does not include the table name. "
            "Expected %(table_name)s interpolation."
        )
