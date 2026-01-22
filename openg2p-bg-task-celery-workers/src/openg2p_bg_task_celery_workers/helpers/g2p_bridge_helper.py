import asyncio
import json

import requests
from openg2p_bg_task_models.schemas import Disbursement
from openg2p_g2p_bridge_models.schemas import (
    DisbursementEnvelopeRequest,
    DisbursementEnvelopeResponse,
    DisbursementPayload,
    DisbursementRequest,
    DisbursementResponse,
    RequestHeader,
)

from .keymanager_helper import KeymanagerHelper


class G2PBridgeDisbursementHelper:
    def __init__(self, config, logger):
        self._config = config
        self._logger = logger
        self.keymanager_helper = KeymanagerHelper(self._config, self._logger)

    def create_disbursement_envelopes(self, disbursement_envelope_request_message):
        """
        Sends a request to the bridge to create a disbursement envelope.
        """
        disbursement_envelope_request_header = RequestHeader(
            version="1.0.0",
            message_id="string",
            message_ts="string",
            action="create_disbursement_envelopes",
            sender_id=self._config.sign_key_keymanager_app_id,
            sender_uri="",
            receiver_id="",
            total_count=1,
            is_msg_encrypted=False,
            meta="string",
        )
        disbursement_envelope_request = DisbursementEnvelopeRequest(
            header=disbursement_envelope_request_header,
            message=disbursement_envelope_request_message,
        )
        disbursement_envelope_request_json = disbursement_envelope_request.model_dump(
            mode="json"
        )
        self._logger.debug(
            f"Disbursement Envelope Request: {disbursement_envelope_request_json}"
        )

        envelope_creation_url = (
            self._config.g2p_bridge_base_url + "/create_disbursement_envelopes"
        )
        self._logger.debug(f"Envelope Creation URL: {envelope_creation_url}")

        jwt_token = asyncio.run(
            self.keymanager_helper.create_jwt_token(
                json.dumps(
                    disbursement_envelope_request_json,
                    indent=None,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Signature": jwt_token,
        }

        self._logger.info("Calling disbursement envelope creation endpoint")
        try:
            response = requests.post(
                envelope_creation_url,
                json=disbursement_envelope_request_json,
                headers=headers,
            )
            response.raise_for_status()
            self._logger.info(
                f"Response status code for disbursement envelope request: {response.status_code}"
            )

            disbursement_envelope_response = (
                DisbursementEnvelopeResponse.model_validate(response.json())
            )
            self._logger.debug(
                f"Disbursement Envelope Response: {disbursement_envelope_response}"
            )

            return disbursement_envelope_response, None

        except Exception as e:
            self._logger.error(
                f"Error occurred while calling envelope creation API: {e}"
            )
            return None, str(e)

    def create_disbursement(self, disbursement_batch, bg_task_session, narrative):
        """
        Sends a request to the bridge to create disbursements.
        """

        disbursement_payloads = []

        for disbursement in disbursement_batch.disbursements:
            disbursement = Disbursement(**disbursement)

            disbursement_payload = DisbursementPayload(
                disbursement_id=disbursement.disbursement_id,
                disbursement_envelope_id=disbursement_batch.disbursement_envelope_id,
                beneficiary_id=disbursement.beneficiary_id,
                beneficiary_name=None,
                disbursement_quantity=disbursement.entitlement,
                compute_elements=disbursement.compute_elements,
                disbursement_cycle_id=int(disbursement_batch.disbursement_cycle_id),
                disbursement_batch_control_id=disbursement_batch.id,
                narrative=narrative,
            )
            disbursement_payloads.append(disbursement_payload)

        disbursement_header = RequestHeader(
            version="1.0.0",
            message_id="string",
            message_ts="string",
            action="create_disbursements",
            sender_id=self._config.sign_key_keymanager_app_id,
            sender_uri="",
            receiver_id="",
            total_count=len(disbursement_payloads),
            is_msg_encrypted=False,
            meta="string",
        )

        disbursement_request = DisbursementRequest(
            header=disbursement_header,
            disbursement_batch_control_id=disbursement_batch.id,
            message=disbursement_payloads,
        )
        disbursement_request_json = disbursement_request.model_dump(mode="json")
        self._logger.debug(f"Disbursement request payload: {disbursement_request_json}")

        disbursement_url = self._config.g2p_bridge_base_url + "/create_disbursements"
        self._logger.debug(f"Disbursement URL: {disbursement_url}")

        jwt_token = asyncio.run(
            self.keymanager_helper.create_jwt_token(
                json.dumps(
                    disbursement_request_json,
                    indent=None,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
        )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Signature": jwt_token,
        }
        self._logger.info(
            f"Calling disbursement creation endpoint for disbursement batch id {disbursement_batch.id} having {len(disbursement_payloads)} beneficiaries"
        )
        try:
            response = requests.post(
                disbursement_url, json=disbursement_request_json, headers=headers
            )
            response.raise_for_status()
            self._logger.info(
                f"Response status code for disbursement batch id {disbursement_batch.id}: {response.status_code}"
            )

            disbursement_response = DisbursementResponse.model_validate(response.json())
            self._logger.debug(
                f"Response for disbursement batch id {disbursement_batch.id}: {disbursement_response}"
            )

            return disbursement_response, None

        except Exception as e:
            self._logger.error(f"Error occurred while calling disbursement API: {e}")
            return None, str(e)
