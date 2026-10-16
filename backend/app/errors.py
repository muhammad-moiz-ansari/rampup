class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status, self.code, self.message, self.retryable = (
            status,
            code,
            message,
            retryable,
        )


def conflict(
    code="INVALID_STATE", message="Operation is incompatible with the current state."
):
    raise AppError(409, code, message)
