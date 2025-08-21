"""Lightweight MQTT broker runner for local test runs.

Usage: . .venv/bin/activate && python scripts/run_local_broker.py
This will block running the broker until terminated.
"""
import asyncio
from hbmqtt.broker import Broker

CONFIG = {
    'listeners': {
        'default': {
            'type': 'tcp',
            'bind': '127.0.0.1:1883'
        }
    },
    'sys_interval': 10,
    'topic-check': {
        'enabled': False
    }
}

async def start_broker():
    broker = Broker(CONFIG)
    await broker.start()
    # Run forever
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(start_broker())
    except KeyboardInterrupt:
        pass
