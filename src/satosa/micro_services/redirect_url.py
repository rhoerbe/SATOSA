import logging
from .base import ResponseMicroService
from satosa.response import Redirect


class RedirectUrl(ResponseMicroService):
    """
    Return to responder if a certain attribute is set in the response
    """

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.info('RedirectUrl microservice active')

    def process(self, context, data):
        redirect_url = data.attributes.get('RedirectUrl', None)[0]
        if redirect_url:
            redirect = Redirect(redirect_url)
            return redirect
        else:
            return super().process(context, data)
