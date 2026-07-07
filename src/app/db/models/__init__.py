"""SQLAlchemy ORM models -- import all so Alembic autogenerate discovers them."""

from app.db.models.ai_project import AIProject
from app.db.models.audit_log import AuditLog
from app.db.models.buyer_need import BuyerNeedDescription
from app.db.models.consortium import Consortium
from app.db.models.document_asset import DocumentAsset
from app.db.models.enrichment_record import EnrichmentRecord
from app.db.models.lumi_job import LumiJob
from app.db.models.membership import Membership
from app.db.models.organization import Organization
from app.db.models.pilot_match import PilotMatch
from app.db.models.product_card import ProductCard
from app.db.models.reference_card import ReferenceCard
from app.db.models.user import User

__all__ = [
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
