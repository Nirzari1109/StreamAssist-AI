"""
Structured logging for observability.
Logs: routing decisions, tool calls, latency, errors, guardrail events.
"""
import logging
import sys
import json
from typing import Optional


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        elif hasattr(record, "__dict__"):
            for k, v in record.__dict__.items():
                if k not in (
                    "name", "msg", "args", "levelname", "levelno",
                    "pathname", "filename", "module", "exc_info",
                    "exc_text", "stack_info", "lineno", "funcName",
                    "created", "msecs", "relativeCreated", "thread",
                    "threadName", "processName", "process", "message",
                ):
                    log_obj[k] = v
        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_tool_call(
    conversation_id: str,
    tool_name: str,
    status: str,
    latency_ms: float,
    error: Optional[str] = None,
):
    logger = get_logger("tool_call")
    extra = {
        "conversation_id": conversation_id,
        "tool_name": tool_name,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        extra["error"] = error
    logger.info("tool_call", extra=extra)


def log_request(
    conversation_id: str,
    intent: str,
    selected_agent: str,
    latency_ms: float,
    guardrail_triggered: bool,
):
    logger = get_logger("request")
    logger.info(
        "request_completed",
        extra={
            "conversation_id": conversation_id,
            "intent": intent,
            "selected_agent": selected_agent,
            "latency_ms": latency_ms,
            "guardrail_triggered": guardrail_triggered,
        },
    )
