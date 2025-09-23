from __future__ import annotations

from time import sleep

from celery import shared_task


@shared_task(name="sample.echo")
def echo(message: str) -> str:
    if not isinstance(message, str):
        raise TypeError("message must be a string")
    return f"echo: {message}"


@shared_task(name="sample.add")
def add(x: int, y: int) -> int:
    return x + y


@shared_task(name="sample.slow")
def slow(seconds: float = 1) -> str:
    # Support fractional seconds and avoid negative sleep
    try:
        secs = float(seconds)
    except Exception:
        secs = 0.0
    sleep(max(0.0, secs))
    return f"slept {seconds}s"
