"""
Viora – backend entry point.
Forces WindowsSelectorEventLoopPolicy on Windows so that psycopg's async driver
works correctly (uvicorn defaults to ProactorEventLoop on Windows which is
incompatible with psycopg async).
"""
import asyncio
import sys

# Must be done BEFORE uvicorn imports anything so that the child worker process
# also inherits the correct policy through the reload mechanism.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        loop="asyncio",   # explicitly selects the asyncio loop impl (Selector on Win)
    )
