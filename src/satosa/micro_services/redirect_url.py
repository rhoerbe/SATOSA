"""
ADFS/SAML-Support for role selection and profile completion after a SAML-Response
was issued using a redirect-to-idp flow.
* Store AuthnRequest for later replay
* Handle redirect-to-idp and replay AuthnRequest after redirect-to-idp flow
"""

import logging
import pickle
import sys
from base64 import a85encode, a85decode
import satosa
from .base import RequestMicroService, ResponseMicroService

MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

STATE_KEY = "REDIRURLCONTEXT"


class RedirectUrlRequest(RequestMicroService):
    """ Store AuthnRequest in SATOSA STATE in case it is required later for the RedirectUrl flow """
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.info('RedirectUrlRequest microservice active')

    def process(self, context: satosa.context.Context,
                internal_request: satosa.internal.InternalData) -> satosa.internal.InternalData:
        logging.debug(f"RedirectUrlRequest: store context (stub)")
        context_serlzd = a85encode(pickle.dumps(context, pickle.HIGHEST_PROTOCOL))
        context_serlzd_str = context_serlzd.decode('utf-8')
        #context.state[STATE_KEY] = context_serlzd_str  # too large for cookie, move to memcached
        return super().process(context, internal_request)


class RedirectUrlResponse(ResponseMicroService):
    """
    Handle following events:
    * Processing a SAML Response:
        if the redirectUrl attribute is set in the response/attribute statement:
                        Redirect to responder
    * Processing a RedirectUrlResponse:
        Retrieve AuthnRequest in SATOSA STATE
        Re-issue AuthnRequest
    """
    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint = 'saml2/redirecturl_response'
        self.redir_attr = config['redirect_attr_name']
        self.redir_entityid = config['redir_entityid']
        logging.info('RedirectUrlResponse microservice active')

    def _handle_redirecturl_response(self, context: satosa.context.Context) -> satosa.response.Response:
        logging.debug(f"RedirectUrl microservice: RedirectUrl processing complete")
        #redir_context = pickle.loads(a85decode(context.state[STATE_KEY]).encode('utf-8'))  # TODO
        #satosa.base.run(redir_context)

    def process(self, context: satosa.context.Context,
                internal_response: satosa.internal.InternalData) -> satosa.response.Response:
        if self.redir_attr in internal_response.attributes:
            logging.debug(f"RedirectUrl microservice: Attribute {self.redir_attr} found, starting redirect")
            redirecturl = internal_response.attributes[self.redir_attr][0] + '?wtrealm=' + 'https%3A%2F%2Fproxy2.test.wpv.portalverbund.at%2Fsp%2Fproxy_backend.xml'
            return satosa.response.Redirect(redirecturl)
        else:
            logging.debug(f"RedirectUrl microservice: Attribute {self.redir_attr} not found")
        return super().process(context, context)

    def register_endpoints(self):
        return [("^{}$".format(self.endpoint), self._handle_redirecturl_response), ]


