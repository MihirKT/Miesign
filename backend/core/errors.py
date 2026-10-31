from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class AppError(Exception):
    def __init__(self, code, message, status=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or []


def _body(code, message, status, details):
    return {"error": {"code": code, "message": message, "status": status, "details": details}}


def exception_handler(exc, context):
    if isinstance(exc, AppError):
        return Response(_body(exc.code, exc.message, exc.status, exc.details), status=exc.status)
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        response.data = _body(
            "NOT_FOUND" if response.status_code == 404 else "BAD_REQUEST",
            str(detail or "Request could not be processed."),
            response.status_code,
            [] if detail else response.data,
        )
    return response
