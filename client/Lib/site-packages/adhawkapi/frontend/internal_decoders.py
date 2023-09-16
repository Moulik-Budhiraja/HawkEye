'''Support module to decode internal packets'''

import struct

from .. import internal


def get_decoder(packet_type, _data, _eye_mask):
    '''Gets a decoder for the given packet'''
    try:
        return _INTERNAL_DECODERS[packet_type]
    except KeyError:
        return None


def get_property_parser(property_type):
    '''Gets a property binary format'''
    # pylint: disable=too-many-return-statements
    if property_type == internal.PropertyType.AUTOTUNE_PHYS_MODEL_RESIDUALS:
        return '<BB14f'
    if property_type == internal.PropertyType.SCAN_REGION:
        return '<BBB4f'
    if property_type == internal.PropertyType.SCAN_POWER:
        return '<BBBf'
    if property_type == internal.PropertyType.DETECTOR_SENSITIVITY:
        return '<6B'
    if property_type == internal.PropertyType.PUPIL_OFFSET:
        return '<BBf'
    if property_type == internal.PropertyType.ALGORITHM_PIPELINE:
        return '<BBB'

    return None


_INTERNAL_DECODERS = {
    internal.PacketType.CONTROL: (lambda data: struct.unpack_from('<B', data)),
    internal.PacketType.EMBEDDED_INFO: (lambda data: (data,))
}
