'''Handles scanning for compatible devices for bringup app'''

import logging
import time
import threading

from . import comportdiscovery
from . import error
from . import register_api


class PortScanner:
    '''Responsible for finding compatible devices

    args:
        new_device_cb(callback(api)): callback to handle new port connection
        log(logging): local logger. Defaults to logging->debug, error, info...
    '''

    def __init__(self, new_device_cb, fault_cb, log=None):
        self._scanthread = None
        self._logger = log if log is not None else logging
        self._run_port_scanner = False
        self._new_device_cb = new_device_cb
        self._fault_cb = fault_cb
        self._start_looking_for_ports()

    def _handle_new_port(self, portname):
        self._logger.debug(f'COM port found: {portname}')
        try:
            # test if this is a compatible device
            api = register_api.RegisterApi(portname, self._fault_cb)
        except error.Error as excp:
            self._logger.debug(f'Invalid port {portname}: {excp}')
            return False

        self._new_device_cb(api)
        return True

    def shutdown(self):
        '''Stops and removes all devices if they are present'''
        self._stop_looking_for_ports()

    def reset_device_connection(self):
        '''Reset and start looking for a new device'''
        # a simple matter of shutting down and letting us re-discover the device
        # we could instantly check for a new device, but if there's a problem when the api is made
        # and the api faults instantly, then it would just loop infinitely.
        self.shutdown()
        self._start_looking_for_ports()

    def _start_looking_for_ports(self):
        '''Launches a thread that scans for ports every second without sleeping the UI'''
        assert self._scanthread is None
        self._logger.debug('Starting port scan')
        self._run_port_scanner = True
        self._scanthread = threading.Thread(target=self._thread_look_for_ports, name='PortScanner')
        self._scanthread.start()

    def _stop_looking_for_ports(self):
        '''Stops the port scanner thread'''
        if self._scanthread is None:
            return
        self._run_port_scanner = False
        self._scanthread.join()
        self._scanthread = None

    def _thread_look_for_ports(self):
        '''Handles scanning for ports when there are no devices connected'''
        while self._run_port_scanner:
            available_ports = comportdiscovery.compatible_ports()
            for newport in available_ports:
                if self._handle_new_port(newport):
                    self._run_port_scanner = False
                    break
            time.sleep(1)
