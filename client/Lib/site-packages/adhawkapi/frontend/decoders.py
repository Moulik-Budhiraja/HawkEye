'''Module that provides a simple way to decode a packet
Usage:
    retcode, size = adhawkapi.decode(PacketType.BLOB_SIZE, response[1:])
'''
import copy
import struct


try:
    from . import internal_decoders
except ImportError:
    internal_decoders = None

from ..publicapi import (
    AckCodes, Events, EyeMask, PacketType, PropertyType,
    SystemInfo, EyeTrackingStreamTypes, FeatureStreamTypes,
    EyeTrackingStreamData, FeatureStreamData)


def decode(packet_type, data, eye_mask):
    '''Decode the message given a specific packet type
    Returns:
        The decoded packet or None if the packet cannot be decoded
    '''
    try:
        if eye_mask == EyeMask.BINOCULAR:
            decoder = _DECODERS_BINOCULAR[packet_type]
        else:
            decoder = _DECODERS_MONOCULAR[packet_type]
    except KeyError:
        decoder = None
        if internal_decoders:
            decoder = internal_decoders.get_decoder(packet_type, data, eye_mask)

    try:
        if not decoder:
            return struct.unpack('<B', data)
        return decoder(data)
    except Exception as exc:  # pylint: disable=broad-except
        if data[0] != AckCodes.SUCCESS:
            # The only time the decoder format won't match is in the
            # case of an error response (ex: timeout)
            return (data[0],)
        raise ValueError(f'No decoder defined for {hex(packet_type)}') from exc


def _decode_blob_data(data):
    if len(data) > 1:
        return (data[0], data[1:])
    # Response for the setter should just be the request result
    return struct.unpack('<B', data)


def _decode_blob_size(data):
    if len(data) > 1:
        return struct.unpack('<BH', data)
    # Response for a setter should just be the request result
    return struct.unpack('<B', data)


def _decode_property_get(data):
    '''Expected response format for property get: (AckCode, PropertyType, data..)'''
    parser = None
    if data[1] == PropertyType.AUTOTUNE_POSITION:
        parser = '<BB4H'
    elif data[1] == PropertyType.STREAM_CONTROL:
        parser = '<BBf'
    elif data[1] == PropertyType.IPD:
        parser = '<BBf'
    elif data[1] == PropertyType.COMPONENT_OFFSETS:
        parser = '<BB6f'
    elif data[1] == PropertyType.EVENT_CONTROL:
        parser = '<BBB'
    elif data[1] == PropertyType.NORMALIZED_EYE_OFFSETS:
        parser = '<BB6f'
    elif data[1] == PropertyType.NOMINAL_EYE_OFFSETS:
        parser = '<BB6f'
    elif data[1] == PropertyType.EYETRACKING_RATE:
        parser = '<BBf'
    elif data[1] == PropertyType.EYETRACKING_STREAMS:
        parser = '<BBL'
    elif data[1] == PropertyType.FEATURE_STREAMS:
        parser = '<BBL'

    if not parser and internal_decoders:
        parser = internal_decoders.get_property_parser(data[1])

    if parser is not None:
        return struct.unpack(parser, data)

    raise ValueError(f'No decoder defined for {PacketType.PROPERTY_GET.name}:{PropertyType(data[1]).name}')


def _decode_request_backend_version(data):
    ackcode, backend_version = struct.unpack_from(f'<B{len(data)-2}s', data)
    return (ackcode, backend_version.decode('utf-8'))


def _decode_request_system_info_multi(data):
    ackcode, sys_info_type = struct.unpack_from('<BB', data)
    data_temp = copy.copy(data[2:])
    info = []
    if ackcode != AckCodes.SUCCESS:
        return (ackcode, sys_info_type, info)
    while len(data_temp) > 0:
        assert len(data_temp) != 1  # multi-request data should always come in sets of 2 (or 3 in the case of a string)
        if data_temp[0] in (SystemInfo.DEVICE_SERIAL, SystemInfo.FIRMWARE_VERSION):
            # if it is a string, grab the length of the string first:
            _info_type, str_length = struct.unpack_from('<BB', data_temp)
            info.append(data_temp[2:str_length + 2].decode('utf-8').split('\0', 1)[0])
            data_temp = data_temp[str_length + 2:]
        elif data_temp[0] == SystemInfo.FIRMWARE_API:
            _info_type, data_len = struct.unpack_from('<BB', data_temp)
            if data_len == 4:
                # Old versions of tros sent this as just a single version, not the string we expect
                version, = struct.unpack('<I', data_temp[2:6])
                info.append(f'0.{version}.0')
                data_temp = data_temp[6:]
            else:
                info.append(data_temp[2:data_len + 2].decode('utf-8').split('\0', 1)[0])
                data_temp = data_temp[data_len + 2:]
        else:
            # it will be an infotype followed by a 1 followed by a byte, requester knows order so just pack it in.
            _info_type, _len, byte_info = struct.unpack_from('<BBB', data_temp)
            assert _len == 1
            info.append(byte_info)
            data_temp = data_temp[3:]

    return (ackcode, sys_info_type, info)


