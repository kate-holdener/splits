#!/usr/bin/env python

import argparse

import signal
import sys

import requests
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin
import json


def signal_handler(signal, frame):
    sys.exit(0)


def get_command_line_arguments():
    parser = argparse.ArgumentParser(description='This is an example program to interact with a RAIN RFID reader using the Impinj Reader API.')
    parser.add_argument('--reader', action='store', dest='reader', required=True, help='the hostname of the reader supporting the Impinj Reader API. Note that Speedway-based readers will need to include port number 8000, e.g. speedwayr-fa-1a-1a:8000).')
    parser.add_argument('--start', action='store', dest='toStart', help='the preset to start')
    parser.add_argument('--store', action='store', dest='customPresetPath', help='a JSON file containing a preset configuration')
    parser.add_argument('--id', action="store", dest='presetId', help='the id of a preset')
    parser.add_argument('--delete', action='store', dest='toDelete', help='the custom preset to delete')
    parser.add_argument('--details', action='store', dest='details', help='gets the configuration for this preset')
    parser.add_argument('--presets', action='store_true', dest='listPresets', help='lists the current set of presets')
    parser.add_argument('--stop', action='store_true', dest='stop', help='stops the active preset')
    parser.add_argument('--status', action='store_true', dest='status', help='gets the reader status')
    parser.add_argument('--schema', action='store_true', dest='schema', help='gets the inventory preset schema')
    parser.add_argument('--stream', action='store_true', dest='stream', help='connects to the event stream')
    parser.add_argument('--profiles', action='store_true', dest='listProfiles', help="displays the profiles supported by the reader")
    return parser.parse_args()


def check_response(response, print_body=True):
    print('HTTP Response: {0} {1}'.format(response.status_code, response.reason))
    if print_body:
        try:
            print('HTTP Response Body:')
            print(json.dumps(response.json(), indent=4))
        except ValueError:
            print('<empty response>')
    if response.status_code != 200:
        sys.exit(response.status_code)
    print(''.center(80, '='))


def print_request(http_method, request_url):
    print(''.center(80, '='))
    print('{0} {1}'.format(http_method, request_url))
    print(''.center(80, '='))


def main():
    # Handle Ctrl+C interrupt
    signal.signal(signal.SIGINT, signal_handler)

    arguments = get_command_line_arguments()

    hostname = 'http://{0}'.format(arguments.reader)

    try:
        requests.get(urljoin(hostname, '/api/v1/status')).raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError):
        print('Error : Unable to connect to the Impinj Reader API on "{0}"'.format(hostname))
        if len(hostname.split(':')) == 2:
            print('        Have you provided the port number with your reader hostname?')
            print('        ex.  --reader <your-reader-hostname>:<api-port>')
        sys.exit(1)

    if arguments.stop:
        stop_request_url = urljoin(hostname, 'api/v1/profiles/stop')
        print_request('POST', stop_request_url)
        check_response(requests.post(stop_request_url))

    if arguments.schema:
        schema_request_url = urljoin(hostname, '/api/v1/profiles/inventory/presets-schema')
        print_request('GET', schema_request_url)
        check_response(requests.get(schema_request_url))

    if arguments.status:
        status_request_url = urljoin(hostname, '/api/v1/status')
        print_request('GET', status_request_url)
        check_response(requests.get(status_request_url))

    if arguments.toDelete:
        delete_request_url = '{0}/api/v1/profiles/inventory/presets/{1}'.format(hostname, arguments.toDelete)
        print_request('DELETE', delete_request_url)
        check_response(requests.delete(delete_request_url))

    if arguments.customPresetPath:
        with open(arguments.customPresetPath) as customPresetFile:
            # Add or update the provided preset
            try:
                custom_preset = json.load(customPresetFile)
                if arguments.presetId is None:
                    print('Error : An id must be provided for custom presets.')
                    sys.exit(1)
                preset_request_url = '{0}/api/v1/profiles/inventory/presets/{1}'.format(hostname, arguments.presetId)
                print_request('PUT', preset_request_url)
                check_response(requests.put(preset_request_url, data=json.dumps(custom_preset)))
            except ValueError:
                print('Error : the provided custom configuration contains invalid json')
                sys.exit(1)

    if arguments.listPresets:
        get_preset_list_request_url = urljoin(hostname, '/api/v1/profiles/inventory/presets')
        print_request('GET', get_preset_list_request_url)
        check_response(requests.get(get_preset_list_request_url))

    if arguments.details:
        get_preset_details_request_url = '{0}/api/v1/profiles/inventory/presets/{1}'.format(hostname, arguments.details)
        print_request('GET', get_preset_details_request_url)
        check_response(requests.get(get_preset_details_request_url))

    if arguments.toStart:
        start_request_url = '{0}/api/v1/profiles/inventory/presets/{1}/start'.format(hostname, arguments.toStart)
        print_request('POST', start_request_url)
        check_response(requests.post(start_request_url))

    if arguments.stream:
        event_stream_request_url = urljoin(hostname, 'api/v1/data/stream')
        print_request('GET', event_stream_request_url)
        event_stream_response = requests.get(event_stream_request_url, stream=True)
        check_response(event_stream_response, print_body=False)
        for event in event_stream_response.iter_lines():
            print(event)

    if arguments.listProfiles:
        list_profiles_request_url = urljoin(hostname, 'api/v1/profiles')
        print_request('GET', list_profiles_request_url)
        check_response(requests.get(list_profiles_request_url))


if __name__ == "__main__":
    main()
