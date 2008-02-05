class MwClientError(RuntimeError):
	pass

class MediaWikiVersionError(MwClientError):
	pass

	
class HTTPError(MwClientError):
	pass
class HTTPStatusError(MwClientError):
	pass
	
class MaximumRetriesExceeded(MwClientError):
	pass
	
class APIError(MwClientError):
	pass
	
class InsufficientPermission(MwClientError):
	pass
class UserBlocked(InsufficientPermission):
	pass

class EditError(MwClientError):
	pass
class ProtectedPageError(EditError, InsufficientPermission):
	pass
class FileExists(EditError):
	pass
	

class LoginError(MwClientError):
	pass

class EmailError(MwClientError):
	pass
class NoSpecifiedEmail(EmailError):
	pass
	
