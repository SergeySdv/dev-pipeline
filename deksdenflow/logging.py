import logging
from typing import Optional


class RequestIdFilter(logging.Filter):
    def __init__(self, request_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = self.request_id
        return True


def setup_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, str(level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s request_id=%(request_id)s",
    )
    return logging.getLogger("deksdenflow")


def get_logger(name: str = "deksdenflow") -> logging.Logger:
    return logging.getLogger(name)


def init_cli_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Initialize logging for CLI tools using the configured log level (default INFO).
    """
    return setup_logging(level or "INFO")
