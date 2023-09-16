'''This module facilitates the communication with the AdHawk eye tracking glasses over BLE'''

import asyncio

from bleak import BleakScanner




class FrontendApi:
    '''Provides the APIs for communiating with the AdHawk eye tracking glasses over BLE'''

    def __init__(self):
        pass

    def open(self, devname):
        self._eventloop = asyncio.new_event_loop()
        self.ble_device = ble_device

    def setup_et_callback(self, streams, callback):
        self._et_callback = callback

    def setup_event_callback(self, callback):
        self._event_callback = callback


if __name__ == '__main__':
    api = FrontendApi('ADHAWK MINDLINK-264')
    api.setup_et_callback(['gaze', 'pupil'], print)