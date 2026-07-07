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
