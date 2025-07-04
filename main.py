from tasks.kafka import kafka_task
from tasks.rib import rib_task
from tasks.sender import sender_task
from tasks.logging import logging_task
from concurrent.futures import ThreadPoolExecutor
from config import Config
from libs.bmp import BMPv3
import queue as queueio
import rocksdbpy
import threading
import asyncio
import logging
import signal
import os

# Validate the configuration
Config.validate()

# Logger
logger = logging.getLogger(__name__)
log_level = Config.LOG_LEVEL
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Add console handler if none exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Signal handler
def handle_shutdown(signum, frame, event):
    """
    Signal handler for shutdown.

    Args:
        signum (int): The signal number.
        frame (frame): The signal frame.
        shutdown_event (asyncio.Event): The shutdown event.
    """
    logger.info(f"Signal {signum}. Triggering shutdown...")
    event.set()

# Main Coroutine
async def main():
    memory = {
        'task': None,
        'time_lag': {},
        'bytes_sent': 0,
        'bytes_received': 0,
        'rows_processed': 0,
    }

    events = {
        'injection': threading.Event(),
        'shutdown': threading.Event(),
    }

    # Queue
    queue = queueio.Queue(maxsize=10000000)

    # Executor
    executor = ThreadPoolExecutor(max_workers=4)

    # Database
    db = rocksdbpy.open_default("/var/lib/rocksdb")

    try:
        logger.info("Starting up...")

        # Register SIGTERM handler
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None, events['shutdown'])
        loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None, events['shutdown'])  # Handle Ctrl+C

        # Validate database state
        if db.get(b'started') == b'\x01':
            if not db.get(b'ready') == b'\x01':
                # Database is in an inconsistent state
                raise RuntimeError("Corrupted database")

        # Initialize the BMP connection
        message = BMPv3.init_message(
            router_name=f'{Config.HOST}.ripe.net' if Config.HOST.startswith('rrc') else Config.HOST,
            router_descr=f'{Config.HOST}.ripe.net' if Config.HOST.startswith('rrc') else f'{Config.HOST}.routeviews.org'
        )
        queue.put((message, 0, None, -1, False))

        # Start tasks
        loop.run_in_executor(executor, rib_task, queue, db, logger, events, memory)
        loop.run_in_executor(executor, kafka_task, queue, db, logger, events, memory)
        loop.run_in_executor(executor, sender_task, queue, db, logger, events, memory)
        loop.run_in_executor(executor, logging_task, queue, logger, events, memory)

        # Wait for the shutdown event
        events['shutdown'].wait()
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        logger.info("Shutting down...")

        # Shutdown the executor
        executor.shutdown(wait=False, cancel_futures=True)

        logger.info("Shutdown complete.")

        # Terminate
        os._exit(1)

if __name__ == "__main__":
    asyncio.run(main())