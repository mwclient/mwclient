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


class NotFound(APIError):

    def __init__(self, entity_type, code='missing', info=None, kwargs=None):
        if not info:
            info = 'Entity "%s" has not been found.' % entity_type
        self.entity_type = entity_type
        super(NotFound, self).__init__(code, info, kwargs)


class CreateError(APIError):

    def __init__(self, entity_type, code=None, info=None, kwargs=None):
        if not info:
            info = 'Entity "%s" can not been created.' % entity_type
        self.entity_type = entity_type
        super(CreateError, self).__init__(code, info, kwargs)


class UserNotFound(NotFound):

    def __init__(self, *args, **kwargs):
        super(UserNotFound, self).__init__('User', *args, **kwargs)


class UserCreateError(CreateError):

    def __init__(self, *args, **kwargs):
        super(UserCreateError, self).__init__('User', *args, **kwargs)


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

    def __init__(self, site, code, info):
        super(LoginError, self).__init__(
            site,
            {'result': code, 'reason': info}  # For backwards-compability
        )
        self.site = site
        self.code = code
        self.info = info

    def __str__(self):
        return self.info


class OAuthAuthorizationError(LoginError):
    pass


class AssertUserFailedError(MwClientError):

    def __init__(self):
        super(AssertUserFailedError, self).__init__((
            'By default, mwclient protects you from accidentally editing '
            'without being logged in. If you actually want to edit without '
            'logging in, you can set force_login on the Site object to False.'
        ))

    def __str__(self):
        return self.args[0]


class EmailError(MwClientError):
    pass


class NoSpecifiedEmail(EmailError):
    pass


class NoWriteApi(MwClientError):
    pass


class InvalidResponse(MwClientError):

    def __init__(self, response_text=None):
        super(InvalidResponse, self).__init__((
            'Did not get a valid JSON response from the server. Check that '
            'you used the correct hostname. If you did, the server might '
            'be wrongly configured or experiencing temporary problems.'),
            response_text
        )
        self.response_text = response_text

    def __str__(self):
        return self.args[0]


class InvalidPageTitle(MwClientError):
    pass
