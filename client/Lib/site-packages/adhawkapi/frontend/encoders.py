'''Module that provides a simple way to encode a packet
Usage:
    message = adhawkapi.encode(PacketType.BLOB_SIZE, 10)
'''

import functools
import struct
from ipaddress import IPv4Address

import numpy as np


try:
    from . import internal_encoders
except ImportError:
    internal_encoders = None

from ..publicapi import (
    CameraUserSettings,
    MarkerSequenceMode,
    PacketType,
    ProcedureType,
    PropertyType,
    SystemControlType
)


def _default_encoder(value):
    return struct.pack('<B', value)


def encode(packet_type, *args):
    '''Encode the message given a specific packet type'''
    try:
        encoder = _ENCODERS[packet_type]
    except KeyError:
        encoder = None
        if internal_encoders:
            encoder = internal_encoders.get_encoder(packet_type)
        if not encoder:
            assert not args
            encoder = functools.partial(_default_encoder, packet_type.value)
    return encoder(*args)


def _encode_start_log_session(log_mode, pre_defined_tags=None, user_defined_tags=None):
    # Convert predefined tags to csv of key:value pairs
    pdf_list = []
    if pre_defined_tags is not None:
        pdf_list = [f'{key}:{value}' for key, value in pre_defined_tags.items()]

    # Append user defined tags
    if user_defined_tags is not None:
        pdf_list.extend(user_defined_tags)

    # Convert to csv
    tags_str = ','.join(pdf_list)
    return struct.pack(
        f'<BB{len(tags_str)}s',
        PacketType.START_LOG_SESSION.value,
        log_mode.value,
        bytes(tags_str, 'utf-8'))


def _encode_log_timestamped_annotation(annotid, parent, name, data=None, timestamp=None):
    msg = list(map(str, [annotid, parent, name, data if data is not None else '']))
    msg = bytes('\x00'.join(msg), 'utf-8')

    return struct.pack(
        '<Bf', PacketType.LOG_TIMESTAMPED_ANNOTATION.value,
        0 if timestamp is None else timestamp) + msg


def _encode_blob_data(blob_type, offset, *data):
    msg = struct.pack('<BBH', PacketType.BLOB_DATA.value, blob_type, offset)
    if data:
        msg += data[0]
    return msg


def _encode_blob_size(blob_type, *size):
    msg = struct.pack('<BB', PacketType.BLOB_SIZE.value, blob_type)
    if size:
        msg += struct.pack('<H', size[0])
    return msg


def _encode_property_get(property_type, *args):

    msg = struct.pack('<BB', PacketType.PROPERTY_GET.value, property_type.value)
    if property_type == PropertyType.STREAM_CONTROL:
        stream_bitmap, = args
        msg += struct.pack('<I', stream_bitmap)
    elif property_type == PropertyType.EVENT_CONTROL:
        event_bitmap, = args
        msg += struct.pack('<I', event_bitmap)
    elif internal_encoders:
        data = internal_encoders.encode_property_get(property_type, *args)
        if data:
            msg += data

    return msg


def _encode_property_set(property_type, *args):
    # pylint: disable=too-many-locals, too-many-return-statements
    msg = struct.pack('<BB', PacketType.PROPERTY_SET.value, property_type.value)
    if property_type == PropertyType.AUTOTUNE_POSITION:
        r_xmean, r_ymean, l_xmean, l_ymean = args
        return msg + struct.pack('<4H', r_xmean, r_ymean, l_xmean, l_ymean)
    if property_type == PropertyType.STREAM_CONTROL:
        stream_bitmap, stream_rate = args
        return msg + struct.pack('<If', stream_bitmap, stream_rate)
    if property_type == PropertyType.IPD:
        ipd, = args
        return msg + struct.pack('<f', ipd)
    if property_type == PropertyType.COMPONENT_OFFSETS:
        r_x, r_y, r_z, l_x, l_y, l_z = args
        return msg + struct.pack('<6f', r_x, r_y, r_z, l_x, l_y, l_z)
    if property_type == PropertyType.EVENT_CONTROL:
        event_bitmap, enabled = args
        return msg + struct.pack('<IB', event_bitmap, enabled)
    if property_type == PropertyType.EYETRACKING_RATE:
        rate, = args
        return msg + struct.pack('<f', rate)
    if property_type == PropertyType.EYETRACKING_STREAMS:
        mask, enable = args
        return msg + struct.pack('<LB', mask, enable)
    if property_type == PropertyType.FEATURE_STREAMS:
        mask, enable = args
        return msg + struct.pack('<LB', mask, enable)
    if internal_encoders:
        data = internal_encoders.encode_property_set(property_type, *args)
        if data:
            return msg + data

    raise ValueError(f'No encoder defined for {PacketType.PROPERTY_SET.name}:{property_type.name}')


