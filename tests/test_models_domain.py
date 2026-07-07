"""Tests for domain entity models (BuyerNeedDescription, ProductCard, ReferenceCard, PilotMatch).

# kills: missing column, wrong FK target, wrong table name, wrong nullable setting,
#        wrong default value, missing JSONB type, wrong enum type on status column
"""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB

from app.db.mixins import EntityMetadataMixin
from app.db.models import BuyerNeedDescription, PilotMatch, ProductCard, ReferenceCard
from app.db.types import uuid7

# ---------------------------------------------------------------------------
# AC-1: BuyerNeedDescription model structure
# ---------------------------------------------------------------------------


def test_ac1_buyer_need_tablename() -> None:
    """AC-1: BuyerNeedDescription.__tablename__ must be 'buyer_need_descriptions'."""
    assert BuyerNeedDescription.__tablename__ == "buyer_need_descriptions"


def test_ac1_buyer_need_inherits_entity_metadata() -> None:
    """AC-1: BuyerNeedDescription must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in BuyerNeedDescription.__mro__


def test_ac1_buyer_need_columns_present() -> None:
    """AC-1: BuyerNeedDescription must have all required columns."""
    col_keys = {c.key for c in BuyerNeedDescription.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "version",
        "status",
        "title",
        "problem_summary",
        "target_outcome",
        "specific_requirements",
        "success_criteria",
        "technical_constraints",
        "timeline",
        "budget_range",
        "vendor_priorities",
        "readiness_score",
        "source_conversation_id",
    }
    # AC-1: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac1_buyer_need_organization_id_not_nullable() -> None:
    """AC-1: BuyerNeedDescription.organization_id must NOT be nullable."""
    col = BuyerNeedDescription.__table__.columns["organization_id"]
    # AC-1: expect nullable=False
    assert col.nullable is False


def test_ac1_buyer_need_title_not_nullable() -> None:
    """AC-1: BuyerNeedDescription.title must NOT be nullable."""
    col = BuyerNeedDescription.__table__.columns["title"]
    # AC-1: expect nullable=False
    assert col.nullable is False


def test_ac1_buyer_need_status_default() -> None:
    """AC-1: BuyerNeedDescription.status must default to 'Draft'."""
    col = BuyerNeedDescription.__table__.columns["status"]
    # AC-1: expect default='Draft'
    assert col.default is not None
    assert col.default.arg == "Draft"  # type: ignore[union-attr]


def test_ac1_buyer_need_version_default() -> None:
    """AC-1: BuyerNeedDescription.version must default to 'v1.0'."""
    col = BuyerNeedDescription.__table__.columns["version"]
    # AC-1: expect default='v1.0'
    assert col.default is not None
    assert col.default.arg == "v1.0"  # type: ignore[union-attr]


def test_ac1_buyer_need_jsonb_columns() -> None:
    """AC-1: JSONB columns must use JSONB type."""
    jsonb_cols = [
        "specific_requirements",
        "success_criteria",
        "technical_constraints",
        "timeline",
        "budget_range",
        "vendor_priorities",
    ]
    for col_name in jsonb_cols:
        col = BuyerNeedDescription.__table__.columns[col_name]
        # AC-1: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


def test_ac1_buyer_need_readiness_score_nullable() -> None:
    """AC-1: BuyerNeedDescription.readiness_score must be nullable Float."""
    col = BuyerNeedDescription.__table__.columns["readiness_score"]
    # AC-1: expect nullable=True
    assert col.nullable is True


def test_ac1_buyer_need_source_conversation_id_nullable() -> None:
    """AC-1: BuyerNeedDescription.source_conversation_id must be nullable UUID."""
    col = BuyerNeedDescription.__table__.columns["source_conversation_id"]
    # AC-1: expect nullable=True
    assert col.nullable is True


def test_ac1_buyer_need_organization_id_fk() -> None:
    """AC-1: BuyerNeedDescription.organization_id must FK to organizations.id."""
    col = BuyerNeedDescription.__table__.columns["organization_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-1: expect FK to organizations.id
    assert "organizations.id" in fk_targets


# ---------------------------------------------------------------------------
# AC-2: ProductCard model structure
# ---------------------------------------------------------------------------


def test_ac2_product_card_tablename() -> None:
    """AC-2: ProductCard.__tablename__ must be 'product_cards'."""
    assert ProductCard.__tablename__ == "product_cards"


def test_ac2_product_card_inherits_entity_metadata() -> None:
    """AC-2: ProductCard must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in ProductCard.__mro__


