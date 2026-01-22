import logging
from datetime import datetime, timezone

from openg2p_bg_task_models.models import DisbursementBatch
from openg2p_g2p_bridge_models.schemas import StatusEnum as StatusEnumCommon
from openg2p_pbms_models.models import (
    G2PBeneficiaryList,
    G2PDisbursementCycle,
    G2PProgramDefinition,
    StatusEnum,
)
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings
from ..helpers import G2PBridgeDisbursementHelper

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()


def construct_narrative(disbursement_cycle_mnemonic: str, program_mnemonic: str) -> str:
    return f"{program_mnemonic} - {disbursement_cycle_mnemonic}"


@celery_app.task(name="disbursement_worker")
def disbursement_worker(id: str):
    _logger.info("Starting disbursement request for disbursement batch id: %s", id)
    bg_task_session_maker = sessionmaker(
        bind=_engine.get("db_engine_bg_task"), expire_on_commit=False
    )
    pbms_session_maker = sessionmaker(
        bind=_engine.get("db_engine_pbms"), expire_on_commit=False
    )

    with pbms_session_maker() as pbms_session, bg_task_session_maker() as bg_task_session:
        disbursement_batch = None
        try:
            disbursement_batch = (
                bg_task_session.query(DisbursementBatch)
                .filter(DisbursementBatch.id == id)
                .first()
            )
            if not disbursement_batch:
                raise Exception(f"No disbursement batch entry found for id: {id}")

            beneficiary_list = (
                pbms_session.query(G2PBeneficiaryList)
                .filter(
                    G2PBeneficiaryList.beneficiary_list_id
                    == disbursement_batch.beneficiary_list_id
                )
                .first()
            )

            # Get the mnemonics and construct narative for disbursement
            disbursement_cycle_mnemonic = (
                pbms_session.query(G2PDisbursementCycle.cycle_mnemonic)
                .filter(
                    G2PDisbursementCycle.id == disbursement_batch.disbursement_cycle_id
                )
                .first()
            )
            disbursement_cycle_mnemonic: str = (
                disbursement_cycle_mnemonic[0] if disbursement_cycle_mnemonic else None
            )

            if not disbursement_cycle_mnemonic:
                raise Exception(
                    f"No disbursement cycle mnemonic found for batch id: {id}"
                )

            program_mnemonic = (
                pbms_session.query(G2PProgramDefinition.program_mnemonic)
                .filter(G2PProgramDefinition.id == beneficiary_list.program_id)
                .first()
            )
            program_mnemonic: str = program_mnemonic[0] if program_mnemonic else None

            if not program_mnemonic:
                raise Exception(f"No program mnemonic found for batch id: {id}")

            narrative: str = construct_narrative(
                disbursement_cycle_mnemonic, program_mnemonic
            )

            # Use the helper class for disbursement creation
            bridge_disbursement_helper = G2PBridgeDisbursementHelper(_config, _logger)
            (
                disbursement_response,
                error,
            ) = bridge_disbursement_helper.create_disbursement(
                disbursement_batch, bg_task_session, narrative
            )
            if error:
                raise Exception(f"Error creating disbursement: {error}")

            if (
                disbursement_response
                and hasattr(disbursement_response, "header")
                and getattr(disbursement_response.header, "status", None)
                == StatusEnumCommon.succ
            ):
                disbursement_batch.disbursement_number_of_attempts += 1
                disbursement_batch.disbursement_processed_date = datetime.now(
                    timezone.utc
                )
                disbursement_batch.disbursement_status = StatusEnum.complete.value

                bg_task_session.commit()
                _logger.info(
                    f"Disbursements created successfully for disbursement batch id: {id}"
                )
            else:
                raise Exception(
                    f"Disbursement creation failed for disbursement batch id: {id}"
                )

        except Exception as e:
            _logger.error(f"Error in disbursement batch worker: {e}")

            # Rollback all sessions
            bg_task_session.rollback()

            disbursement_batch.disbursement_number_of_attempts += 1
            disbursement_batch.disbursement_processed_date = datetime.now(timezone.utc)
            disbursement_batch.disbursement_status = (
                StatusEnum.pending.value
                if disbursement_batch.disbursement_number_of_attempts
                < _config.worker_max_attempts
                else StatusEnum.failed.value
            )
            disbursement_batch.disbursement_latest_error_code = str(e)
            bg_task_session.commit()

        _logger.info(
            "Completed processing disbursements for disbursement batch id %s" % id
        )