def _encode_camera_user_settings_set(user_setting: CameraUserSettings, value):
    msg = struct.pack('<BB', PacketType.CAMERA_USER_SETTINGS_SET.value, user_setting.value)
    if user_setting == CameraUserSettings.GAZE_DEPTH:
        return msg + struct.pack('<f', value)
    if user_setting == CameraUserSettings.PARALLAX_CORRECTION:
        return msg + struct.pack('<B', value)
    if user_setting == CameraUserSettings.SAMPLING_DURATION:
        return msg + struct.pack('<I', value)
    raise ValueError(f'No encoder defined for {PacketType.CAMERA_USER_SETTINGS_SET.name}:{user_setting.name}')


def _encode_system_info(sys_info_type, *multi_args):
    return struct.pack(
        f'<BB{str(len(multi_args)) + "B" if len(multi_args) > 0 else ""}',
        PacketType.REQUEST_SYSTEM_INFO.value, sys_info_type.value, *multi_args)  # enum to int


def _encode_system_control(control_type, *args):
    msg = struct.pack('<BB', PacketType.SYSTEM_CONTROL.value, control_type.value)
    if control_type == SystemControlType.TRACKING:
        enable, = args
        msg = msg + struct.pack('<B', int(enable))
    return msg


def _encode_cal_gui_requests(mode, n_points, marker_size_mm, randomize, fov):
    if mode in [MarkerSequenceMode.FIXED_GAZE, MarkerSequenceMode.FIXED_GAZE_FOUR_MARKERS]:
        try:
            fov_h, fov_v, shift_h, shift_v = fov
        except (TypeError, ValueError):
            raise ValueError(f'Invalid value ({fov}) provided for fov')

        return struct.pack('<4BfB4f', PacketType.PROCEDURE_START.value, ProcedureType.CALIBRATION_GUI.value, mode,
                           n_points, marker_size_mm, randomize, fov_h, fov_v, shift_h, shift_v)
    return struct.pack('<4BfB', PacketType.PROCEDURE_START.value, ProcedureType.CALIBRATION_GUI.value, mode, n_points,
                       marker_size_mm, randomize)


def _encode_val_gui_requests(mode, n_rows, n_columns, marker_size_mm, randomize, fov):
    if mode in [MarkerSequenceMode.FIXED_GAZE, MarkerSequenceMode.FIXED_GAZE_FOUR_MARKERS]:
        try:
            fov_h, fov_v, shift_h, shift_v = fov
        except (TypeError, ValueError):
            raise ValueError(f'Invalid value ({fov}) provided for fov')

        return struct.pack('<5BfB4f', PacketType.PROCEDURE_START.value, ProcedureType.VALIDATION_GUI.value, mode,
                           n_rows, n_columns, marker_size_mm, randomize, fov_h, fov_v, shift_h, shift_v)
    return struct.pack('<5BfB', PacketType.PROCEDURE_START.value, ProcedureType.VALIDATION_GUI.value, mode, n_rows,
                       n_columns, marker_size_mm, randomize)


def _encode_screen_board_request(screen_width, screen_height, aruco_dic, marker_ids, markers):
    if np.shape(markers) != (len(marker_ids), 3):
        raise ValueError("Marker ids don't match the number of markers")
    packet = struct.pack('<B2fH', PacketType.REGISTER_SCREEN_BOARD.value, screen_width, screen_height, aruco_dic)
    for counter, marker_id in enumerate(marker_ids):
        packet += struct.pack('<H3f', marker_id, *markers[counter])
    return packet


