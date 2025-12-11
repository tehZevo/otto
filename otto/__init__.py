import asyncio
from .otto import main as _async_main

def main():
    asyncio.run(_async_main())
