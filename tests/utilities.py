"""
Shared utilities for running tests.
"""

import asyncio


async def delay_close(time=30, log_fn=print):
    if time <= 0:
        raise ValueError("time must be > 0")
    try:
        for countdown in range(time, 0, -1):
            await asyncio.sleep(1)
            log_fn(f"{countdown:2} second{'s' if countdown > 1 else ''} remaining...")
    except Exception as e:
        raise e


async def wait_async(t):
    return await asyncio.sleep(t)
