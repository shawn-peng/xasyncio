import unittest
from unittest.mock import patch

from asyncio_utils import *


def _print(*args, **kwargs):
    # print(*args, **kwargs, flush=True)
    pass


class MyTestCase(unittest.TestCase):
    def test_call_sync(self):
        steps = [0]
        loop = ThreadedEventLoop('test_loop')
        steps.append(1)
        loop.call_sync(lambda: (_print('lambda function called'), steps.append(2)))
        steps.append(3)
        _print(loop.stopped)

        self.assertEqual([0, 1, 2, 3], steps)
        loop.stop()
        self.assertEqual(True, loop.stopped)

    async def test_call_async(self):
        steps = [0]
        loop = ThreadedEventLoop('test_loop')
        event = ThreadSafeEvent()
        steps.append(1)
        loop.call_async(lambda: (_print('lambda function called'), steps.append(3), event.set()))
        steps.append(2)
        await event.wait()
        steps.append(4)

        self.assertEqual([0, 1, 2, 3, 4], steps)
        del loop


if __name__ == '__main__':
    unittest.main()
