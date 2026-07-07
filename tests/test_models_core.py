"""Tests for core domain entity models (Organization, User, Membership).

# kills: missing column, wrong FK target, wrong table name, missing constraint,
#        wrong nullable setting, missing unique constraint on membership
"""

from __future__ import annotations

import uuid

from app.db.models import Membership, Organization, User
from app.db.types import uuid7

# ---------------------------------------------------------------------------
# AC-1: Organization model structure
# ---------------------------------------------------------------------------


def test_ac1_organization_tablename() -> None:
    """AC-1: Organization.__tablename__ must be 'organizations'."""
    assert Organization.__tablename__ == "organizations"


def test_ac1_organization_columns_present() -> None:
    """AC-1: Organization must have all required columns."""
    col_keys = {c.key for c in Organization.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "visibility",
        "name",
        "business_id",
        "organization_type",
        "location",
        "ai_maturity_level",
        "capabilities",
        "status",
    }
    # AC-1: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac1_organization_does_not_have_organization_id() -> None:
    """AC-1: Organization must NOT have organization_id (no self-referential FK)."""
    col_keys = {c.key for c in Organization.__table__.columns}
    # AC-1: expect no organization_id column
    assert "organization_id" not in col_keys


def test_ac1_organization_id_is_primary_key() -> None:
    """AC-1: Organization.id must be the primary key."""
    pk_cols = [c.name for c in Organization.__table__.primary_key.columns]
    # AC-1: expect 'id' as primary key
    assert pk_cols == ["id"]


def test_ac1_organization_id_default_is_uuid7() -> None:
    """AC-1: Organization.id default must produce UUIDv7."""
    col = Organization.__table__.columns["id"]
    # AC-1: expect default callable that produces UUIDv7
    assert col.default is not None
    assert col.default.is_callable
    # SQLAlchemy wraps the callable to accept a context arg
    result = col.default.arg(None)  # type: ignore[misc]
    assert isinstance(result, uuid.UUID)
    assert result.version == 7


def test_ac1_organization_name_not_nullable() -> None:
    """AC-1: Organization.name must be NOT NULL."""
    col = Organization.__table__.columns["name"]
    # AC-1: expect nullable=False
    assert col.nullable is False


def test_ac1_organization_business_id_unique() -> None:
    """AC-1: Organization.business_id must have a unique constraint."""
    col = Organization.__table__.columns["business_id"]
    # AC-1: expect unique=True
    assert col.unique is True


def test_ac1_organization_ai_maturity_check_constraint() -> None:
    """AC-1: Organization must have a check constraint on ai_maturity_level."""
    constraints = [
        c for c in Organization.__table__.constraints
        if hasattr(c, "name") and c.name == "ck_organizations_ai_maturity_level_range"
    ]
    # AC-1: expect check constraint exists
    assert len(constraints) == 1


def test_ac1_organization_status_default() -> None:
    """AC-1: Organization.status must default to 'active'."""
    col = Organization.__table__.columns["status"]
    # AC-1: expect default='active'
    assert col.default is not None
    assert col.default.arg == "active"  # type: ignore[union-attr]


def test_ac1_organization_created_at_server_default() -> None:
    """AC-1: Organization.created_at must have a server_default."""
    col = Organization.__table__.columns["created_at"]
    # AC-1: expect server_default is set
    assert col.server_default is not None


def test_ac1_organization_timestamps_timezone() -> None:
    """AC-1: All timestamp columns must use DateTime(timezone=True)."""
    for col_name in ("created_at", "updated_at", "deleted_at"):
        col = Organization.__table__.columns[col_name]
        # AC-1: expect timezone=True on DateTime
        assert col.type.timezone is True, f"{col_name} must have timezone=True"


# ---------------------------------------------------------------------------
# AC-2: User model structure
# ---------------------------------------------------------------------------


def test_ac2_user_tablename() -> None:
    """AC-2: User.__tablename__ must be 'users'."""
    assert User.__tablename__ == "users"


