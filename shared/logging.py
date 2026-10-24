"""Structured JSON logs keyed by incident_id / task_id / agent. Owner: D1; D2 imports get_logger."""
import json
import logging
import sys

_FIELDS = ("incident_id", "task_id", "agent", "latency_ms", "status")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname,
               "logger": record.name, "msg": record.getMessage()}
        for f in _FIELDS:
            if hasattr(record, f):
                out[f] = getattr(record, f)
        return json.dumps(out, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"supplyshock.{name}")
    if not logger.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(_JsonFormatter())
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_task(logger: logging.Logger, msg: str, *, incident_id="", task_id="", agent="",
             latency_ms=0, status="ok", level=logging.INFO) -> None:
    logger.log(level, msg, extra={"incident_id": incident_id, "task_id": task_id, "agent": agent,
                                  "latency_ms": latency_ms, "status": status})
