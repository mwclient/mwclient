class MwClientError(RuntimeError):
    pass


class MediaWikiVersionError(MwClientError):
    pass


class APIDisabledError(MwClientError):
    pass


class MaximumRetriesExceeded(MwClientError):
    pass


class APIError(MwClientError):

    def __init__(self, code, info, kwargs):
        self.code = code
        self.info = info
        super(APIError, self).__init__(code, info, kwargs)


class InsufficientPermission(MwClientError):
    pass


class UserBlocked(InsufficientPermission):
    pass


class EditError(MwClientError):
    pass


class ProtectedPageError(EditError, InsufficientPermission):

    def __init__(self, page, code=None, info=None):
        self.page = page
        self.code = code
        self.info = info

    def __str__(self):
        if self.info is not None:
            return self.info
        return 'You do not have the "edit" right.'


class FileExists(EditError):
    pass


class LoginError(MwClientError):
    pass


class OAuthAuthorizationError(LoginError):

    def __init__(self, code, info):
        self.code = code
        self.info = info

    def __str__(self):
        return self.info


class AssertUserFailedError(LoginError):

    def __init__(self):
        self.message = 'By default, mwclient protects you from ' + \
                       'accidentally editing without being logged in. If you ' + \
                       'actually want to edit without logging in, you can set ' + \
                       'force_login on the Site object to False.'

        LoginError.__init__(self)

    def __str__(self):
        return self.message


class EmailError(MwClientError):
    pass


class NoSpecifiedEmail(EmailError):
    pass


class NoWriteApi(MwClientError):
    pass


class InvalidResponse(MwClientError):

    def __init__(self, response_text=None):
        self.message = 'Did not get a valid JSON response from the server. Check that ' + \
                       'you used the correct hostname. If you did, the server might ' + \
                       'be wrongly configured or experiencing temporary problems.'
        self.response_text = response_text
        super(InvalidResponse, self).__init__(self.message, response_text)

    def __str__(self):
        return self.message


class InvalidPageTitle(MwClientError):
    pass
