from typing import List

from openg2p_g2p_bridge_models.schemas import (
    Request,
    SyncResponse,
)
from pydantic import BaseModel


class DisbursementEnvelopeRequestPayload(BaseModel):
    beneficiary_list_id: str


class DisbursementEnvelopeResponsePayload(BaseModel):
    beneficiary_list_id: str
    disbursement_envelopes: List[dict]


class DisbursementEnvelopeRequest(Request):
    message: DisbursementEnvelopeRequestPayload


class DisbursementEnvelopeResponse(SyncResponse):
    message: DisbursementEnvelopeResponsePayload
