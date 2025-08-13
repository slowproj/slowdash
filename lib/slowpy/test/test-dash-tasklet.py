import asyncio

async def _initialize():
    print("Hello from tasklet")

    
async def _loop():
    print("I'm working. Type Ctrl-c to stop me.")
    await asyncio.sleep(1)

    
async def _finalize():
    print("bye!")

    

if __name__ == '__main__':
    from slowpy.dash import Tasklet
    slowtask = Tasklet()
    slowtask.run()
