'''Support module to encode internal packets'''

import struct

from .. import internal


def get_encoder(packet_type):
    '''Gets an encoder for the given packet'''
    try:
        return _INTERNAL_ENCODERS[packet_type]
    except KeyError:
        return None


def encode_property_get(property_type, *args):
    '''Encodes internal property get'''
    if property_type in (internal.PropertyType.SCAN_REGION, internal.PropertyType.SCAN_POWER):
        eyeindex, = args
        return struct.pack('<B', eyeindex)
    if property_type == internal.PropertyType.DETECTOR_SENSITIVITY:
        eyeindex, detector_type, detector_id = args
        return struct.pack('<3B', eyeindex, detector_type, detector_id)

    return None


def encode_property_set(property_type, *args):
    '''Encodes internal property set'''
    if property_type == internal.PropertyType.SCAN_REGION:
        eyeindex, xmean, ymean, width, height = args
        return struct.pack('<B4f', eyeindex, xmean, ymean, width, height)
    if property_type == internal.PropertyType.SCAN_POWER:
        eyeindex, power = args
        return struct.pack('<Bf', eyeindex, power)
    if property_type == internal.PropertyType.DETECTOR_SENSITIVITY:
        eyeindex, detector_type, detector_id, sensitivity = args
        return struct.pack('<4B', eyeindex, detector_type, detector_id, sensitivity)
    if property_type == internal.PropertyType.PUPIL_OFFSET:
        pupil_offset = args[0]
        return struct.pack('<f', pupil_offset)
    if property_type == internal.PropertyType.ALGORITHM_PIPELINE:
        pipeline_id, = args
        return struct.pack('<B', pipeline_id)

    return None


def _encode_internal_control(control_type, *args):
    msg = struct.pack('<BB', internal.PacketType.CONTROL.value, control_type.value)
    if control_type == internal.ControlType.PULSE_STREAM_CONFIG:
        full_rate, unfilter = args
        return msg + struct.pack('<BB', full_rate, unfilter)
    if control_type in (internal.ControlType.LOG_MODE, internal.ControlType.SCANBOX):
        control_value, = args
        return msg + struct.pack('<B', control_value)
    return msg


_INTERNAL_ENCODERS = {
    # internal packets
    internal.PacketType.CONTROL: _encode_internal_control
}
