"""HTTP status codes used across the project."""


class HttpStatus:
    OK = 200
    BAD_REQUEST = 400
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500

    # Retry when status is this high or above (5xx family).
    SERVER_ERROR_MIN = 500
