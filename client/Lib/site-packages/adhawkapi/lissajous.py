'''This module provides lissajous-based tracking related APIs'''

import enum
import functools
import math

from . import decoders, baseapp, registers
from .capi.py import libtrackerinfo
from .internal import PacketType as InternalPacketType
from .publicapi import PacketType
from .version import SemanticVersion


class MegaLissajous(baseapp.BaseAppApi, app_id=5):
    '''Python frontend for AdHawk's lissajous-based tracking API'''

    class DataType(enum.IntEnum):
        '''Tracker common data types'''
        LISSAJOUS_DATA = 0

    @staticmethod
    def _handle_raw_pulse_v3(func, packet):
        timestamp, trid, pdid, x_phase, y_phase, pulse_width = \
            decoders.decode(InternalPacketType.RAW_PULSE_V3, packet.payload, [libtrackerinfo.get_eye_mask()])
        func(timestamp, trid, pdid, x_phase, y_phase, pulse_width)

    def _handle_megalisa_pulse(self, func, packet):
        trid = packet.metadata.src_id
        refstamp, xpos, ypos, _amp, pulse_width, pdid = packet.unpack_payload('<HHHHHH')
        scale_factor = math.pi / 4096
        xpos *= scale_factor
        ypos *= scale_factor
        pulse_width *= scale_factor
        func(refstamp, trid, pdid, xpos, ypos, pulse_width)

    def set_stream_enable(self, enable, trid):
        '''Enable/disable megalisa stream'''
        # ensure in-flight packets are stopped when the stream is stopped
        self.set_register(registers.MEGALISA_STREAM_ENABLE, int(enable), trid)

    def add_callback_lissajous_data(self, func):
        '''Add callback to retrieve timestamp, trid, pdid, x phase, y phase, and pulse width'''
        if SemanticVersion.compare(self.firmware_info.api_version, SemanticVersion(0, 111, 0)) >= 0:
            self._callbacks.add_callback(functools.partial(self._handle_raw_pulse_v3, func),
                                         InternalPacketType.RAW_PULSE_V3, key=func)
        else:
            self._callbacks.add_callback(functools.partial(self._handle_megalisa_pulse, func),
                                         self.DataType.LISSAJOUS_DATA << 4 | self._app_id, key=func)

    def add_tracker_status_callback(self, report_stream_cb):
        '''Add callback to retrieve tracker status'''
        self._callbacks.add_callback(lambda pkt: report_stream_cb(*pkt.unpack_payload('<B')),
                                     PacketType.TRACKER_STATUS, key=report_stream_cb)
