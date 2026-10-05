import unittest

import xasyncio
from xasyncio import *

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
