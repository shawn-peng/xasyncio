import asyncio
import dataclasses
import logging
import threading
import traceback

from typing import *


class ThreadingError(Exception):
    pass


def handle_result(future):
    try:
        # This will trigger the exception if the coroutine failed
        future.result()
    except Exception:
        logging.exception("Exception caught in background thread safe task:")


@dataclasses.dataclass
class AsyncThreadBase:
    # def call_async(self, func, *args):
    #     raise NotImplementedError
    #
    # def call_sync(self, func, *args):
    #     raise NotImplementedError
    #
    # def sync_coroutine(self, coro, timeout=None):
    #     raise NotImplementedError
    #
    # def ensure_coroutine(self, coro):
    #     raise NotImplementedError
    #
    # async def await_coroutine(self, coro):
    #     raise NotImplementedError
    #
    # def stop(self):
    #     raise NotImplementedError
    name: str = ''
    loop: asyncio.AbstractEventLoop | None = None
    events: dict = dataclasses.field(default_factory=dict)
    events_out_thread: dict = dataclasses.field(default_factory=dict)

    def _stop_self(self):
        """this function must be called with this thread"""
        if self.stopped:
            return
        self.loop.stop()
        self.stopped = True

    async def stop(self):
        """thread safe stop function"""
        # Called in other thread

        # thread = threading.current_thread()
        # if thread == self.thread:
        #     print('calling from the loop thread')
        # else:
        #     print('calling from another loop')
        print(f'Threaded loop {self.name} stopping')
        await self.sync_call(self._stop_self)

    def _mark_running(self, running=True):
        # if running:
        #     print('mark running')
        # else:
        #     print('mark stopped')
        self.stopped = not running

    def create_out_thread_event(self, name):
        self.events_out_thread[name] = threading.Event()

    def wait_out_thread_event(self, name):
        self.events_out_thread[name].wait()

    def notify_out_thread_event(self, name):
        # print('notify event', name)
        self.events_out_thread[name].set()

    def create_event(self, name):
        self.events[name] = threading.Event()

    def notify(self, event_name):
        self.events[event_name].set()

    def wait(self, event_name):
        self.events[event_name].wait()

    # def call_blocking(self, func, *args):
    # def call_sync(self, func, *args):
    #     # other thread will be blocked and could result in deadlocks
    #     pass

    async def sync_call(self, func, *args):
        # Called in other thread
        # blocking_call_w_loop(self.loop, func, *args)
        finish_event = asyncio.Event()
        caller_loop = asyncio.get_event_loop()

        def _set_finish_event():
            caller_loop.call_soon_threadsafe(lambda: finish_event.set())

        def _helper():
            # in self thread
            try:
                func(*args)
                _set_finish_event()
            except Exception as e:
                nonlocal exception
                traceback.print_exc()
                exception = e
                _set_finish_event()

        exception = None

        def _ex_handler(e):
            nonlocal exception
            exception = e
            raise exception

        self.loop.set_exception_handler(_ex_handler)

        self.loop.call_soon_threadsafe(_helper)
        await finish_event.wait()
        if exception:
            raise exception

    def async_call(self, func, *args):
        self.loop.call_soon_threadsafe(func, *args)

    # def _sync_coro(self, coro):
    #     if threading.current_thread() != self.thread:
    #         raise ThreadingError('Invalid thread: this function must be called in the loop thread')

    async def run_coroutine(self, coro, timeout=None):
        """may from another thread"""
        # use run_coroutine_threadsafe in the same thread will deadlock
        # so we must check in which thread we are calling this
        # if asyncio.get_event_loop() is self.loop:
        #     raise ThreadingError('Must call sync coroutine from another '
        #                          'thread. Use await run_coroutine(coro) '
        #                          'instead or just use await coro.')
        # return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)
        return await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(coro, self.loop))

    def ensure_coroutine(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(handle_result)
        return future

    # async def run_coroutine(self, coro):

    def blocking_call_w_loop(self, loop, func, *args):
        pass

    # def sync_coroutine_deadlock(self, coro, timeout=None):
    #     finish_event = threading.Event()
    #
    #     async def _helper():
    #         try:
    #             await coro
    #         except Exception as e:
    #             traceback.print_exc()
    #
    #         finish_event.set()
    #
    #     self.loop.call_soon_threadsafe(self.loop.create_task, _helper())
    #     finish_event.wait()


class AsyncThread(threading.Thread, AsyncThreadBase):
    """Class for a new thread"""

    def __init__(self, name):
        # super(AsyncThread, self).__init__()
        threading.Thread.__init__(self)
        AsyncThreadBase.__init__(self)
        self.name = name
        self.events = {}
        self.events_out_thread = {}
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stopped = True
        self.create_out_thread_event('loop_started')
        self.start()
        self.wait_out_thread_event('loop_started')
        logging.debug('AsyncThread init finished and running')

    def __repr__(self):
        return f'<AsyncThread {self.name}>'

    async def stop(self):
        # Called in other thread
        await super().stop()
        res = self.join(1)
        print(res)

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Need to call this in the loop, mainly because need to make sure the loop is running
        # debugging version
        # self.loop.call_soon_threadsafe(
        #     lambda: (
        #         print('notifying loop started'),
        #         self._mark_running(),
        #         print(self.stopped),
        #         self.notify_out_thread_event('loop_started')))

        # self.loop.call_soon_threadsafe(
        # self.loop.call_soon(
        #     lambda: (
        #         self._mark_running(), self.notify_out_thread_event('loop_started')
        #     )
        # )

        async def _notify_running():
            logging.debug('notify running')
            self._mark_running()
            self.notify_out_thread_event('loop_started')

        asyncio.ensure_future(_notify_running())

        logging.info('running loop')
        self.loop.run_forever()
        print(f'Loop ({self.name}) finished')

    def __hash__(self):
        return 0

    def __eq__(self, other):
        return self is other


class AsyncedThread(AsyncThreadBase):
    """Class for converting an existing thread"""

    def __init__(self, name, thread):
        self.thread = thread
        self.loop = asyncio.get_event_loop()
        assert self.loop.is_running()  # we require the loop already running
        self.name = name
        self.events = {}
        self.events_out_thread = {}
        self.stopped = True


class ThreadSafeEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self._loop = asyncio.get_event_loop()
        assert self._loop

    def set(self):
        self._loop.call_soon_threadsafe(super().set)

    def clear(self):
        self._loop.call_soon_threadsafe(super().clear)


class ThreadSafeSemaphore(asyncio.Semaphore):
    pass


async def cross_thread_call(loop: asyncio.BaseEventLoop, func, *args):
    done = ThreadSafeEvent()

    def _helper():
        func(*args)
        done.set()

    loop.call_soon_threadsafe(_helper)
    await done.wait()
