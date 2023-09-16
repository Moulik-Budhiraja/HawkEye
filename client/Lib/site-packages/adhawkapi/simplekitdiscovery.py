'''This module provides the ability to discover and connect to AdHawk devices'''

import logging

from . import base, comportdiscovery, error


def get_port(serial_num):
    '''Returns the serial port associated with the specific serial number'''
    available_ports = comportdiscovery.compatible_ports()
    for port in available_ports:
        try:
            api = base.BaseApi(port)
        except error.Error as excp:
            logging.warning(f'Failed to connect to port {port}: {excp}')
        else:
            if api.firmware_info.serial_num == serial_num:
                return port
            api.shutdown()

    raise FileNotFoundError(f'Device not found: {serial_num}')


class DeviceList:
    '''Convenience class to detect all AdHawk devices on the system'''

    def __init__(self):
        self._ports = {}
        # Automatically populate the device list on creation
        self.refresh()

    @property
    def ports(self):
        '''Returns all available ports and their associated serial number'''
        return [(port, serial_num) for port, (serial_num, _) in self._ports.items()]

    @property
    def endpoints(self):
        '''Returns all trackers currently available on the system'''
        return [(port, serial_num, trid)
                for port, (serial_num, active_trackers) in self._ports.items()
                for trid in active_trackers]

    def refresh(self):
        '''Rediscover the list of devices on the system'''
        available_ports = comportdiscovery.compatible_ports()

        deletedports = [(port, api)
                        for port, api in self._ports.items()
                        if port not in available_ports]
        for port, api in deletedports:
            del self._ports[port]

        newports = [port for port in available_ports if port not in self._ports]
        for port in newports:
            try:
                api = base.BaseApi(port)
            except error.Error as excp:
                logging.warning(f'Failed to connect to port {port}: {excp}')
            else:
                self._ports[port] = (api.firmware_info.serial_num,
                                     api.firmware_info.active_trackers)
                api.shutdown()
