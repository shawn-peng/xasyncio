import asyncio
import dataclasses
import functools
import signal
import threading
import time
import unittest
from unittest.mock import patch

import sys

import xasyncio


def is_debugging():
    return sys.gettrace() is not None or 'pydevd' in sys.modules

print(f"Is debugger active? {is_debugging()}")

from xasyncio import *


def _print(*args, **kwargs):
    # print(*args, **kwargs, flush=True)
    pass


def set_async_timeout(timeout):
    """Not working under thread blocking case"""

    def _set_async_timeout(f):
        assert asyncio.iscoroutinefunction(f)

        @functools.wraps(f)
        async def _f(*args):
            await asyncio.wait_for(f(*args), timeout)

        return _f

    return _set_async_timeout if not is_debugging() else lambda f: f


async def timer(t, coro):
    await asyncio.sleep(t)
    return await coro


def set_deadline(timeout):
    signal.setitimer(signal.ITIMER_REAL, timeout)


def create_deadline(t):
    async def _on_timeout():
        raise TimeoutError

    return asyncio.create_task(timer(t, _on_timeout()))


class BaseTestCases:
    class AsyncThreadTestBase(unittest.IsolatedAsyncioTestCase):
        async def asyncSetUp(self) -> None:
            self.loop: AsyncThreadBase | None = None
            # self.loop = AsyncThread('test_loop')
            # self.deadline = create_deadline(1)
            # set_deadline(1)

        # @set_async_timeout(1)
        async def test_call_sync(self):
            # in Main thread
            steps = [0]
            loop = self.loop
            steps.append(1)
            await loop.sync_call(
                lambda: (print('lambda function called'), steps.append(2)))
            steps.append(3)
            print(loop.stopped)

            self.assertEqual([0, 1, 2, 3], steps)
            # loop.stop()
            # self.assertEqual(True, loop.stopped)

        # @set_async_timeout(1)
        async def test_call_sync_raise_ex(self):
            # in Main thread
            steps = [0]
            loop = self.loop
            steps.append(1)

            def _test_func_w_ex():
                print('lambda function called')
                steps.append(2)
                raise Exception('test ex')

            with self.assertRaises(Exception) as cm:
                await loop.sync_call(_test_func_w_ex)
            self.assertEqual(str(cm.exception), 'test ex')
            steps.append(3)
            print(loop.stopped)

            self.assertEqual([0, 1, 2, 3], steps)

        async def test_ensure_coroutine_raise_ex(self):
            steps = [0]
            loop = self.loop

            async def _test_coro():
                steps.append(1)
                raise Exception('test ex')

            loop.ensure_coroutine(_test_coro())

            steps.append(1)
            await asyncio.sleep(.1)
            self.assertEqual([0, 1, 1], steps)

        # @set_async_timeout(1)
        async def test_async_call(self):
            steps = [0]
            loop = self.loop
            # loop = AsyncedThread('test_loop', threading.current_thread())
            event = ThreadSafeEvent()
            steps.append(1)
            loop.async_call(
                lambda: (print('lambda function called'), steps.append(2),
                         event.set()))
            steps.append(2)
            await event.wait()
            steps.append(3)

            self.assertEqual([0, 1, 2, 2, 3], steps)
            # del loop

        @set_async_timeout(1)
        async def test_run_coro(self):
            steps = [0]
            loop = self.loop

            async def _test_coro():
                print('coroutine called')
                steps.append(2)

            async def _test_in_thread():
                steps.append(1)
                await loop.run_coroutine(_test_coro())
                steps.append(3)

            async with AsyncThread('stub_thread') as t:
                await t.run_coroutine(_test_in_thread())

                self.assertEqual([0, 1, 2, 3], steps)
                # print('stopping stub thread')
                # await t.stop()
                # print('stopping threaded loop')
                # loop.stop()

        # @set_async_timeout(1)
        # async def test_sync_coro(self):
        #     steps = [0]
        #     loop = self.loop
        #
        #     async def _test_coro():
        #         print('coroutine called')
        #         steps.append(2)
        #
        #     def _test_in_thread():
        #         steps.append(1)
        #         loop.sync_coroutine(_test_coro())
        #         steps.append(3)
        #
        #     t = AsyncThread('stub_thread')
        #     await t.call_sync(_test_in_thread)
        #
        #     self.assertEqual([0, 1, 2, 3], steps)
        #     print('stopping stub thread')
        #     await t.stop()
        #     print('stopping threaded loop')
        #     # loop.stop()

        # @set_async_timeout(1)
        async def test_async_coro(self):
            steps = [0]
            loop = self.loop

            async def _test_coro():
                print('coroutine called')
                steps.append(1)

            loop.ensure_coroutine(_test_coro())
            steps.append(1)
            await asyncio.sleep(.1)
            self.assertEqual([0, 1, 1], steps)
            print('stopping threaded loop')
            # loop.stop()

        async def test_sleep(self):
            steps = [0]
            loop = self.loop

            async def loop_func():
                steps.append(1)
                await asyncio.sleep(.1)
                steps.append(2)

            loop.ensure_coroutine(loop_func())
            await asyncio.sleep(2)
            steps.append(3)
            self.assertEqual([0, 1, 2, 3], steps)

        async def test_exc_handle(self):
            steps = [0]
            loop = self.loop

            def loop_func():
                steps.append(1)
                raise (Exception('test ex'))

            thread = threading.current_thread()
            async def _test_exc_handle():
                self.assertIs(thread, threading.current_thread())
                steps.append(2)

            await loop.register_exception_handler(_test_exc_handle)
            loop.async_call(loop_func)
            await asyncio.sleep(1)
            self.assertEqual([0, 1, 2], steps)


class AsyncThreadTestCase(BaseTestCases.AsyncThreadTestBase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.loop = AsyncThread('test_loop')
        await self.loop.__aenter__()

    async def asyncTearDown(self) -> None:
        # await self.loop.stop()
        await self.loop.__aexit__(*sys.exc_info())
        self.assertEqual(True, self.loop.stopped)


class AsyncThreadUsingEnterTestCase(BaseTestCases.AsyncThreadTestBase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.loop = AsyncThread('test_loop')
        self.loop.enter()

    async def asyncTearDown(self) -> None:
        await self.loop.stop()
        self.assertEqual(True, self.loop.stopped)
        await super().asyncTearDown()


class AsyncedThreadTestCase(BaseTestCases.AsyncThreadTestBase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.loop = AsyncedThread('test_loop', threading.current_thread())


class AsyncQueueTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_queue_put_get_in_one_thread(self) -> None:
        q = AsyncQueue()
        await q.put(1)
        await q.put(2)
        self.assertEqual(1, await q.get())
        self.assertEqual(2, await q.get())

    async def test_queue_get_in_wrong_thread(self) -> None:
        q = AsyncQueue()
        await q.put(1)

        async def test_in_thread():
            item = await q.get()
            print('got item', item)

        async with AsyncThread('test_loop') as t:
            await q.put(1)

            with self.assertRaises(Exception) as cm:
                await t.run_coroutine(test_in_thread())
            self.assertEqual(str(cm.exception),
                             'Not called in the owner thread')

    async def test_queue_put_in_another_thread(self) -> None:
        q = AsyncQueue()

        async def test_in_thread():
            await q.put(1)

        async with AsyncThread('test_loop') as t:
            await t.run_coroutine(test_in_thread())
            res = await q.get()
            self.assertEqual(1, res)


if __name__ == '__main__':
    unittest.main()