def _default_decoder(data):
    return data.decode('utf-8')


def _decode_request_system_info(data):
    ackcode, sys_info_type = struct.unpack_from('<BB', data)
    if sys_info_type == SystemInfo.MULTI_INFO:
        return _decode_request_system_info_multi(data)
    try:
        decoder = _SYSTEM_INFO_DECODERS[sys_info_type]
    except KeyError:
        decoder = _default_decoder

    return (ackcode, sys_info_type, decoder(data[2:]))


def _decode_start_log_session(data):
    err, data = struct.unpack(f'<B{len(data)-1}s', data)
    return (err, data.decode('utf-8'))


def _decode_events(data):  # pylint: disable=too-many-return-statements
    event_type = data[0]
    if event_type == Events.BLINK:
        timestamp, duration = struct.unpack_from('<ff', data, 1)
        return event_type, timestamp, duration
    if event_type == Events.SACCADE:
        timestamp, duration, amplitude = struct.unpack_from('<fff', data, 1)
        return event_type, timestamp, duration, amplitude
    if event_type in (Events.EYE_CLOSED, Events.EYE_OPENED, Events.TRACKLOSS_START, Events.TRACKLOSS_END,
                      Events.SACCADE_START, Events.SACCADE_END):
        timestamp, eye_idx = struct.unpack_from('<fB', data, 1)
        return event_type, timestamp, eye_idx
    if event_type == Events.VALIDATION_SAMPLE:
        timestamp, ref_x, ref_y, ref_z, gaze_x, gaze_y, gaze_z, vergence, precision = struct.unpack_from('<9f', data, 1)
        return event_type, timestamp, ref_x, ref_y, ref_z, gaze_x, gaze_y, gaze_z, vergence, precision
    if event_type == Events.VALIDATION_SUMMARY:
        timestamp, mae = struct.unpack_from('<2f', data, 1)
        return event_type, timestamp, mae
    if event_type == Events.PROCEDURE_STARTED:
        timestamp = struct.unpack_from('<f', data, 1)[0]
        return event_type, timestamp
    if event_type == Events.PROCEDURE_ENDED:
        timestamp, results = struct.unpack_from('<fB', data, 1)
        return event_type, timestamp, results
    if event_type == Events.EXTERNAL_TRIGGER:
        timestamp, trigger_id = struct.unpack_from('<fB', data, 1)
        return event_type, timestamp, trigger_id
    raise ValueError(f'No decoder defined for event: {event_type}')


def _decode_et_stream(data):

    MONOCULAR_ET_DECODE = {  # pylint: disable=invalid-name
        EyeTrackingStreamTypes.GAZE: '<4f',
        EyeTrackingStreamTypes.PER_EYE_GAZE: '<3f',
        EyeTrackingStreamTypes.EYE_CENTER: '<3f',
        EyeTrackingStreamTypes.PUPIL_POSITION: '<3f',
        EyeTrackingStreamTypes.PUPIL_DIAMETER: '<f',
        EyeTrackingStreamTypes.GAZE_IN_IMAGE: '<4f',
        EyeTrackingStreamTypes.GAZE_IN_SCREEN: '<2f',
        EyeTrackingStreamTypes.IMU_QUATERNION: '<4f',
    }

    BINOCULAR_ET_DECODE = {  # pylint: disable=invalid-name
        EyeTrackingStreamTypes.GAZE: '<4f',
        EyeTrackingStreamTypes.PER_EYE_GAZE: '<6f',
        EyeTrackingStreamTypes.EYE_CENTER: '<6f',
        EyeTrackingStreamTypes.PUPIL_POSITION: '<6f',
        EyeTrackingStreamTypes.PUPIL_DIAMETER: '<2f',
        EyeTrackingStreamTypes.GAZE_IN_IMAGE: '<4f',
        EyeTrackingStreamTypes.GAZE_IN_SCREEN: '<2f',
        EyeTrackingStreamTypes.IMU_QUATERNION: '<4f',
    }

    timestamp, eye_mask = struct.unpack_from('<QB', data, 0)
    et_data = EyeTrackingStreamData(timestamp * 1e-9, EyeMask(eye_mask), None, None, None,
                                    None, None, None, None, None)
    offset = struct.calcsize('<QB')
    decode_map = BINOCULAR_ET_DECODE if eye_mask == 3 else MONOCULAR_ET_DECODE

    stream_type = 0
    while offset < len(data):
        stream_type, = struct.unpack_from('<B', data, offset)
        offset += 1
        if stream_type == EyeTrackingStreamTypes.GAZE:
            et_data.gaze = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.PER_EYE_GAZE:
            et_data.per_eye_gaze = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.EYE_CENTER:
            et_data.eye_center = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.PUPIL_POSITION:
            et_data.pupil_pos = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.PUPIL_DIAMETER:
            et_data.pupil_diameter = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.GAZE_IN_IMAGE:
            et_data.gaze_in_image = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.GAZE_IN_SCREEN:
            et_data.gaze_in_screen = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        elif stream_type == EyeTrackingStreamTypes.IMU_QUATERNION:
            et_data.imu_quaternion = struct.unpack_from(decode_map[stream_type], data, offset)
            offset += struct.calcsize(decode_map[stream_type])
        else:
            raise ValueError(f'Unknown or unsupported et stream type {stream_type}')
    return et_data


