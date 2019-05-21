import logging
import sys
import satosa
from .base import ResponseMicroService

MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)


class RedirectUrl(ResponseMicroService):
    """
    ADFS/SAML-Support for role selection and profile completion after login:
        if the redirectUrl attribute is set in the response/attribute statement:
            Store AuthnRequest in SATOSA STATE
            Redirect to responder
    3. Re-issue AuthnRequest
    """

    def __init__(self, config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint = "/redirecturl_response"
        self.redir_attr = config['redirect_attr_name']
        self.STATE_KEY = "REDIRURL"
        logging.info('RedirectUrl microservice active')

    def _handle_redirecturl_response(self, context: satosa.context.Context) -> satosa.response.Response:
        pass

    def process(self, context: satosa.context.Context,
                internal_response: satosa.internal.InternalData) -> satosa.response.Response:
        redir_state = context.state[self.STATE_KEY]
        if self.redir_attr in internal_response.attributes:
            logging.debug(f"RedirectUrl microservice: Attribute {self.redir_attr} found, starting redirect")
            context.state[self.STATE_KEY]["authRequest"] = 'placeholder authnRequest'
            redirecturl = internal_response.attributes[self.redir_attr]
            return satosa.response.Redirect(redirecturl)
        else:
            logging.debug(f"RedirectUrl microservice: Attribute {self.redir_attr} not found")
        return super().process(context, context)

    def register_endpoints(self):
        return [("^{}$".format(self.endpoint), self._handle_redirecturl_response), ]
