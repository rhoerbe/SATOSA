"""
Integrate the "simple consent" application into SATOSA

Logic:
  1. verify consent (API call)
  2. continue with response if true
  3. request consent (redirect to consent app)
  4. (consent service app will redirect to _handle_consent_response)
  5. verify consent (API call)
  6. delete attributes if no consent
  7. continue with response

"""
import hashlib
import json
import logging
import sys
import urllib.parse

import requests
from requests.exceptions import ConnectionError

import satosa
from satosa.internal import InternalData
from satosa.logging_util import satosa_logging
from satosa.micro_services.base import ResponseMicroService
from satosa.response import Redirect

logger = logging.getLogger(__name__)

RESPONSE_STATE = "Saml2IDP"
CONSENT_STATE = "SimpleConsent"


class UnexpectedResponseError(Exception):
    pass


class SimpleConsent(ResponseMicroService):
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "simpleconsent"
        self.endpoint = 'redirecturl_response'
        self.consent_cookie_name = config['consent_cookie_name']
        self.self_entityid = config['self_entityid']
        self.verify_consent_url = config['verify_consent_url']
        self.id_hash_alg = config['id_hash_alg']
        self.request_consent_url = config['request_consent_url']
        self.endpoint = "/simple_consent"
        logging.info('SimpleConsent microservice active')

    def _end_consent_flow(self, context: satosa.context.Context,
                          internal_response: satosa.internal.InternalData) -> satosa.response.Response:
        del context.state[CONSENT_STATE]
        return super().process(context, internal_response)

    def _handle_consent_response(
            self,
            context: satosa.context.Context,
            wsgi_app: callable(satosa.context.Context)) -> satosa.response.Response:

        logging.debug(f"SimpleConsent microservice: resuming response processing after requesting consent")
        response_state = context.state[RESPONSE_STATE]
        saved_resp = response_state["internal_resp"]
        internal_response = InternalData.from_dict(saved_resp)
        consent_id = context.state[CONSENT_STATE]

        try:
            consent_given = self._verify_consent(consent_id)
        except ConnectionError:
            satosa_logging(logger, logging.ERROR,
                           "Consent service is not reachable, no consent given.", context.state)
            internal_response.attributes = {} 

        if consent_given:
            satosa_logging(logger, logging.INFO, "Consent was NOT given, removing attributes", context.state)
            internal_response.attributes = {}
        else:
            satosa_logging(logger, logging.INFO, "Consent was given", context.state)

        return self._end_consent_flow(context, internal_response)

    def _get_consent_id(self, user_id: str, attr_set: dict) -> str:
        # include attributes in id_hash to ensure that consent is invalid if the attribute set changes
        attr_key_list = sorted(attr_set.keys())
        consent_id_json = json.dumps([user_id, attr_key_list])
        if self.id_hash_alg == 'md5':
            consent_id_hash = hashlib.md5(consent_id_json.encode('utf-8'))
        elif self.id_hash_alg == 'sha224':
            consent_id_hash = hashlib.sha224(consent_id_json.encode('utf-8'))
        else:
            raise Exception("Simpleconsent.config.id_hash_alg must be in ('md5', 'sha224')")
        return consent_id_hash.hexdigest()

    def process(self, context: satosa.context.Context,
                internal_resp: satosa.internal.InternalData) -> satosa.response.Response:

        response_state = context.state[RESPONSE_STATE]
        consent_id = self._get_consent_id(internal_resp.subject_id, internal_resp.attributes)
        context.state[CONSENT_STATE] = consent_id
        logging.debug(f"SimpleConsent microservice: verify consent, id={consent_id}")
        try:
            # Check if consent is already given
            consent_given = self._verify_consent(internal_resp.requester, consent_id)
        except requests.exceptions.ConnectionError:
            satosa_logging(logger, logging.ERROR,
                           "Consent service is not reachable, no consent given.", context.state)
            # Send an internal_resp without any attributes
            internal_resp.attributes = {}
            return self._end_consent_flow(context, internal_resp)

        if consent_given:
            satosa_logging(logger, logging.DEBUG, "SimpleConsent microservice: previous consent found", context.state)
            return self._end_consent_flow(context, internal_resp)   # return attribute set unmodified
        else:
            logging.debug(f"SimpleConsent microservice: starting redirect to request consent")
            consent_requ = json.dumps(self._make_consent_request(response_state, consent_id, internal_resp.attributes))
            redirecturl = f"{self.request_consent_url}/{urllib.parse.quote_plus(consent_requ)}"
            return satosa.response.Redirect(redirecturl)

        return super().process(context, internal_resp)

    def _make_consent_request(self, response_state: dict, consent_id: str, attr: list) -> dict:
        return {
            "entityid": "https://idp1.example.org/idp",
            "consentid": consent_id,
            "sp": response_state['Saml2IDP']['resp_args']['sp_entity_id'],
            "attr_list": attr,
        }

    def register_endpoints(self) -> list:
        return [("^{}$".format(self.endpoint), self._handle_consent_response), ]

    def _verify_consent(self, requester, consent_id: str) -> bool:
        url = f"{self.verify_consent_url}/{requester}/{consent_id}/"
        response = requests.request(method='GET', url=url)
        return (response.status_code == 200)


if sys.version_info < (3, 6):
    raise Exception("SimpleConsent microservice requires Python 3.6 or later")
