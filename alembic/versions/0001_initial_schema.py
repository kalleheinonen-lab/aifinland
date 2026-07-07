"""Initial schema: all 13 tables with PostgreSQL enums and RLS policies.

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

RLS policy patterns applied:
  Pattern 1 - Self-keyed (organizations):
      id = current_setting('app.current_organization_id')::uuid
  Pattern 2 - Nullable org (users, consortia):
      organization_id = current_setting('app.current_organization_id')::uuid
      OR organization_id IS NULL
  Pattern 3 - Standard tenant-scoped (all other tables):
      organization_id = current_setting('app.current_organization_id')::uuid
  Special - Audit logs (append-only, read-only for app role):
      SELECT only, organization_id = ... OR organization_id IS NULL
      INSERT/UPDATE/DELETE handled by BYPASSRLS migration/service role
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.rls import (
    apply_rls_policy,
    apply_rls_policy_nullable_org,
    apply_rls_policy_self_keyed,
    drop_rls_policy,
)

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables, enum types, indexes, and RLS policies."""

    # -------------------------------------------------------------------------
    # Step 1: Create PostgreSQL ENUM types
    # All enums are in the public schema and match the SQLAlchemy type objects
    # defined in src/app/db/types.py.
    # -------------------------------------------------------------------------

    op.execute(
        """
        CREATE TYPE public.needstatus AS ENUM (
            'Draft',
            'ConversationStarted',
            'StructuredDraft',
            'NeedsUserReview',
            'ReadyForMatching',
            'MatchmakingRequested',
            'MatchResultsAvailable',
            'Completed',
            'Archived'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.productstatus AS ENUM (
            'Draft',
            'AIParsed',
            'VendorReview',
            'ReadyForAdminReview',
            'Published',
            'Archived'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.pilotmatchstatus AS ENUM (
            'Candidate',
            'ShownToDemand',
            'AcceptedByDemand',
            'ContactShared',
            'SupplyNotified',
            'ClosedPlatformRole',
            'RejectedByDemand',
            'SuppressedCapacityFull'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.consortiumstatus AS ENUM (
            'ProblemStatementComplete',
            'ReadinessCheck',
            'CandidateSearchRequested',
            'LumiCandidatesReceived',
            'AdminReview',
            'InvitationsSent',
            'InterestedOrganizations',
            'QuestionSetCompleted',
            'ConsortiumProposal',
            'FinalCompositionConfirmed',
            'ContactShared',
            'ClosedPlatformRole'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.organizationtype AS ENUM (
            'University',
            'ResearchInstitute',
            'LargeEnterprise',
            'SME',
            'Startup',
            'PublicSector',
            'Municipality',
            'Hospital',
            'NGO',
            'TradeAssociation',
            'Accelerator',
            'InvestmentFund',
            'MediaOrganization',
            'InternationalOrganization',
            'Other'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.membershiprole AS ENUM (
            'SuperAdmin',
            'Admin',
            'AOCAdmin',
            'AOCViewer',
            'OrganizationAdmin',
            'OrganizationUser',
            'Viewer',
            'VendorManager',
            'DemandManager',
            'ConsortiumParticipant'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.membershipstatus AS ENUM (
            'Active',
            'Invited',
            'Suspended',
            'Revoked'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.userstatus AS ENUM (
            'Active',
            'Inactive',
            'PendingVerification',
            'Suspended'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.dataqualitystatus AS ENUM (
            'Unverified',
            'Verified',
            'Flagged',
            'Enriched'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE public.visibility AS ENUM (
            'Public',
            'Private',
            'Internal'
        )
        """
    )

    # -------------------------------------------------------------------------
    # Step 2: Create tables in FK-dependency order
    # -------------------------------------------------------------------------

    # --- Table 1: organizations ---
    # RLS Pattern 1 (self-keyed): id = current_setting('app.current_organization_id')::uuid
    # Does NOT inherit EntityMetadataMixin -- no self-referential organization_id FK.
    # created_by / updated_by use deferred FKs to users (use_alter=True) to break
    # the chicken-and-egg cycle between organizations and users.
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_organizations_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_organizations_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("business_id", sa.String(), nullable=True, unique=True),
        sa.Column(
            "organization_type",
            sa.Enum(
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
                name="organizationtype",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("location", JSONB(), nullable=True),
        sa.Column("ai_maturity_level", sa.Integer(), nullable=True),
        sa.Column("capabilities", JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.CheckConstraint(
            "ai_maturity_level IS NULL OR (ai_maturity_level >= 1 AND ai_maturity_level <= 5)",
            name="ck_organizations_ai_maturity_level_range",
        ),
    )

    # --- Table 2: users ---
    # RLS Pattern 2 (nullable org): organization_id = ... OR organization_id IS NULL
    # Platform-scoped users (SuperAdmin) have organization_id=NULL and must remain
    # visible to all tenants for authentication and permission lookups.
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_users_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_users_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_users_organization",
            ),
            nullable=True,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "Active",
                "Inactive",
                "PendingVerification",
                "Suspended",
                name="userstatus",
                schema="public",
                create_type=False,
            ),
            nullable=False,
            server_default="Active",
        ),
        sa.Column("preferred_language", sa.String(), nullable=False, server_default="fi"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_secret", sa.String(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "force_password_reset",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # --- Table 3: memberships ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_memberships_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_memberships_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_memberships_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
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
                name="membershiprole",
                schema="public",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "Active",
                "Invited",
                "Suspended",
                "Revoked",
                name="membershipstatus",
                schema="public",
                create_type=False,
            ),
            nullable=False,
            server_default="Active",
        ),
        sa.UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_memberships_user_organization",
        ),
    )

    # --- Table 4: buyer_need_descriptions ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "buyer_need_descriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_buyer_need_descriptions_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_buyer_need_descriptions_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_buyer_need_descriptions_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(), nullable=False, server_default="v1.0"),
        sa.Column(
            "status",
            sa.Enum(
                "Draft",
                "ConversationStarted",
                "StructuredDraft",
                "NeedsUserReview",
                "ReadyForMatching",
                "MatchmakingRequested",
                "MatchResultsAvailable",
                "Completed",
                "Archived",
                name="needstatus",
                schema="public",
                create_type=False,
            ),
            nullable=False,
            server_default="Draft",
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("problem_summary", sa.Text(), nullable=True),
        sa.Column("target_outcome", sa.Text(), nullable=True),
        sa.Column("specific_requirements", JSONB(), nullable=True),
        sa.Column("success_criteria", JSONB(), nullable=True),
        sa.Column("technical_constraints", JSONB(), nullable=True),
        sa.Column("timeline", JSONB(), nullable=True),
        sa.Column("budget_range", JSONB(), nullable=True),
        sa.Column("vendor_priorities", JSONB(), nullable=True),
        sa.Column("readiness_score", sa.Float(), nullable=True),
        sa.Column("source_conversation_id", UUID(as_uuid=True), nullable=True),
    )

    # --- Table 5: product_cards ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "product_cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_product_cards_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_product_cards_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_product_cards_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(), nullable=False, server_default="v1.0"),
        sa.Column(
            "status",
            sa.Enum(
                "Draft",
                "AIParsed",
                "VendorReview",
                "ReadyForAdminReview",
                "Published",
                "Archived",
                name="productstatus",
                schema="public",
                create_type=False,
            ),
            nullable=False,
            server_default="Draft",
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("product_version", sa.String(), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("demo", JSONB(), nullable=True),
        sa.Column("pricing_model", sa.String(), nullable=True),
        sa.Column("price_range", JSONB(), nullable=True),
        sa.Column("hosting_location", sa.String(), nullable=True),
        sa.Column("certifications", JSONB(), nullable=True),
        sa.Column("readiness", JSONB(), nullable=True),
        sa.Column("implementation_time", sa.String(), nullable=True),
        sa.Column("pilot_settings", JSONB(), nullable=True),
    )

    # --- Table 6: reference_cards ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "reference_cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_reference_cards_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_reference_cards_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_reference_cards_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(), nullable=False, server_default="v1.0"),
        sa.Column("reference_type", sa.String(), nullable=False, server_default="anonymous"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("customer_industry", sa.String(), nullable=True),
        sa.Column("customer_size", sa.String(), nullable=True),
        sa.Column("measurable_result", sa.Text(), nullable=True),
        sa.Column("timeline", JSONB(), nullable=True),
        sa.Column("technologies_used", JSONB(), nullable=True),
        sa.Column("provider_role", sa.Text(), nullable=True),
        sa.Column("starting_situation_and_problem", sa.Text(), nullable=True),
        sa.Column("solution_approach", sa.Text(), nullable=True),
        sa.Column("ai_extraction_confidence", sa.Float(), nullable=True),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_cards.id"),
            nullable=True,
        ),
    )

    # --- Table 7: pilot_matches ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # organization_id is set to demand_organization_id (the buyer's org).
    # Also has supply_organization_id and demand_organization_id as separate FKs.
    op.create_table(
        "pilot_matches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_pilot_matches_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_pilot_matches_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_pilot_matches_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "need_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buyer_need_descriptions.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_cards.id"),
            nullable=False,
        ),
        sa.Column(
            "demand_organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                name="fk_pilot_matches_demand_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "supply_organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                name="fk_pilot_matches_supply_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "Candidate",
                "ShownToDemand",
                "AcceptedByDemand",
                "ContactShared",
                "SupplyNotified",
                "ClosedPlatformRole",
                "RejectedByDemand",
                "SuppressedCapacityFull",
                name="pilotmatchstatus",
                schema="public",
                create_type=False,
            ),
            nullable=False,
            server_default="Candidate",
        ),
        sa.Column("signals", JSONB(), nullable=True),
        sa.Column("lumi_score", sa.Float(), nullable=True),
        sa.Column("demand_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_shared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supply_notified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Table 8: consortia ---
    # RLS Pattern 2 (nullable org): organization_id = ... OR organization_id IS NULL
    # Platform-scoped: organization_id is nullable (inherited from mixin, not overridden).
    # Consortia can be created by platform admins without a specific org context.
    op.create_table(
        "consortia",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_consortia_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_consortia_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_consortia_organization",
            ),
            nullable=True,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "problem_statement_id",
            UUID(as_uuid=True),
            sa.ForeignKey("buyer_need_descriptions.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
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
                name="consortiumstatus",
                schema="public",
                create_type=False,
            ),
            nullable=False,
            server_default="ProblemStatementComplete",
        ),
        sa.Column("participants", JSONB(), nullable=True),
        sa.Column("candidate_organizations", JSONB(), nullable=True),
        sa.Column("question_set_version", sa.String(), nullable=False, server_default="v1.0"),
        sa.Column("match_summary", JSONB(), nullable=True),
        sa.Column(
            "finalized_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_consortia_finalized_by_user",
            ),
            nullable=True,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Table 9: ai_projects ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "ai_projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_ai_projects_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_ai_projects_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_ai_projects_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("maturity_stage", sa.String(), nullable=True),
        sa.Column("technologies", JSONB(), nullable=True),
        sa.Column("funding_sources", JSONB(), nullable=True),
        sa.Column("public_description", sa.Text(), nullable=True),
        sa.Column("impact_metrics", JSONB(), nullable=True),
    )

    # --- Table 10: lumi_jobs ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Tenant-scoped: organization_id maps to the tenant_id concept.
    # Note: organization_id is nullable per EntityMetadataMixin default; rows with
    # NULL organization_id are invisible to tenants under Pattern 3 (correct behavior).
    op.create_table(
        "lumi_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_lumi_jobs_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_lumi_jobs_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_lumi_jobs_organization",
            ),
            nullable=True,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("use_case", sa.String(), nullable=False),
        sa.Column(
            "caller_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_lumi_jobs_caller_user",
            ),
            nullable=False,
        ),
        sa.Column("input", JSONB(), nullable=False),
        sa.Column("filters", JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("results", JSONB(), nullable=True),
        sa.Column("diagnostics", JSONB(), nullable=True),
    )

    # --- Table 11: audit_logs ---
    # Special RLS: read-only SELECT policy for app role, filtered by
    # organization_id OR organization_id IS NULL (platform-scoped entries visible).
    # INSERT/UPDATE/DELETE are handled by the BYPASSRLS migration/service role.
    # Append-only: no updated_at, no deleted_at columns.
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_audit_logs_actor_user",
            ),
            nullable=True,
        ),
        sa.Column("actor_ip", sa.String(), nullable=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                name="fk_audit_logs_organization",
            ),
            nullable=True,
        ),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("before_state", JSONB(), nullable=True),
        sa.Column("after_state", JSONB(), nullable=True),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
    )

    # --- Table 12: document_assets ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "document_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_document_assets_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_document_assets_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_document_assets_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("object_storage_key", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column(
            "uploader_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_document_assets_uploader_user",
            ),
            nullable=False,
        ),
        sa.Column("extraction_status", sa.String(), nullable=True),
        sa.Column("extracted_text_ref", sa.String(), nullable=True),
    )

    # --- Table 13: enrichment_records ---
    # RLS Pattern 3 (standard): organization_id = current_setting(...)::uuid
    # Always tenant-scoped: organization_id is NOT NULL.
    op.create_table(
        "enrichment_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_enrichment_records_created_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                use_alter=True,
                name="fk_enrichment_records_updated_by_user",
            ),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "organizations.id",
                use_alter=True,
                name="fk_enrichment_records_organization",
            ),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.Enum(
                "Public",
                "Private",
                "Internal",
                name="visibility",
                schema="public",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("field_path", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("extraction_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("human_validation_status", sa.String(), nullable=True, server_default="pending"),
    )

    # -------------------------------------------------------------------------
    # Step 3: Create indexes
    # Using CREATE INDEX (not CONCURRENTLY) -- safe for initial migration with
    # no existing data. Future migrations on populated tables MUST use CONCURRENTLY.
    # -------------------------------------------------------------------------

    # Unique index on users.email (enforces uniqueness at DB level)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Composite index on memberships(user_id, organization_id) for membership lookups
    op.create_index(
        "ix_memberships_user_id_organization_id",
        "memberships",
        ["user_id", "organization_id"],
    )

    # Composite index on buyer_need_descriptions(organization_id, status) for tenant queries
    op.create_index(
        "ix_buyer_need_descriptions_organization_id_status",
        "buyer_need_descriptions",
        ["organization_id", "status"],
    )

    # Composite index on product_cards(organization_id, status) for tenant queries
    op.create_index(
        "ix_product_cards_organization_id_status",
        "product_cards",
        ["organization_id", "status"],
    )

    # Index on pilot_matches(need_id) for need-based match lookups
    op.create_index("ix_pilot_matches_need_id", "pilot_matches", ["need_id"])

    # Index on pilot_matches(demand_organization_id) for buyer-side match queries
    op.create_index(
        "ix_pilot_matches_demand_organization_id",
        "pilot_matches",
        ["demand_organization_id"],
    )

    # Index on lumi_jobs(request_id) for job deduplication lookups
    op.create_index("ix_lumi_jobs_request_id", "lumi_jobs", ["request_id"], unique=True)

    # -------------------------------------------------------------------------
    # Step 4: Apply RLS policies
    # -------------------------------------------------------------------------

    # --- organizations: Pattern 1 (self-keyed) ---
    # The org's own PK is the tenant key: id = current_setting(...)::uuid
    # No organization_id column exists on this table.
    apply_rls_policy_self_keyed(op, "organizations")

    # --- users: Pattern 2 (nullable org) ---
    # Platform-scoped users (SuperAdmin) have organization_id=NULL and must remain
    # visible to all tenants for auth and permission resolution.
    apply_rls_policy_nullable_org(op, "users")

    # --- memberships: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "memberships")

    # --- buyer_need_descriptions: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "buyer_need_descriptions")

    # --- product_cards: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "product_cards")

    # --- reference_cards: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "reference_cards")

    # --- pilot_matches: Pattern 3 (standard) ---
    # organization_id is set to demand_organization_id (buyer's org).
    apply_rls_policy(op, "pilot_matches")

    # --- consortia: Pattern 2 (nullable org) ---
    # Platform-scoped: organization_id is nullable. Consortia created by platform
    # admins (NULL org) must remain visible to all tenants for consortium workflows.
    apply_rls_policy_nullable_org(op, "consortia")

    # --- ai_projects: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "ai_projects")

    # --- lumi_jobs: Pattern 3 (standard) ---
    # Tenant-scoped: organization_id maps to the requesting tenant.
    apply_rls_policy(op, "lumi_jobs")

    # --- audit_logs: Special (read-only for app role) ---
    # Append-only table: the app role may SELECT but MUST NOT INSERT/UPDATE/DELETE.
    # Writes are performed by the BYPASSRLS migration/service role.
    # Policy includes OR NULL so platform-scoped audit entries remain visible.
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY audit_logs_select_policy ON audit_logs
        FOR SELECT
        USING (
            organization_id = current_setting('app.current_organization_id')::uuid
            OR organization_id IS NULL
        )
        """
    )

    # --- document_assets: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "document_assets")

    # --- enrichment_records: Pattern 3 (standard) ---
    # Always tenant-scoped; organization_id is NOT NULL.
    apply_rls_policy(op, "enrichment_records")


def downgrade() -> None:
    """Drop all RLS policies, indexes, tables, and enum types in reverse order."""

    # -------------------------------------------------------------------------
    # Step 1: Drop RLS policies (reverse order)
    # -------------------------------------------------------------------------

    drop_rls_policy(op, "enrichment_records")
    drop_rls_policy(op, "document_assets")

    # audit_logs: only SELECT policy was created for app role
    op.execute("DROP POLICY IF EXISTS audit_logs_select_policy ON audit_logs")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")

    drop_rls_policy(op, "lumi_jobs")
    drop_rls_policy(op, "ai_projects")
    drop_rls_policy(op, "consortia")
    drop_rls_policy(op, "pilot_matches")
    drop_rls_policy(op, "reference_cards")
    drop_rls_policy(op, "product_cards")
    drop_rls_policy(op, "buyer_need_descriptions")
    drop_rls_policy(op, "memberships")
    drop_rls_policy(op, "users")
    drop_rls_policy(op, "organizations")

    # -------------------------------------------------------------------------
    # Step 2: Drop indexes
    # -------------------------------------------------------------------------

    op.drop_index("ix_lumi_jobs_request_id", table_name="lumi_jobs")
    op.drop_index("ix_pilot_matches_demand_organization_id", table_name="pilot_matches")
    op.drop_index("ix_pilot_matches_need_id", table_name="pilot_matches")
    op.drop_index("ix_product_cards_organization_id_status", table_name="product_cards")
    op.drop_index(
        "ix_buyer_need_descriptions_organization_id_status",
        table_name="buyer_need_descriptions",
    )
    op.drop_index(
        "ix_memberships_user_id_organization_id",
        table_name="memberships",
    )
    op.drop_index("ix_users_email", table_name="users")

    # -------------------------------------------------------------------------
    # Step 3: Drop tables in reverse FK-dependency order
    # -------------------------------------------------------------------------

    op.drop_table("enrichment_records")
    op.drop_table("document_assets")
    op.drop_table("audit_logs")
    op.drop_table("lumi_jobs")
    op.drop_table("ai_projects")
    op.drop_table("consortia")
    op.drop_table("pilot_matches")
    op.drop_table("reference_cards")
    op.drop_table("product_cards")
    op.drop_table("buyer_need_descriptions")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")

    # -------------------------------------------------------------------------
    # Step 4: Drop enum types in reverse creation order
    # -------------------------------------------------------------------------

    op.execute("DROP TYPE IF EXISTS public.visibility")
    op.execute("DROP TYPE IF EXISTS public.dataqualitystatus")
    op.execute("DROP TYPE IF EXISTS public.userstatus")
    op.execute("DROP TYPE IF EXISTS public.membershipstatus")
    op.execute("DROP TYPE IF EXISTS public.membershiprole")
    op.execute("DROP TYPE IF EXISTS public.organizationtype")
    op.execute("DROP TYPE IF EXISTS public.consortiumstatus")
    op.execute("DROP TYPE IF EXISTS public.pilotmatchstatus")
    op.execute("DROP TYPE IF EXISTS public.productstatus")
    op.execute("DROP TYPE IF EXISTS public.needstatus")
