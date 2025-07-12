import asyncio
import threading
import traceback

from typing import *


class ThreadingError(Exception):
    pass


class AsyncThread(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.events = {}
        self.events_out_thread = {}
        self.loop: asyncio.BaseEventLoop | None = None
        self.stopped = True
        self.start()
        self.create_out_thread_event('loop_started')
        self.wait_out_thread_event('loop_started')

    def _stop(self):
        """this function must be called with the thread"""
        if self.stopped:
            return
        self.loop.stop()
        self.stopped = True

    def stop(self):
        """thread safe stop function"""
        # thread = threading.current_thread()
        # if thread == self.thread:
        #     print('calling from the loop thread')
        # else:
        #     print('calling from another loop')
        print(f'Threaded loop {self.name} stopping')
        self.call_sync(self._stop)
        # self.thread.join(10)
        self.join(10)

    def _mark_running(self, running=True):
        # if running:
        #     print('mark running')
        # else:
        #     print('mark stopped')
        self.stopped = not running

    def run(self):
        self.loop = asyncio.new_event_loop()
        # Need to call this in the loop, mainly because need to make sure the loop is running
        # debugging version
        # self.loop.call_soon_threadsafe(
        #     lambda: (
        #         print('notifying loop started'),
        #         self._mark_running(),
        #         print(self.stopped),
        #         self.notify_out_thread_event('loop_started')))
        self.loop.call_soon_threadsafe(
            lambda: (
                self._mark_running(), self.notify_out_thread_event('loop_started')
            )
        )

        self.loop.run_forever()
        print(f'Loop ({self.name}) finished')

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

    def call_sync(self, func, *args):
        blocking_call_w_loop(self.loop, func, *args)

    def call_async(self, func, *args):
        self.loop.call_soon_threadsafe(func, *args)

    # def _sync_coro(self, coro):
    #     if threading.current_thread() != self.thread:
    #         raise ThreadingError('Invalid thread: this function must be called in the loop thread')

    def await_coroutine(self, coro, timeout=None):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

        # finish_event = threading.Event()
        #
        # async def _helper():
        #     try:
        #         await coro
        #     except Exception as e:
        #         traceback.print_exc()
        #
        #     finish_event.set()
        #
        # self.loop.call_soon_threadsafe(self.loop.create_task, _helper())
        # finish_event.wait()


class AsyncedThread:
    def __init__(self, name, thread):
        self.thread = thread
        self.loop = asyncio.get_event_loop()
        assert self.loop.is_running()  # we require the loop already running
        self.name = name
        self.events = {}
        self.events_out_thread = {}
        self.stopped = True

    def _stop(self):
        """this function must be called with the thread"""
        if self.stopped:
            return
        self.loop.stop()
        self.stopped = True

    def stop(self):
        """thread safe stop function"""
        # thread = threading.current_thread()
        # if thread == self.thread:
        #     print('calling from the loop thread')
        # else:
        #     print('calling from another loop')
        print(f'Threaded loop {self.name} stopping')
        self.call_sync(self._stop)
        # self.thread.join(10)
        self.join(10)

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

    def call_sync(self, func, *args):
        blocking_call_w_loop(self.loop, func, *args)

    def call_async(self, func, *args):
        self.loop.call_soon_threadsafe(func, *args)

    # def _sync_coro(self, coro):
    #     if threading.current_thread() != self.thread:
    #         raise ThreadingError('Invalid thread: this function must be called in the loop thread')

    def await_coroutine(self, coro, timeout=None):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

        # finish_event = threading.Event()
        #
        # async def _helper():
        #     try:
        #         await coro
        #     except Exception as e:
        #         traceback.print_exc()
        #
        #     finish_event.set()
        #
        # self.loop.call_soon_threadsafe(self.loop.create_task, _helper())
        # finish_event.wait()


def blocking_call_w_loop(loop, func, *args):
    finish_event = threading.Event()

    def _helper():
        try:
            func(*args)
            finish_event.set()
        except Exception:
            traceback.print_exc()

    loop.call_soon_threadsafe(_helper)
    finish_event.wait()


class ThreadSafeEvent(asyncio.Event):
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
