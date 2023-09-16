'''This module provides the base class as well as the common APIs for all
Adhawk's applications
'''

import logging
import os

import adhawktools

from . import error, packet, registers
from .capi.py import libbaseapi, libtracker_com, libtrackerinfo
from .kitinfo import KitInfo, get_active_eyes_and_trackers
from .version import SemanticVersion


class MinimumAPIVersion(error.Error):
    '''Version of embedded application is not able to program with this GUI'''
    pass


class BaseApi:
    '''Base API class to manage common communication and validation tasks'''

    _callbacks = adhawktools.StandaloneMultiNotification()
    _fault_callbacks = adhawktools.StandaloneNotification()
    _firmware_info = None

    def __init__(self, portname=None, fault_cb=None, ignore_fault=False):
        self._portname = libtracker_com.get_descr()
        if self._portname is None:
            self._create_com(portname, fault_cb, ignore_fault)
            logging.info(f'Opened port {portname}')
            self._portname = libtracker_com.get_descr()
        elif fault_cb is not None:
            self._fault_callbacks.add_callback(fault_cb)

        if self._firmware_info is None:
            self._build_firmware_info()

    @property
    def portname(self):
        '''Returns portname this API instance is using to communicate to firmware'''
        return self._portname

    @property
    def firmware_info(self):
        '''Returns identification information retrieved from the firmware'''
        return self._firmware_info

    def remove_callback(self, func):
        '''Remove a callback from the underlying com layer'''
        self._callbacks.remove_callback(func)

    @staticmethod
    def shutdown():
        '''Shutsdown the communication to microcontroller and closes the port'''
        libbaseapi.deinit()
        BaseApi._firmware_info = None

    @staticmethod
    def stats():
        '''Returns the number of received / dropped packets'''
        return libtracker_com.received(), libtracker_com.dropped()

    def _create_com(self, portname, fault_cb, ignore_fault):
        if not portname:
            raise error.Error('No open port found')

        if os.path.islink(portname):
            portname = os.path.realpath(portname)

        self._callbacks.reset()
        self._fault_callbacks.reset()
        if fault_cb is not None:
            self._fault_callbacks.add_callback(fault_cb)

        self._fault_cb = libtracker_com.FAULT_CB(self._handle_fault)
        self._stream_cb = libtracker_com.PACKET_CB(self._handle_stream)

        if 'spi' in portname:
            params = libtracker_com.spi_params(portname)
        else:
            params = libtracker_com.usb_params(portname)

        libbaseapi.init(params, self._stream_cb, self._fault_cb, ignore_fault)

    def _build_firmware_info(self):
        active_eyes, active_trackers = get_active_eyes_and_trackers(libtrackerinfo.get_eye_mask())
        BaseApi._firmware_info = KitInfo(
            libtrackerinfo.get_serial_number(),
            tuple(active_eyes),
            tuple(active_trackers),
            registers.SpecProductId(libtrackerinfo.get_product_id()),
            registers.SpecCamera(libtrackerinfo.get_camera_type()),
            False,
            SemanticVersion.from_string(libtrackerinfo.get_api_version()),
            libtrackerinfo.get_firmware_version())

    def _rebuild_firmware_info(self):
        '''Reloads the tracker info api and rebuilds firmware info'''
        if libtrackerinfo.reload():
            self._build_firmware_info()

    def _handle_stream(self, packet_data, packet_len):
        '''Helper routine invoked by the messenger to handle received packets'''
        data = bytes(packet_data[:packet_len])

        try:
            pkt = packet.PacketV3Factory.construct_from_raw(data)
        except NotImplementedError:
            return

        assert pkt.metadata.stream

        enc_app_id = ord(pkt.header) | pkt.metadata.error << 8
        self._callbacks.notify_callbacks(enc_app_id, pkt)

    def _handle_fault(self):
        '''Helper routine invoked by messenger to handle exceptions'''
        logging.debug('Tracker got disconnected')
        self._fault_callbacks.notify_callbacks()
