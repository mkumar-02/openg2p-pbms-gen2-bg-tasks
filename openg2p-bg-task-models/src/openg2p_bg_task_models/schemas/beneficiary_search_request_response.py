from typing import List, Optional

from openg2p_g2p_bridge_models.schemas import (
    Request,
    SyncResponse,
)
from pydantic import BaseModel


class BeneficiarySearchRequestPayload(BaseModel):
    beneficiary_list_id: str
    target_registry: str
    page: int
    page_size: int
    search_query: str
    order_by: str


class BeneficiarySearchResponsePayload(BaseModel):
    total_beneficiary_count: int
    page: int
    page_size: int
    beneficiaries: Optional[List[object]] = None


class BeneficiarySearchRequest(Request):
    message: BeneficiarySearchRequestPayload


class BeneficiarySearchResponse(SyncResponse):
    message: BeneficiarySearchResponsePayload
