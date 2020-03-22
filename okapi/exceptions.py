class APIClientError(Exception):
    response = None
    data = {}
    code = -1
    message = "An unknown error occurred"

    def __init__(self, message=None, code=None, data=None, response=None):
        if data is None:
            data = {}

        self.response = response
        if message:
            self.message = message
        if code:
            self.code = code
        if data:
            self.data = data

    def __str__(self):
        if self.code:
            return '{}: {}'.format(self.code, self.message)
        return self.message


class BadRequestError(APIClientError):
    message = 'Invalid parameters given'


class GeneralInternalHostError(APIClientError):
    message = 'Internal host error'
