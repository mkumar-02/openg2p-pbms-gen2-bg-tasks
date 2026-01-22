from typing import List, Optional

from openg2p_g2p_bridge_models.schemas import (
    Request,
    SyncResponse,
)
from pydantic import BaseModel


class DisbursementBatchRequestPayload(BaseModel):
    beneficiary_list_id: str


class DisbursementBatchResponsePayload(BaseModel):
    beneficiary_list_id: Optional[str] = None
    disbursement_batches: List[dict]


class DisbursementBatchRequest(Request):
    message: DisbursementBatchRequestPayload


class DisbursementBatchResponse(SyncResponse):
    message: DisbursementBatchResponsePayload
