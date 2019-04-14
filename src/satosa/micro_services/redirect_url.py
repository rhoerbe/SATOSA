from .base import ResponseMicroService


class RedirectUrl(ResponseMicroService):
    """
    Return to responder if a certain attribute is set in the response
    """

    def process(self, context, data):
        return super().process(context, data)
