import logging
import os
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
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s %(message)s request_id=%(request_id)s',
    )
    logger = logging.getLogger("deksdenflow")
    return logger


def get_logger(name: str = "deksdenflow") -> logging.Logger:
    return logging.getLogger(name)
