
import asyncio
import random, time

# copied from https://asyncio.readthedocs.io/en/latest/producer_consumer.html
# but, modified to taste (obviously)

class DT:
    def __init__(self, base=1):
        self.b = base
        self.t = 0
    async def rwait(self):
        self.ldt = dt = self.b + random.random()
        await asyncio.sleep(dt)
        self.t += dt

async def produce(queue, n):
    t = DT(0.3)
    for _ in range(n):
        await t.rwait()
        item = f'item-{t.t:0.1f}'
        print(f'produced {item}')
        await queue.put(item)
    print(f'produced FIN')
    await queue.put(None) # FIN

async def consume(queue):
    t = DT(0.7)
    item = await queue.get()
    while item:
        print(f'consumed {item}')
        await t.rwait()
        item = await queue.get()
    print(f'consumed FIN')

loop = asyncio.get_event_loop()
queue = asyncio.Queue(loop=loop)
producer_coro = produce(queue, 3)
consumer_coro = consume(queue)
loop.run_until_complete(asyncio.gather(producer_coro, consumer_coro))
loop.close()
