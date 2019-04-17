import logging
from .base import ResponseMicroService
from satosa.response import Redirect


class ReturnToAdfs(ResponseMicroService):
    """
    Support a flow where the backend SP will redirect to an IDP-defined location
    if a configuration-defined attribute is set in the response.
    This is a workaround to support interactive flows in ADFS.
    After the redirect and user interactions ADFS will send a second SAMl Response,
    that time without redirect_url.
    """

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirect_url_attr = config['redirect_url_attr']
        logging.info('ReturnToAdfs microservice active')

    def process(self, context, data):
        redirect_url = data.attributes.get(self.redirect_url_attr, [None])[0]
        if redirect_url:
            assert redirect_url.startswith('http')
            redirect = Redirect(redirect_url)
            return redirect
        else:
            return super().process(context, data)
