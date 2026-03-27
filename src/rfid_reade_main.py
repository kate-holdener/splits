from readers.sllurp_reader import LLRPReader
scanner_address = '169.254.1.1'
from queue import Queue
from time import sleep

event_q = Queue()
reader = LLRPReader(event_q, scanner_address)
reader.start()

while True:
    sleep(1)
