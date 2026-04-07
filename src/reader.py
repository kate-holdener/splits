from typing import Protocol
from queue import Queue

import threading
import time

class Reader(Protocol):
    def __init__(self):
        self.thread = None
        self.running = False
        self.queue = None
   
    def _run(self):
        raise NotImplementedError
 
    def start(self, event_queue: Queue):
        self.queue = event_queue
        """Start the reader thread."""
        if self.thread is not None and self.thread.is_alive():
            print("Reader is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the reader thread."""
        self.running = False
        if self.thread is not None:
            self.thread.join()

    def get_protocol(self)->str:
        pass

    def get_address(self)->str:
        pass