def test_ac2_product_card_columns_present() -> None:
    """AC-2: ProductCard must have all required columns."""
    col_keys = {c.key for c in ProductCard.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "version",
        "status",
        "name",
        "product_version",
        "short_description",
        "demo",
        "pricing_model",
        "price_range",
        "hosting_location",
        "certifications",
        "readiness",
        "implementation_time",
        "pilot_settings",
    }
    # AC-2: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac2_product_card_organization_id_not_nullable() -> None:
    """AC-2: ProductCard.organization_id must NOT be nullable."""
    col = ProductCard.__table__.columns["organization_id"]
    # AC-2: expect nullable=False
    assert col.nullable is False


def test_ac2_product_card_name_not_nullable() -> None:
    """AC-2: ProductCard.name must NOT be nullable."""
    col = ProductCard.__table__.columns["name"]
    # AC-2: expect nullable=False
    assert col.nullable is False


def test_ac2_product_card_status_default() -> None:
    """AC-2: ProductCard.status must default to 'Draft'."""
    col = ProductCard.__table__.columns["status"]
    # AC-2: expect default='Draft'
    assert col.default is not None
    assert col.default.arg == "Draft"  # type: ignore[union-attr]


def test_ac2_product_card_version_default() -> None:
    """AC-2: ProductCard.version must default to 'v1.0'."""
    col = ProductCard.__table__.columns["version"]
    # AC-2: expect default='v1.0'
    assert col.default is not None
    assert col.default.arg == "v1.0"  # type: ignore[union-attr]


def test_ac2_product_card_jsonb_columns() -> None:
    """AC-2: JSONB columns must use JSONB type."""
    jsonb_cols = [
        "demo",
        "price_range",
        "certifications",
        "readiness",
        "pilot_settings",
    ]
    for col_name in jsonb_cols:
        col = ProductCard.__table__.columns[col_name]
        # AC-2: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


