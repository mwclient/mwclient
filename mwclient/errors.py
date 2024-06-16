from typing import Any, TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:
    import mwclient.page


class MwClientError(RuntimeError):
    pass


class MediaWikiVersionError(MwClientError):
    pass


class APIDisabledError(MwClientError):
    pass


class MaximumRetriesExceeded(MwClientError):
    pass


class APIError(MwClientError):

    def __init__(self, code: Optional[str], info: str, kwargs: Optional[Any]) -> None:
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

    def __init__(
        self,
        page: 'mwclient.page.Page',
        code: Optional[str] = None,
        info: Optional[str] = None
    ) -> None:
        self.page = page
        self.code = code
        self.info = info

    def __str__(self) -> str:
        if self.info is not None:
            return self.info
        return 'You do not have the "edit" right.'


class FileExists(EditError):
    pass


class LoginError(MwClientError):

    def __init__(
        self, site: 'mwclient.client.Site', code: Optional[str], info: str
    ) -> None:
        super(LoginError, self).__init__(
            site,
            {'result': code, 'reason': info}  # For backwards-compability
        )
        self.site = site
        self.code = code
        self.info = info

    def __str__(self) -> str:
        return self.info


class OAuthAuthorizationError(LoginError):
    pass


class AssertUserFailedError(MwClientError):

    def __init__(self) -> None:
        super(AssertUserFailedError, self).__init__((
            'By default, mwclient protects you from accidentally editing '
            'without being logged in. If you actually want to edit without '
            'logging in, you can set force_login on the Site object to False.'
        ))

    def __str__(self) -> str:
        return cast(str, self.args[0])


class EmailError(MwClientError):
    pass


class NoSpecifiedEmail(EmailError):
    pass


class NoWriteApi(MwClientError):
    pass


class InvalidResponse(MwClientError):

    def __init__(self, response_text: Optional[str] = None) -> None:
        super(InvalidResponse, self).__init__((
            'Did not get a valid JSON response from the server. Check that '
            'you used the correct hostname. If you did, the server might '
            'be wrongly configured or experiencing temporary problems.'),
            response_text
        )
        self.response_text = response_text

    def __str__(self) -> str:
        return cast(str, self.args[0])


class InvalidPageTitle(MwClientError):
    pass
