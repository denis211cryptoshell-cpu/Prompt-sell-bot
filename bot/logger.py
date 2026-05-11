import logging
import sys
from pathlib import Path

from loguru import logger


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(log_level: str = "INFO", debug: bool = False) -> None:
    """Configure loguru logger with console + file output."""

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler — colorful, human-readable
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level if not debug else "DEBUG",
        colorize=True,
        enqueue=True,
    )

    # File handler — daily rotation, keep 7 days
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        format=file_format,
        level="DEBUG",
        rotation="00:00",       # rotate at midnight
        retention="7 days",     # keep 7 days
        compression="zip",      # compress old logs
        enqueue=True,
        encoding="utf-8",
    )

    # Intercept standard logging (aiogram, SQLAlchemy, asyncpg, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Silence noisy libraries in non-debug mode
    if not debug:
        for noisy in ("aiogram.event", "aiohttp.access"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.info("Logger configured | level={} debug={}", log_level, debug)
