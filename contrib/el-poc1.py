
import asyncio, fcntl, time

def blah(fmt):
    print(fmt.format('start'))
    with open('/proc/loadavg', 'r') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        time.sleep(0.5)
        l = fh.readline().strip().split()[0]
        print(fmt.format(l))
    return l

async def ablah(fmt):
    return await evloop.run_in_executor(None, blah, fmt)

evloop = asyncio.get_event_loop()
tasks  = [ ablah(f'supz-{i}: {{0}}') for i in range(5) ]
future = asyncio.gather(*tasks)

evloop.run_until_complete(future)
for item in future.result():
    print(f'result: {item}')
