"""Custom types, UUIDv7 helper, and PostgreSQL enum type definitions."""

from __future__ import annotations

import uuid
from enum import StrEnum

import uuid_utils
from sqlalchemy import Enum


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 value as a stdlib uuid.UUID.

    Uses uuid_utils for the actual UUIDv7 generation (time-ordered),
    then converts to stdlib uuid.UUID which SQLAlchemy's Uuid type expects.
    """
    return uuid.UUID(str(uuid_utils.uuid7()))


# ---------------------------------------------------------------------------
# State machine enums
# ---------------------------------------------------------------------------


class NeedStatus(StrEnum):
    Draft = "Draft"
    ConversationStarted = "ConversationStarted"
    StructuredDraft = "StructuredDraft"
    NeedsUserReview = "NeedsUserReview"
    ReadyForMatching = "ReadyForMatching"
    MatchmakingRequested = "MatchmakingRequested"
    MatchResultsAvailable = "MatchResultsAvailable"
    Completed = "Completed"
    Archived = "Archived"


class ProductStatus(StrEnum):
    Draft = "Draft"
    AIParsed = "AIParsed"
    VendorReview = "VendorReview"
    ReadyForAdminReview = "ReadyForAdminReview"
    Published = "Published"
    Archived = "Archived"


class PilotMatchStatus(StrEnum):
    Candidate = "Candidate"
    ShownToDemand = "ShownToDemand"
    AcceptedByDemand = "AcceptedByDemand"
    ContactShared = "ContactShared"
    SupplyNotified = "SupplyNotified"
    ClosedPlatformRole = "ClosedPlatformRole"
    RejectedByDemand = "RejectedByDemand"
    SuppressedCapacityFull = "SuppressedCapacityFull"


class ConsortiumStatus(StrEnum):
    ProblemStatementComplete = "ProblemStatementComplete"
    ReadinessCheck = "ReadinessCheck"
    CandidateSearchRequested = "CandidateSearchRequested"
    LumiCandidatesReceived = "LumiCandidatesReceived"
    AdminReview = "AdminReview"
    InvitationsSent = "InvitationsSent"
    InterestedOrganizations = "InterestedOrganizations"
    QuestionSetCompleted = "QuestionSetCompleted"
    ConsortiumProposal = "ConsortiumProposal"
    FinalCompositionConfirmed = "FinalCompositionConfirmed"
    ContactShared = "ContactShared"
    ClosedPlatformRole = "ClosedPlatformRole"


class OrganizationType(StrEnum):
    University = "University"
    ResearchInstitute = "ResearchInstitute"
    LargeEnterprise = "LargeEnterprise"
    SME = "SME"
    Startup = "Startup"
    PublicSector = "PublicSector"
    Municipality = "Municipality"
    Hospital = "Hospital"
    NGO = "NGO"
    TradeAssociation = "TradeAssociation"
    Accelerator = "Accelerator"
    InvestmentFund = "InvestmentFund"
    MediaOrganization = "MediaOrganization"
    InternationalOrganization = "InternationalOrganization"
    Other = "Other"


class MembershipRole(StrEnum):
    SuperAdmin = "SuperAdmin"
    Admin = "Admin"
    AOCAdmin = "AOCAdmin"
    AOCViewer = "AOCViewer"
    OrganizationAdmin = "OrganizationAdmin"
    OrganizationUser = "OrganizationUser"
    Viewer = "Viewer"
    VendorManager = "VendorManager"
    DemandManager = "DemandManager"
    ConsortiumParticipant = "ConsortiumParticipant"


class MembershipStatus(StrEnum):
    Active = "Active"
    Invited = "Invited"
    Suspended = "Suspended"
    Revoked = "Revoked"


class UserStatus(StrEnum):
    Active = "Active"
    Inactive = "Inactive"
    PendingVerification = "PendingVerification"
    Suspended = "Suspended"


class DataQualityStatus(StrEnum):
    Unverified = "Unverified"
    Verified = "Verified"
    Flagged = "Flagged"
    Enriched = "Enriched"


class Visibility(StrEnum):
    Public = "Public"
    Private = "Private"
    Internal = "Internal"


# ---------------------------------------------------------------------------
# SQLAlchemy PostgreSQL ENUM type objects
# (schema='public', create_type=True so Alembic emits CREATE TYPE)
# ---------------------------------------------------------------------------

NeedStatusType = Enum(
    NeedStatus,
    name="needstatus",
    schema="public",
    create_type=True,
)

ProductStatusType = Enum(
    ProductStatus,
    name="productstatus",
    schema="public",
    create_type=True,
)

PilotMatchStatusType = Enum(
    PilotMatchStatus,
    name="pilotmatchstatus",
    schema="public",
    create_type=True,
)

ConsortiumStatusType = Enum(
    ConsortiumStatus,
    name="consortiumstatus",
    schema="public",
    create_type=True,
)

OrganizationTypeType = Enum(
    OrganizationType,
    name="organizationtype",
    schema="public",
    create_type=True,
)

MembershipRoleType = Enum(
    MembershipRole,
    name="membershiprole",
    schema="public",
    create_type=True,
)

MembershipStatusType = Enum(
    MembershipStatus,
    name="membershipstatus",
    schema="public",
    create_type=True,
)

UserStatusType = Enum(
    UserStatus,
    name="userstatus",
    schema="public",
    create_type=True,
)

DataQualityStatusType = Enum(
    DataQualityStatus,
    name="dataqualitystatus",
    schema="public",
    create_type=True,
)

VisibilityType = Enum(
    Visibility,
    name="visibility",
    schema="public",
    create_type=True,
)
