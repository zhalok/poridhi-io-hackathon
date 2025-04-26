import random
import asyncio


def get_random_value(values):
    return random.choice(values)


async def do_some_heavy_task():
    ms = get_random_value([100, 150, 200, 300, 600, 500, 1000, 1400, 2500])
    should_throw_error = get_random_value([1, 2, 3, 4, 5, 6, 7, 8]) == 8

    if should_throw_error:
        raise Exception(get_random_value([
            "DB Payment Failure",
            "DB Server is Down",
            "Access Denied",
            "Not Found Error"
        ]))

    await asyncio.sleep(ms / 1000.0)
    return ms
