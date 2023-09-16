'''Module that provides decoders for internal packets'''

import math
import struct

from adhawkapi import frontend, internal


def _decode_raw_pulse_v2(data):
    tid_pdid, timestamp, xphase, yphase, pulse_width = struct.unpack('<BfHHH', data)
    tid = tid_pdid & 0xF
    pd_id = (tid_pdid >> 4) & 0xF
    scale_factor = math.pi / 4096
    xphase *= scale_factor
    yphase *= scale_factor
    pulse_width *= scale_factor
    return timestamp, tid, pd_id, xphase, yphase, pulse_width


def _decode_raw_pulse_v3(data):
    timestamp, xphase, yphase, pulse_width, tid, pdid = struct.unpack('<qHHHBB', data)
    scale_factor = math.tau / 65535
    xphase *= scale_factor
    yphase *= scale_factor
    pulse_width *= scale_factor
    return timestamp, tid, pdid, xphase, yphase, pulse_width


def _decode_internal_analytics(data):
    if data[0] == internal.AnalyticsStreamType.ANNOTATIONS:
        return _decoder_internal_annotations(data)
    raise ValueError(f'No decoder defined for {internal.PacketType.ANALYTICS.name}:{data[0]}')


def _decoder_internal_annotations(data):
    annot_type, timestamp = struct.unpack_from('<Bf', data, 1)
    annotation_info_map = {
        internal.Annotations.CALIBRATION_START: None,
        internal.Annotations.CALIBRATION_END: None,
        internal.Annotations.CALIBRATION_ABORT: None,
        internal.Annotations.CALIBRATION_POINT: lambda data: dict(zip(('x', 'y', 'z'), struct.unpack('<fff', data))),
        internal.Annotations.RECENTER: lambda data: dict(zip(('x', 'y', 'z'), struct.unpack('<fff', data))),
        internal.Annotations.AUTOTUNE_START: None,
        internal.Annotations.AUTOTUNE_END: None,
        internal.Annotations.DATASTREAM: lambda data: {'val': struct.unpack('<I', data)},
        internal.Annotations.AUTOPHASE_END: lambda data: dict(zip((
            'x0', 'y0', 'x1', 'y1'), map(math.degrees, struct.unpack('<4f', data)))),
        internal.Annotations.FUSION_FUSED: lambda data: {'trackerId': struct.unpack('<B', data)},
        internal.Annotations.CALIBRATION_SAMPLE: lambda data: dict(zip((
            'gaze_ref_x', 'gaze_ref_y', 'gaze_ref_z',
            'glint_x0', 'glint_y0', 'glint_x1', 'glint_y1',
            'pupil_x0', 'pupil_y0', 'pupil_x1', 'pupil_y1'), struct.unpack('<11f', data))),
        internal.Annotations.VALIDATION_START: None,
        internal.Annotations.VALIDATION_END: None,
        internal.Annotations.VALIDATION_POINT: lambda data: dict(zip(('x', 'y', 'z'), struct.unpack('<fff', data))),
        internal.Annotations.VALIDATION_SAMPLE: lambda data: dict(zip((
            'gaze_ref_x', 'gaze_ref_y', 'gaze_ref_z',
            'glint_x0', 'glint_y0', 'glint_x1', 'glint_y1',
            'pupil_x0', 'pupil_y0', 'pupil_x1', 'pupil_y1'), struct.unpack('<11f', data))),
        internal.Annotations.AUTOPHASE_START: None,
        internal.Annotations.ALGORITHM_PIPELINE_UPDATE: lambda data: {'algorithmId': struct.unpack('<B', data)},
    }

    try:
        label = internal.Annotations(annot_type).name.replace('_', '.').capitalize()
        parser = annotation_info_map[annot_type]
    except KeyError:
        raise ValueError(f'No decoder defined for {hex(internal.PacketType.ANALYTICS)}:{data[0]}:{data[1]}')

    info = None
    if parser is not None:
        try:
            info = parser(data[6:])
        except Exception as exc:
            raise ValueError(f'Failed to decode {hex(internal.PacketType.ANALYTICS)}:{data[0]}:{data[1]}') from exc
    return timestamp, '', '', label, info  # timestamp, annot_id, parent_id, label, info


_INTERNAL_DECODERS = {
    internal.PacketType.RAW_PULSE_V2: _decode_raw_pulse_v2,
    internal.PacketType.RAW_PULSE_V3: _decode_raw_pulse_v3,
    internal.PacketType.ANALYTICS: _decode_internal_analytics,
}

frontend.decoders._DECODERS_BINOCULAR.update(_INTERNAL_DECODERS)  # pylint: disable=protected-access
frontend.decoders._DECODERS_MONOCULAR.update(_INTERNAL_DECODERS)  # pylint: disable=protected-access

decode = frontend.decoders.decode
