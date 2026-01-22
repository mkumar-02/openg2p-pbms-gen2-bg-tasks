from openg2p_bg_task_registry_adapters.schema import (
    BeneficiaryListSummaryPayload,
)
from openg2p_g2p_bridge_models.schemas import (
    Request,
    SyncResponse,
)
from pydantic import BaseModel


class SummaryRequestPayload(BaseModel):
    beneficiary_list_id: str
    target_registry: str


class SummaryRequest(Request):
    message: SummaryRequestPayload


class SummaryResponse(SyncResponse):
    message: BeneficiaryListSummaryPayload