def _decode_feature_stream(data):
    timestamp, tracker_id = struct.unpack_from('<QB', data, 0)
    offset = struct.calcsize('<QB')
    feature_data = FeatureStreamData(timestamp * 1e-9, tracker_id, None, None, None)
    glints = []
    while offset < len(data):
        stream_type, = struct.unpack_from('<B', data, offset)
        offset += 1
        if stream_type == FeatureStreamTypes.GLINT:
            glint = struct.unpack_from('<B2f', data, offset)
            offset += struct.calcsize('<B2f')
            glints.append(glint)
        elif stream_type == FeatureStreamTypes.FUSED:
            feature_data.fused = struct.unpack_from('<2f', data, offset)
            offset += struct.calcsize('<2f')
        elif stream_type == FeatureStreamTypes.PUPIL_ELLIPSE:
            feature_data.ellipse = struct.unpack_from('<5f', data, offset)
            offset += struct.calcsize('<5f')
        else:
            raise ValueError(f'Unknown or unsupported feature stream type {stream_type}')
    if len(glints) > 0:
        feature_data.glints = glints
    return feature_data


_DECODERS = {
    # streams
    PacketType.EYETRACKING_STREAM: _decode_et_stream,
    PacketType.FEATURE_STREAM: _decode_feature_stream,
    PacketType.PULSE: (lambda data: struct.unpack('<B5fB', data)),
    PacketType.GLINT: (lambda data: struct.unpack('<B3fB', data)),
    PacketType.FUSE: (lambda data: struct.unpack('<B3fB', data)),
    PacketType.GAZE: (lambda data: struct.unpack('<5f', data)),
    PacketType.PUPIL_CENTER: (lambda data: struct.unpack('<B3f', data)),
    PacketType.PUPIL_ELLIPSE: (lambda data: struct.unpack('<B6f', data)),
    PacketType.IMU: (lambda data: struct.unpack('<7f', data)),
    PacketType.IMU_ROTATION: (lambda data: struct.unpack('<4f', data)),
    PacketType.IRIS_IMAGE_DATA_STREAM: (lambda data: struct.unpack('<BI100B', data)),
    PacketType.EVENTS: _decode_events,
    PacketType.GAZE_IN_IMAGE: (lambda data: struct.unpack('<5f', data)),
    PacketType.GAZE_IN_SCREEN: (lambda data: struct.unpack('<3f', data)),
    PacketType.MCU_TEMPERATURE: (lambda data: struct.unpack('<2f', data)),

    # responses
    PacketType.TRACKER_READY: (lambda data: tuple()),
    PacketType.TRACKER_STATE: (lambda data: data),
    PacketType.CALIBRATION_ERROR: (lambda data: struct.unpack('<ff', data)),
    PacketType.BLOB_SIZE: _decode_blob_size,
    PacketType.BLOB_DATA: _decode_blob_data,
    PacketType.SAVE_BLOB: (lambda data: struct.unpack('<BI', data)),
    PacketType.START_LOG_SESSION: _decode_start_log_session,
    PacketType.REQUEST_SYSTEM_INFO: _decode_request_system_info,
    PacketType.REQUEST_BACKEND_VERSION: _decode_request_backend_version,
    PacketType.PROPERTY_SET: (lambda data: struct.unpack('<BB', data)),
    PacketType.PROPERTY_GET: _decode_property_get,
    PacketType.SYSTEM_CONTROL: (lambda data: struct.unpack('<BB', data)),
    PacketType.PROCEDURE_START: (lambda data: struct.unpack('<BB', data)),
    PacketType.PROCEDURE_STATUS: (lambda data: struct.unpack('<3B', data)),
}


_DECODERS_BINOCULAR = {
    PacketType.PER_EYE_GAZE: (lambda data: struct.unpack('<7f', data)),
    PacketType.PUPIL_POSITION: (lambda data: struct.unpack('<7f', data)),
    PacketType.PUPIL_DIAMETER: (lambda data: struct.unpack('<3f', data)),
    **_DECODERS
}


_DECODERS_MONOCULAR = {
    PacketType.PER_EYE_GAZE: (lambda data: struct.unpack('<4f', data)),
    PacketType.PUPIL_POSITION: (lambda data: struct.unpack('<4f', data)),
    PacketType.PUPIL_DIAMETER: (lambda data: struct.unpack('<2f', data)),
    **_DECODERS
}


_SYSTEM_INFO_DECODERS = {
    SystemInfo.CAMERA_TYPE: (lambda data: data[0]),
    SystemInfo.PRODUCT_ID: (lambda data: data[0]),
    SystemInfo.EYE_MASK: (lambda data: EyeMask(data[0])),
}
