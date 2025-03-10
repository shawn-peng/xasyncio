import asyncio
import threading


class ThreadedEventLoop:
    def __init__(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        self.events = {}
        self.events_out_thread = {}
        self.loop = None
        self.create_out_thread_event('loop_started')
        print('waiting for loop to start')
        self.wait_out_thread_event('loop_started')
        print('Threaded Loop is ready for using')

    def run(self):
        self.loop = asyncio.new_event_loop()
        # self.loop = asyncio.get_event_loop()
        # Need to call this in the loop, mainly because need to make sure the loop is running
        self.loop.call_soon_threadsafe(
            lambda: (print('notifying loop started'), self.notify_out_thread_event('loop_started')))
        self.loop.run_forever()

    def create_out_thread_event(self, name):
        self.events_out_thread[name] = threading.Event()

    def wait_out_thread_event(self, name):
        self.events_out_thread[name].wait()

    def notify_out_thread_event(self, name):
        self.events_out_thread[name].set()

    def create_event(self, name):
        self.events[name] = threading.Event()

    def notify(self, event_name):
        self.events[event_name].set()

    def wait(self, event_name):
        self.events[event_name].wait()

    def call(self, func, *args):
        blocking_call_w_loop(self.loop, func, *args)


def blocking_call_w_loop(loop, func, *args):
    finish_event = threading.Event()

    def _helper():
        func(*args)
        finish_event.set()

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