def test_ac2_user_columns_present() -> None:
    """AC-2: User must have all required columns."""
    col_keys = {c.key for c in User.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "email",
        "username",
        "display_name",
        "password_hash",
        "status",
        "preferred_language",
        "mfa_enabled",
        "mfa_secret",
        "last_login_at",
        "force_password_reset",
    }
    # AC-2: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac2_user_organization_id_nullable() -> None:
    """AC-2: User.organization_id must be nullable (platform-scoped users)."""
    col = User.__table__.columns["organization_id"]
    # AC-2: expect nullable=True
    assert col.nullable is True


def test_ac2_user_email_unique_not_null() -> None:
    """AC-2: User.email must be unique and not null."""
    col = User.__table__.columns["email"]
    # AC-2: expect unique and not nullable
    assert col.unique is True
    assert col.nullable is False


def test_ac2_user_password_hash_not_null() -> None:
    """AC-2: User.password_hash must be not null."""
    col = User.__table__.columns["password_hash"]
    # AC-2: expect nullable=False
    assert col.nullable is False


def test_ac2_user_status_default() -> None:
    """AC-2: User.status must default to 'Active'."""
    col = User.__table__.columns["status"]
    # AC-2: expect default='Active'
    assert col.default is not None
    assert col.default.arg == "Active"  # type: ignore[union-attr]


def test_ac2_user_preferred_language_default() -> None:
    """AC-2: User.preferred_language must default to 'fi'."""
    col = User.__table__.columns["preferred_language"]
    # AC-2: expect default='fi'
    assert col.default is not None
    assert col.default.arg == "fi"  # type: ignore[union-attr]


def test_ac2_user_mfa_enabled_default_false() -> None:
    """AC-2: User.mfa_enabled must default to False."""
    col = User.__table__.columns["mfa_enabled"]
    # AC-2: expect default=False
    assert col.default is not None
    assert col.default.arg is False  # type: ignore[union-attr]


def test_ac2_user_force_password_reset_default_false() -> None:
    """AC-2: User.force_password_reset must default to False."""
    col = User.__table__.columns["force_password_reset"]
    # AC-2: expect default=False
    assert col.default is not None
    assert col.default.arg is False  # type: ignore[union-attr]


def test_ac2_user_last_login_at_timezone() -> None:
    """AC-2: User.last_login_at must use DateTime(timezone=True)."""
    col = User.__table__.columns["last_login_at"]
    # AC-2: expect timezone=True
    assert col.type.timezone is True


def test_ac2_user_inherits_entity_metadata() -> None:
    """AC-2: User must inherit EntityMetadataMixin columns."""
    from app.db.mixins import EntityMetadataMixin

    # AC-2: expect User has EntityMetadataMixin in MRO
    assert EntityMetadataMixin in User.__mro__


# ---------------------------------------------------------------------------
# AC-3: Membership model structure
# ---------------------------------------------------------------------------


def test_ac3_membership_tablename() -> None:
    """AC-3: Membership.__tablename__ must be 'memberships'."""
    assert Membership.__tablename__ == "memberships"


def test_ac3_membership_columns_present() -> None:
    """AC-3: Membership must have all required columns."""
    col_keys = {c.key for c in Membership.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "user_id",
        "role",
        "status",
    }
    # AC-3: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac3_membership_organization_id_not_nullable() -> None:
    """AC-3: Membership.organization_id must NOT be nullable."""
    col = Membership.__table__.columns["organization_id"]
    # AC-3: expect nullable=False
    assert col.nullable is False


def test_ac3_membership_user_id_not_nullable() -> None:
    """AC-3: Membership.user_id must NOT be nullable."""
    col = Membership.__table__.columns["user_id"]
    # AC-3: expect nullable=False
    assert col.nullable is False