def test_ac2_product_card_organization_id_fk() -> None:
    """AC-2: ProductCard.organization_id must FK to organizations.id."""
    col = ProductCard.__table__.columns["organization_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-2: expect FK to organizations.id
    assert "organizations.id" in fk_targets


# ---------------------------------------------------------------------------
# AC-3: ReferenceCard model structure
# ---------------------------------------------------------------------------


def test_ac3_reference_card_tablename() -> None:
    """AC-3: ReferenceCard.__tablename__ must be 'reference_cards'."""
    assert ReferenceCard.__tablename__ == "reference_cards"


def test_ac3_reference_card_inherits_entity_metadata() -> None:
    """AC-3: ReferenceCard must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in ReferenceCard.__mro__


def test_ac3_reference_card_columns_present() -> None:
    """AC-3: ReferenceCard must have all required columns."""
    col_keys = {c.key for c in ReferenceCard.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "version",
        "reference_type",
        "status",
        "customer_industry",
        "customer_size",
        "measurable_result",
        "timeline",
        "technologies_used",
        "provider_role",
        "starting_situation_and_problem",
        "solution_approach",
        "ai_extraction_confidence",
        "product_id",
    }
    # AC-3: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac3_reference_card_organization_id_not_nullable() -> None:
    """AC-3: ReferenceCard.organization_id must NOT be nullable."""
    col = ReferenceCard.__table__.columns["organization_id"]
    # AC-3: expect nullable=False
    assert col.nullable is False


def test_ac3_reference_card_reference_type_default() -> None:
    """AC-3: ReferenceCard.reference_type must default to 'anonymous'."""
    col = ReferenceCard.__table__.columns["reference_type"]
    # AC-3: expect default='anonymous'
    assert col.default is not None
    assert col.default.arg == "anonymous"  # type: ignore[union-attr]


def test_ac3_reference_card_status_default() -> None:
    """AC-3: ReferenceCard.status must default to 'draft'."""
    col = ReferenceCard.__table__.columns["status"]
    # AC-3: expect default='draft'
    assert col.default is not None
    assert col.default.arg == "draft"  # type: ignore[union-attr]


def test_ac3_reference_card_product_id_fk() -> None:
    """AC-3: ReferenceCard.product_id must FK to product_cards.id."""
    col = ReferenceCard.__table__.columns["product_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-3: expect FK to product_cards.id
    assert "product_cards.id" in fk_targets


def test_ac3_reference_card_product_id_nullable() -> None:
    """AC-3: ReferenceCard.product_id must be nullable."""
    col = ReferenceCard.__table__.columns["product_id"]
    # AC-3: expect nullable=True
    assert col.nullable is True


def test_ac3_reference_card_jsonb_columns() -> None:
    """AC-3: JSONB columns must use JSONB type."""
    jsonb_cols = ["timeline", "technologies_used"]
    for col_name in jsonb_cols:
        col = ReferenceCard.__table__.columns[col_name]
        # AC-3: expect JSONB type and nullable
        assert isinstance(col.type, JSONB), f"{col_name} must be JSONB"
        assert col.nullable is True, f"{col_name} must be nullable"


def test_ac3_reference_card_ai_extraction_confidence_nullable() -> None:
    """AC-3: ReferenceCard.ai_extraction_confidence must be nullable Float."""
    col = ReferenceCard.__table__.columns["ai_extraction_confidence"]
    # AC-3: expect nullable=True
    assert col.nullable is True


# ---------------------------------------------------------------------------
# AC-4: PilotMatch model structure
# ---------------------------------------------------------------------------


def test_ac4_pilot_match_tablename() -> None:
    """AC-4: PilotMatch.__tablename__ must be 'pilot_matches'."""
    assert PilotMatch.__tablename__ == "pilot_matches"


def test_ac4_pilot_match_inherits_entity_metadata() -> None:
    """AC-4: PilotMatch must inherit EntityMetadataMixin."""
    assert EntityMetadataMixin in PilotMatch.__mro__


def test_ac4_pilot_match_columns_present() -> None:
    """AC-4: PilotMatch must have all required columns."""
    col_keys = {c.key for c in PilotMatch.__table__.columns}
    expected = {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "organization_id",
        "visibility",
        "need_id",
        "product_id",
        "demand_organization_id",
        "supply_organization_id",
        "status",
        "signals",
        "lumi_score",
        "demand_approved_at",
        "contact_shared_at",
        "supply_notified_at",
    }
    # AC-4: expect all columns present
    assert expected.issubset(col_keys), f"Missing columns: {expected - col_keys}"


def test_ac4_pilot_match_organization_id_not_nullable() -> None:
    """AC-4: PilotMatch.organization_id must NOT be nullable."""
    col = PilotMatch.__table__.columns["organization_id"]
    # AC-4: expect nullable=False
    assert col.nullable is False


def test_ac4_pilot_match_need_id_fk() -> None:
    """AC-4: PilotMatch.need_id must FK to buyer_need_descriptions.id."""
    col = PilotMatch.__table__.columns["need_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-4: expect FK to buyer_need_descriptions.id
    assert "buyer_need_descriptions.id" in fk_targets


def test_ac4_pilot_match_product_id_fk() -> None:
    """AC-4: PilotMatch.product_id must FK to product_cards.id."""
    col = PilotMatch.__table__.columns["product_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-4: expect FK to product_cards.id
    assert "product_cards.id" in fk_targets


def test_ac4_pilot_match_demand_organization_id_fk() -> None:
    """AC-4: PilotMatch.demand_organization_id must FK to organizations.id."""
    col = PilotMatch.__table__.columns["demand_organization_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-4: expect FK to organizations.id
    assert "organizations.id" in fk_targets
    # AC-4: expect not nullable
    assert col.nullable is False


def test_ac4_pilot_match_supply_organization_id_fk() -> None:
    """AC-4: PilotMatch.supply_organization_id must FK to organizations.id."""
    col = PilotMatch.__table__.columns["supply_organization_id"]
    fk_targets = [fk.target_fullname for fk in col.foreign_keys]
    # AC-4: expect FK to organizations.id
    assert "organizations.id" in fk_targets
    # AC-4: expect not nullable
    assert col.nullable is False


def test_ac4_pilot_match_status_default() -> None:
    """AC-4: PilotMatch.status must default to 'Candidate'."""
    col = PilotMatch.__table__.columns["status"]
    # AC-4: expect default='Candidate'
    assert col.default is not None
    assert col.default.arg == "Candidate"  # type: ignore[union-attr]


def test_ac4_pilot_match_signals_jsonb() -> None:
    """AC-4: PilotMatch.signals must be JSONB and nullable."""
    col = PilotMatch.__table__.columns["signals"]
    # AC-4: expect JSONB type and nullable
    assert isinstance(col.type, JSONB)
    assert col.nullable is True


def test_ac4_pilot_match_lumi_score_nullable() -> None:
    """AC-4: PilotMatch.lumi_score must be nullable Float."""
    col = PilotMatch.__table__.columns["lumi_score"]
    # AC-4: expect nullable=True
    assert col.nullable is True


def test_ac4_pilot_match_timestamps_timezone() -> None:
    """AC-4: DateTime columns must use timezone=True."""
    for col_name in ("demand_approved_at", "contact_shared_at", "supply_notified_at"):
        col = PilotMatch.__table__.columns[col_name]
        # AC-4: expect timezone=True on DateTime
        assert col.type.timezone is True, f"{col_name} must have timezone=True"
        assert col.nullable is True, f"{col_name} must be nullable"


# ---------------------------------------------------------------------------
# AC-5: __init__.py exports all domain models
# ---------------------------------------------------------------------------


def test_ac5_models_init_exports_domain_models() -> None:
    """AC-5: app.db.models must export all domain models."""
    import app.db.models as models_pkg

    # AC-5: expect all domain models importable from the package
    assert hasattr(models_pkg, "BuyerNeedDescription")
    assert hasattr(models_pkg, "ProductCard")
    assert hasattr(models_pkg, "ReferenceCard")
    assert hasattr(models_pkg, "PilotMatch")
    assert models_pkg.BuyerNeedDescription is BuyerNeedDescription
    assert models_pkg.ProductCard is ProductCard
    assert models_pkg.ReferenceCard is ReferenceCard
    assert models_pkg.PilotMatch is PilotMatch


# ---------------------------------------------------------------------------
# AC-1 (cont): BuyerNeedDescription instantiation
# ---------------------------------------------------------------------------


def test_ac1_buyer_need_instantiation() -> None:
    """AC-1: BuyerNeedDescription can be instantiated with required fields."""
    org_id = uuid7()
    need = BuyerNeedDescription(organization_id=org_id, title="Test Need")
    # AC-1: expect explicit fields set
    assert need.organization_id == org_id
    assert need.title == "Test Need"


# ---------------------------------------------------------------------------
# AC-2 (cont): ProductCard instantiation
# ---------------------------------------------------------------------------


def test_ac2_product_card_instantiation() -> None:
    """AC-2: ProductCard can be instantiated with required fields."""
    org_id = uuid7()
    card = ProductCard(organization_id=org_id, name="Test Product")
    # AC-2: expect explicit fields set
    assert card.organization_id == org_id
    assert card.name == "Test Product"


# ---------------------------------------------------------------------------
# AC-3 (cont): ReferenceCard instantiation
# ---------------------------------------------------------------------------


def test_ac3_reference_card_instantiation() -> None:
    """AC-3: ReferenceCard can be instantiated with required fields."""
    org_id = uuid7()
    ref = ReferenceCard(organization_id=org_id)
    # AC-3: expect explicit fields set
    assert ref.organization_id == org_id


# ---------------------------------------------------------------------------
# AC-4 (cont): PilotMatch instantiation
# ---------------------------------------------------------------------------


def test_ac4_pilot_match_instantiation() -> None:
    """AC-4: PilotMatch can be instantiated with required fields."""
    org_id = uuid7()
    need_id = uuid7()
    product_id = uuid7()
    supply_org_id = uuid7()
    match = PilotMatch(
        organization_id=org_id,
        need_id=need_id,
        product_id=product_id,
        demand_organization_id=org_id,
        supply_organization_id=supply_org_id,
    )
    # AC-4: expect explicit fields set
    assert match.organization_id == org_id
    assert match.need_id == need_id
    assert match.product_id == product_id
    assert match.demand_organization_id == org_id
    assert match.supply_organization_id == supply_org_id
