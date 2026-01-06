import asyncio
import threading

from .utils import ThreadingError


# from xasyncio import ThreadingError


class AsyncQueue(asyncio.Queue):
    """Thread safe queue. Can be put by different threads, but can only be
    gotten from the owner thread."""

    def __init__(self):
        super().__init__()
        self.loop = asyncio.get_event_loop()
        self.thread = threading.current_thread()

    async def put(self, item):
        asyncio.run_coroutine_threadsafe(super().put(item), self.loop)

    async def get(self):
        if threading.current_thread() is not self.thread:
            raise ThreadingError('Not called in the owner thread')
        return await super().get()
