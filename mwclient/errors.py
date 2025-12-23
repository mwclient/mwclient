from typing import Any, TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:
    import mwclient.page


class MwClientError(RuntimeError):
    """Base class for all mwclient errors."""
    pass


class MediaWikiVersionError(MwClientError):
    """The version of MediaWiki is not supported."""
    pass


class APIDisabledError(MwClientError):
    """The API is disabled on the wiki."""
    pass


class MaximumRetriesExceeded(MwClientError):
    """The maximum number of retries for a request has been exceeded."""
    pass


class APIError(MwClientError):
    """Base class for errors returned by the MediaWiki API.

    Attributes:
        code (Optional[str]): The error code returned by the API.
        info (str): The error message returned by the API.
        kwargs (Optional[Any]): Additional information.
    """

    def __init__(self, code: Optional[str], info: str, kwargs: Optional[Any]) -> None:
        self.code = code
        self.info = info
        super().__init__(code, info, kwargs)


class InsufficientPermission(MwClientError):
    """Raised when the user does not have sufficient permissions to perform an
    action."""
    pass


class UserBlocked(InsufficientPermission):
    """Raised when attempting to perform an action while blocked."""
    pass


class EditError(MwClientError):
    """Base class for errors related to editing pages."""
    pass


class ProtectedPageError(EditError, InsufficientPermission):
    """Raised when attempting to edit a protected page.

    Attributes:
        page (mwclient.page.Page): The page for which the edit attempt was made.
        code (Optional[str]): The error code returned by the API.
        info (Optional[str]): The error message returned by the API.
    """

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
    """
    Raised when trying to upload a file that already exists.

    See also: https://www.mediawiki.org/wiki/API:Upload#Upload_warnings

    Attributes:
        file_name (str): The name of the file that already exists.
    """

    def __init__(self, file_name: str) -> None:
        self.file_name = file_name

    def __str__(self) -> str:
        return (
            f'The file "{self.file_name}" already exists. '
            f'Set ignore=True to overwrite it.'
        )


class LoginError(MwClientError):
    """Base class for login errors.

    Attributes:
        site (mwclient.site.Site): The site object on which the login attempt
            was made.
        code (str): The error code returned by the API.
        info (str): The error message returned by the API.
    """

    def __init__(
        self, site: 'mwclient.client.Site', code: Optional[str], info: str
    ) -> None:
        super().__init__(
            site,
            {'result': code, 'reason': info}  # For backwards-compability
        )
        self.site = site
        self.code = code
        self.info = info

    def __str__(self) -> str:
        return self.info


class OAuthAuthorizationError(LoginError):
    """Raised when OAuth authorization fails.

    Attributes:
        site (mwclient.site.Site): The site object on which the login attempt
            was made.
        code (str): The error code returned by the API.
        info (str): The error message returned by the API.
    """
    pass


class AssertUserFailedError(MwClientError):
    """Raised when the user assertion fails."""
    def __init__(self) -> None:
        super().__init__(
            'By default, mwclient protects you from accidentally editing '
            'without being logged in. If you actually want to edit without '
            'logging in, you can set force_login on the Site object to False.'
        )

    def __str__(self) -> str:
        return cast(str, self.args[0])


class EmailError(MwClientError):
    """Base class for email errors."""
    pass


class NoSpecifiedEmail(EmailError):
    """Raised when trying to email a user who has not specified an email"""
    pass


class InvalidResponse(MwClientError):
    """Raised when the server returns an invalid JSON response.

    Attributes:
        response_text (str): The response text from the server.
    """

    def __init__(self, response_text: Optional[str] = None) -> None:
        super().__init__((
            'Did not get a valid JSON response from the server. Check that '
            'you used the correct hostname. If you did, the server might '
            'be wrongly configured or experiencing temporary problems.'),
            response_text
        )
        self.response_text = response_text

    def __str__(self) -> str:
        return cast(str, self.args[0])


class InvalidPageTitle(MwClientError):
    """Raised when an invalid page title is used."""
    pass


class UserAgentError(MwClientError):
    """Raised when attempting to use a Wikimedia site without a custom
    User-Agent.
    """
    pass
