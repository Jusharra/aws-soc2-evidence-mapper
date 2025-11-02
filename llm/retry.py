from __future__ import annotations
import random, time
from typing import Callable, TypeVar

T = TypeVar("T")

def retry(fn: Callable[[], T], *, attempts: int = 4, base: float = 0.4, cap: float = 5.0) -> T:
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # network/5xx/throughput
            last_exc = e
            sleep = min(cap, base * (2 ** i)) * (0.5 + random.random())
            time.sleep(sleep)
    raise last_exc  # bubble up after retries