def test_ac3_membership_user_id_fk_to_users() -> None:
    """AC-3: Membership.user_id must FK to users.id."""
    col = Membership.__table__.columns["user_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-3: expect FK to users.id
    assert "users.id" in fk_targets


def test_ac3_membership_unique_constraint() -> None:
    """AC-3: Membership must have UniqueConstraint on (user_id, organization_id)."""
    from sqlalchemy import UniqueConstraint

    unique_constraints = [
        c for c in Membership.__table__.constraints
        if isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns} == {"user_id", "organization_id"}
    ]
    # AC-3: expect exactly one such constraint
    assert len(unique_constraints) == 1


def test_ac3_membership_role_not_nullable() -> None:
    """AC-3: Membership.role must NOT be nullable."""
    col = Membership.__table__.columns["role"]
    # AC-3: expect nullable=False
    assert col.nullable is False


def test_ac3_membership_status_default() -> None:
    """AC-3: Membership.status must default to 'Active'."""
    col = Membership.__table__.columns["status"]
    # AC-3: expect default='Active'
    assert col.default is not None
    assert col.default.arg == "Active"  # type: ignore[union-attr]


def test_ac3_membership_inherits_entity_metadata() -> None:
    """AC-3: Membership must inherit EntityMetadataMixin."""
    from app.db.mixins import EntityMetadataMixin

    # AC-3: expect Membership has EntityMetadataMixin in MRO
    assert EntityMetadataMixin in Membership.__mro__


# ---------------------------------------------------------------------------
# AC-4: __init__.py exports all models
# ---------------------------------------------------------------------------


def test_ac4_models_init_exports() -> None:
    """AC-4: app.db.models must export Organization, User, Membership."""
    import app.db.models as models_pkg

    # AC-4: expect all three models importable from the package
    assert hasattr(models_pkg, "Organization")
    assert hasattr(models_pkg, "User")
    assert hasattr(models_pkg, "Membership")
    assert models_pkg.Organization is Organization
    assert models_pkg.User is User
    assert models_pkg.Membership is Membership


# ---------------------------------------------------------------------------
# AC-1 (cont): Organization instantiation with defaults
# ---------------------------------------------------------------------------


def test_ac1_organization_instantiation() -> None:
    """AC-1: Organization can be instantiated with required fields."""
    org = Organization(name="Test Org")
    # AC-1: expect name set
    assert org.name == "Test Org"
    # Column defaults (status, id) are applied at INSERT time by SQLAlchemy,
    # so we verify the column metadata has the correct defaults instead.
    status_col = Organization.__table__.columns["status"]
    assert status_col.default is not None
    assert status_col.default.arg == "active"


# ---------------------------------------------------------------------------
# AC-2 (cont): User instantiation with defaults
# ---------------------------------------------------------------------------


def test_ac2_user_instantiation() -> None:
    """AC-2: User can be instantiated with required fields."""
    user = User(email="test@example.com", password_hash="$2b$12$hash")
    # AC-2: expect explicit fields set
    assert user.email == "test@example.com"
    assert user.password_hash == "$2b$12$hash"
    # Column defaults are applied at INSERT time; verify column metadata
    cols = User.__table__.columns
    assert cols["preferred_language"].default.arg == "fi"  # type: ignore[union-attr]
    assert cols["mfa_enabled"].default.arg is False  # type: ignore[union-attr]
    assert cols["force_password_reset"].default.arg is False  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# AC-3 (cont): Membership instantiation
# ---------------------------------------------------------------------------


def test_ac3_membership_instantiation() -> None:
    """AC-3: Membership can be instantiated with required fields."""
    org_id = uuid7()
    user_id = uuid7()
    m = Membership(organization_id=org_id, user_id=user_id, role="Admin")
    # AC-3: expect explicit fields set
    assert m.organization_id == org_id
    assert m.user_id == user_id
    assert m.role == "Admin"
    # Column default for status is applied at INSERT time
    status_col = Membership.__table__.columns["status"]
    assert status_col.default is not None
    assert status_col.default.arg == "Active"
