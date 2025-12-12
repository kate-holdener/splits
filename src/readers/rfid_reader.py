import requests

class RFIDReader(Reader):
    def __init__(self, queue, scanner_address):
        super(queue)
        self.scanner = scanner_address
        self.hostname = 'https://root:impinj@{0}'.format(scanner_address)

    def _run(self):
        requests.post(urljoin(self.hostname, 'api/v1/profiles/stop'), verify=False) # Stop the active preset
        requests.post(urljoin(self.hostname, 'api/v1/profiles/inventory/presets/default/start'), verify=False) # Start the default preset
        while self.running:
            for event_data in requests.get(urljoin(self.hostname, 'api/v1/data/stream'),verify=False, stream=True).iter_lines(): # Connect to the event stream
                event = Event();
                event.timestamp = event_data.time;
                event.id = event_data.
                self.queue.put(event)