def _encode_procedure_start_request(procedure_type, *args):
    if procedure_type in (ProcedureType.DEVICE_CALIBRATION, ProcedureType.UPDATE_FIRMWARE):
        packet = struct.pack('<BB', PacketType.PROCEDURE_START.value, procedure_type.value)
    elif procedure_type == ProcedureType.CALIBRATION_GUI:
        packet = _encode_cal_gui_requests(*args)
    elif procedure_type == ProcedureType.VALIDATION_GUI:
        packet = _encode_val_gui_requests(*args)
    elif procedure_type == ProcedureType.AUTOTUNE_GUI:
        mode, marker_size_mm = args
        packet = struct.pack('<BBBf', PacketType.PROCEDURE_START.value, procedure_type.value, mode, marker_size_mm)
    elif procedure_type == ProcedureType.QUICKSTART_GUI:
        mode, marker_size_mm, returning_user = args
        packet = struct.pack('<BBBfB', PacketType.PROCEDURE_START.value, procedure_type.value, mode, marker_size_mm,
                             returning_user)
    return packet


def _autotune_encoder(args):
    payload = struct.pack('<B', PacketType.TRIGGER_AUTOTUNE.value)
    if args is not None:
        payload += struct.pack('<fff', args[0], args[1], args[2])
    return payload


_ENCODERS = {
    # public packets
    PacketType.START_LOG_SESSION: _encode_start_log_session,
    PacketType.LOG_TIMESTAMPED_ANNOTATION: _encode_log_timestamped_annotation,
    PacketType.BLOB_SIZE: _encode_blob_size,
    PacketType.BLOB_DATA: _encode_blob_data,
    PacketType.PROPERTY_GET: _encode_property_get,
    PacketType.PROPERTY_SET: _encode_property_set,
    PacketType.START_CAMERA:
        (lambda res_index, correct_distortion: struct.pack('<BHB', PacketType.START_CAMERA.value,
                                                           res_index, correct_distortion)),
    PacketType.START_VIDEO_STREAM:
        (lambda ip, port: struct.pack('<BIH', PacketType.START_VIDEO_STREAM.value, int(IPv4Address(ip)), port)),
    PacketType.STOP_VIDEO_STREAM:
        (lambda ip, port: struct.pack('<BIH', PacketType.STOP_VIDEO_STREAM.value, int(IPv4Address(ip)), port)),
    PacketType.REGISTER_SCREEN_BOARD: _encode_screen_board_request,
    PacketType.CAMERA_USER_SETTINGS_SET: _encode_camera_user_settings_set,
    PacketType.REGISTER_CALIBRATION:
        (lambda x, y, z: struct.pack('<Bfff', PacketType.REGISTER_CALIBRATION.value, x, y, z)),
    PacketType.REGISTER_VALIDATION:
        (lambda x, y, z: struct.pack('<Bfff', PacketType.REGISTER_VALIDATION.value, x, y, z)),
    PacketType.RECENTER_CALIBRATION:
        (lambda x, y, z: struct.pack('<Bfff', PacketType.RECENTER_CALIBRATION, x, y, z)),
    PacketType.LOAD_BLOB:
        (lambda blob_type, blob_id: struct.pack('<BBI', PacketType.LOAD_BLOB.value, blob_type.value, blob_id)),
    PacketType.SAVE_BLOB:
        (lambda blob_type: struct.pack('<BB', PacketType.SAVE_BLOB.value, blob_type.value)),
    PacketType.DELETE_BLOB:
        (lambda blob_id: struct.pack('<BI', PacketType.DELETE_BLOB.value,  blob_id)),
    PacketType.REQUEST_SYSTEM_INFO: _encode_system_info,
    PacketType.SYSTEM_CONTROL: _encode_system_control,
    PacketType.PROCEDURE_START: _encode_procedure_start_request,
    PacketType.PROCEDURE_STATUS: (lambda procedure_type:
                                  struct.pack('<BB', PacketType.PROCEDURE_STATUS.value, procedure_type.value)),
    PacketType.TRIGGER_AUTOTUNE: _autotune_encoder,
}
