'''This module handles translating data into blobs and back'''
import logging
import struct
from collections import namedtuple
from typing import Any

import numpy as np

from . import defaults
from .publicapi import BlobType


# Blob object
Blob = namedtuple('Blob', ['version', 'data'])

# Context required to setup the blob format
CalibrationContext = namedtuple('CalibrationContext', ['eye_mask'])
MultiglintContext = namedtuple('MultiglintContext', ['num_eyes'])

SIZEOF_FLOAT = 4
SIZEOF_USHORT = 2
XYZ_SIZE = 3
NUM_SCAN_DIMS = 2
MODEL_ET_NUM_POLY_TERMS = 55
PRIOR_INPUT_DIM = 6
PRIOR_OUTPUT_DIM = 2
TUNE_REF_SIZE = 4
MODULECAL_RANGE_SIZE = 4
MODULECAL_NUM_COUPLING_TERMS = 3  # per dimension
N_PDS = defaults.N_PHOTODIODES + defaults.MAX_PUPIL_DETECTORS


def parse_blob(blob_type: BlobType, context: namedtuple, blob_data: bytes) -> Any:
    '''Parse blobs returned from the embedded device'''
    parser_map = {
        (BlobType.MULTIGLINT, 1): _parse_multiglint_v1_blob,
        (BlobType.MULTIGLINT, 2): _parse_multiglint_v2_blob,
        (BlobType.CALIBRATION, 6): _parse_calibration_v6_blob,
        (BlobType.CALIBRATION, 7): _parse_calibration_v7_blob,
        (BlobType.CALIBRATION, 8): _parse_calibration_v8_blob,
        (BlobType.CALIBRATION, 9): _parse_calibration_v9_blob,
        (BlobType.AUTOTUNE, 1): _parse_autotune_v1_blob,
        (BlobType.AUTOTUNE, 2): _parse_autotune_v2_blob,
        (BlobType.DYNAMIC_FUSION, 1): _parse_dynamic_fusion_v1_blob,
        (BlobType.DYNAMIC_FUSION, 2): _parse_dynamic_fusion_v2_blob,
        # No longer supporting modulecal v1 blobs
        (BlobType.MODULE_CAL, 2): _parse_module_cal_v4_blob,
        (BlobType.MODULE_CAL, 3): _parse_module_cal_v4_blob,
        (BlobType.MODULE_CAL, 4): _parse_module_cal_v4_blob,
        (BlobType.MODULE_CAL, 5): _parse_module_cal_v5_blob,
        (BlobType.MODULE_CAL, 6): _parse_module_cal_v6_blob,
        (BlobType.MODEL_ET, 1): _parse_model_et_v1_blob,
        (BlobType.MODEL_ET, 2): _parse_model_et_v2_blob,
        (BlobType.MODEL_PRIORS, 1): _parse_model_priors_v1_blob,
        (BlobType.MODEL_PRIORS, 2): _parse_model_priors_v2_blob,
        (BlobType.GEOMETRY, 1): _parse_geometry_v1_blob,
        (BlobType.GEOMETRY, 2): _parse_geometry_v2_blob,
        (BlobType.GEOMETRY, 3): _parse_geometry_v3_blob,
        (BlobType.AUTOTUNE_MULTIGLINT, 1): _parse_multiglint_v2_blob,
    }
    try:
        blob_version = blob_data[0]
    except IndexError:
        raise ValueError(f'No {blob_type.name} to read')
    try:
        logging.info(f'Parsing {blob_type.name} v{blob_version} blob')
        parser = parser_map[(blob_type, blob_version)]
    except KeyError:
        raise ValueError(f'No parser defined for {blob_type.name} v{blob_version}')
    try:
        return Blob(blob_version, parser(bytes(blob_data[1:]), context))
    except Exception as excp:  # pylint: disable-broad-except
        raise ValueError(f"Blob data doesn't match {blob_type.name} v{blob_version} format: {excp}") from excp


def create_blob(blob_type: BlobType, blob_version: int, context: namedtuple, data) -> bytes:
    '''Create a blob for storage on the embedded device'''
    creator_map = {
        (BlobType.MULTIGLINT, 1): _create_multiglint_v1_blob,
        (BlobType.MULTIGLINT, 2): _create_multiglint_v2_blob,
        (BlobType.CALIBRATION, 6): _create_calibration_v6_blob,
        (BlobType.CALIBRATION, 7): _create_calibration_v7_blob,
        (BlobType.CALIBRATION, 8): _create_calibration_v8_blob,
        (BlobType.CALIBRATION, 9): _create_calibration_v9_blob,
        (BlobType.AUTOTUNE, 2): _create_autotune_v2_blob,
        (BlobType.DYNAMIC_FUSION, 2): _create_dynamic_fusion_v2_blob,
        # No longer supporting creation of modulecal v1 or v2 blobs
        (BlobType.MODULE_CAL, 3): _create_module_cal_v4_blob,
        (BlobType.MODULE_CAL, 4): _create_module_cal_v4_blob,
        (BlobType.MODULE_CAL, 5): _create_module_cal_v5_blob,
        (BlobType.MODULE_CAL, 6): _create_module_cal_v6_blob,
        (BlobType.MODEL_ET, 2): _create_model_et_v2_blob,
        (BlobType.MODEL_PRIORS, 2): _create_model_priors_v2_blob,
        (BlobType.GEOMETRY, 3): _create_geometry_v3_blob,
        (BlobType.AUTOTUNE_MULTIGLINT, 1): _create_multiglint_v2_blob,
    }
    try:
        logging.info(f'Creating {blob_type.name} v{blob_version} blob')
        creator = creator_map[(blob_type, blob_version)]
    except KeyError:
        raise ValueError(f'No blob creator defined for {blob_type.name} v{blob_version}')
    try:
        return struct.pack('<B', blob_version) + bytes(creator(data, context))
    except Exception as excp:  # pylint: disable-broad-except
        raise ValueError(f'Invalid data provided for {blob_type.name} v{blob_version}: {excp}') from excp


def _create_multiglint_v2_blob(data: any, context: MultiglintContext) -> bytes:

    blob_data = []
    for eye in range(context.num_eyes):
        for pdid in range(defaults.N_PHOTODIODES):
            blob_data += struct.pack('<ff', *data[eye][pdid])
    return blob_data


def _parse_multiglint_v2_blob(blob_data: bytes, context: MultiglintContext) -> any:

    offset = 0
    multiglint = np.zeros((context.num_eyes, defaults.N_PHOTODIODES, 2))
    for eye in range(context.num_eyes):
        for pdid in range(defaults.N_PHOTODIODES):
            multiglint[eye][pdid] = struct.unpack_from('<ff', blob_data, offset)
            offset = offset + 8
    return multiglint


def _parse_multiglint_v1_blob(blob_data: bytes, context: MultiglintContext) -> any:
    multiglint = _parse_multiglint_v2_blob(blob_data, context)
    return multiglint * 2.0


def _create_multiglint_v1_blob(data: any, context: MultiglintContext) -> bytes:
    return _create_multiglint_v2_blob(data * 0.5, context)


def _create_calibration_v6_blob(data: any, context: CalibrationContext) -> bytes:
    '''Create the calibration v6 blob
    Args:
        data (dict): Calibration blob data of the following form {
                gaze_ref: [NUM_POINTS][XYZ],
                fused: [NUM_POINTS][MAX_SCANNERS][XY]
                pupil: [NUM_POINTS][MAX_SCANNERS][XY]
                glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]}
    Returns:
        bytes: [[gaze_ref, glint_mask, fused, pupil_mask, pupil, glint], ...]
    '''

    num_points = len(data['gaze_ref'])
    blob_data = [num_points]
    for gaze, fused, pupil, glint in zip(data['gaze_ref'], data['fused'], data['pupil'], data['glint']):
        gaze = np.array(gaze)
        fused = np.array(fused)
        pupil = np.array(pupil)
        glint = np.array(glint)
        blob_data += struct.pack('<3f', *gaze)
        glint_mask = 0
        pupil_mask = 0
        for eye in range(defaults.MAX_EYES):
            if context.eye_mask & (1 << eye) and np.all(np.isfinite(fused[eye])):
                glint_mask |= 1 << eye
            if context.eye_mask & (1 << eye) and np.all(np.isfinite(pupil[eye])):
                pupil_mask |= 1 << eye

        blob_data += struct.pack(f'<B{defaults.MAX_SCANNERS * NUM_SCAN_DIMS}f', glint_mask, *fused.flatten())
        blob_data += struct.pack(f'<B{defaults.MAX_SCANNERS * NUM_SCAN_DIMS}f', pupil_mask, *pupil.flatten())
        blob_data += struct.pack(
            f'<{defaults.MAX_SCANNERS * defaults.N_PHOTODIODES * NUM_SCAN_DIMS}f',
            *glint.flatten())
    return blob_data


def _create_calibration_v7_blob(data: any, context: CalibrationContext) -> bytes:
    '''Create the calibration v7 blob
    Args:
        data (dict): Calibration blob data of the following form {
                gaze_ref: [NUM_POINTS][XYZ],
                fused: [NUM_POINTS][MAX_SCANNERS][XY]
                pupil: [NUM_POINTS][MAX_SCANNERS][XY]
                glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]}
                dscales: [NUM_POINTS][MAX_SCANNERS][XY]
    Returns:
        bytes: [[gaze_ref, glint_mask, fused, pupil_mask, pupil, glint, dscales], ...]
    '''

    num_points = len(data['gaze_ref'])
    blob_data = [num_points]
    for gaze, fused, pupil, glint, dscales in zip(data['gaze_ref'], data['fused'], data['pupil'], data['glint'],
                                                  data['dscales']):
        gaze = np.array(gaze)
        fused = np.array(fused)
        pupil = np.array(pupil)
        glint = np.array(glint)
        dscales = np.array(dscales)
        blob_data += struct.pack('<3f', *gaze)
        glint_mask = 0
        pupil_mask = 0
        for eye in range(defaults.MAX_EYES):
            if context.eye_mask & (1 << eye) and np.all(np.isfinite(fused[eye])):
                glint_mask |= 1 << eye
            if context.eye_mask & (1 << eye) and np.all(np.isfinite(pupil[eye])):
                pupil_mask |= 1 << eye

        blob_data += struct.pack(f'<B{defaults.MAX_SCANNERS * NUM_SCAN_DIMS}f', glint_mask, *fused.flatten())
        blob_data += struct.pack(f'<B{defaults.MAX_SCANNERS * NUM_SCAN_DIMS}f', pupil_mask, *pupil.flatten())
        blob_data += struct.pack(
            f'<{defaults.MAX_SCANNERS * defaults.N_PHOTODIODES * NUM_SCAN_DIMS}f',
            *glint.flatten())
        blob_data += struct.pack(f'<{defaults.MAX_SCANNERS * NUM_SCAN_DIMS}f', *dscales.flatten())
    return blob_data


def _create_calibration_v8_blob(data: any, context: CalibrationContext) -> bytes:
    '''Create the calibration v8 blob
    Args:
        data (dict): Calibration blob data of the following form {
                gaze_ref: [NUM_POINTS][XYZ],
                fused: [NUM_POINTS][MAX_SCANNERS][XY]
                pupil: [NUM_POINTS][MAX_SCANNERS][XY]
                glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]
                dscales: [NUM_POINTS][MAX_SCANNERS][XY]
                component_offsets: [MAX_SCANNERS][XYZ]}
    Returns:
        bytes: [component_offsets, num_points, [gaze_ref, glint_mask, fused, pupil_mask, pupil, glint, dscales], ...]
    '''
    blob_data_v7 = _create_calibration_v7_blob(data, context)
    component_offsets = np.array(data['component_offsets'])
    blob_data = []
    blob_data += struct.pack(f'<{defaults.MAX_SCANNERS * XYZ_SIZE}f', *component_offsets.flatten())
    blob_data += blob_data_v7
    return blob_data


def _create_calibration_v9_blob(data: any, context: CalibrationContext) -> bytes:
    '''Create the calibration v9 blob
    Args:
        data (dict): Calibration blob data of the following form {
                gaze_ref: [NUM_POINTS][XYZ],
                fused: [NUM_POINTS][MAX_SCANNERS][XY]
                pupil: [NUM_POINTS][MAX_SCANNERS][XY]
                glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]
                dscales: [NUM_POINTS][MAX_SCANNERS][XY]
                component_offsets: [MAX_SCANNERS][XYZ]}
                eye_position: [MAX_SCANNERS][XYZ]}
    Returns:
        bytes: [eye_position, component_offsets, num_points,
                [gaze_ref, glint_mask, fused, pupil_mask, pupil, glint, dscales], ...]
    '''
    blob_data_v8 = _create_calibration_v8_blob(data, context)
    eye_position = np.array(data['eye_position'])
    blob_data = []
    blob_data += struct.pack(f'<{defaults.MAX_SCANNERS * XYZ_SIZE}f', *eye_position.flatten())
    blob_data += blob_data_v8
    return blob_data


def _parse_calibration_v6_blob(blob_data: bytes, _context: CalibrationContext) -> any:
    '''Parse the calibration v6 blob
    Args:
        bytes: [[gaze_ref, glint_mask, fused, pupil_mask, pupil, glint], ...]
        context: Any context used to help parse the data
    Returns:
        dict: Calibration blob data of the following form
        {
            gaze_ref: [NUM_POINTS][XYZ],
            fused: [NUM_POINTS][MAX_SCANNERS][XY]
            pupil: [NUM_POINTS][MAX_SCANNERS][XY]
            glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]
        }
    '''
    offset = 1
    gaze_ref = []
    fused = []
    pupil = []
    glint = []

    fused_dim = (defaults.MAX_SCANNERS, NUM_SCAN_DIMS)
    pupil_dim = (defaults.MAX_SCANNERS, NUM_SCAN_DIMS)
    glint_dim = (defaults.MAX_SCANNERS, defaults.N_PHOTODIODES * NUM_SCAN_DIMS)

    fused_len = np.prod(fused_dim)
    pupil_len = np.prod(pupil_dim)
    glint_len = np.prod(glint_dim)

    while offset < len(blob_data):
        gaze_point = struct.unpack_from('<3f', blob_data, offset)
        gaze_ref.append(np.asarray(gaze_point))
        offset += 12

        _glint_mask, = struct.unpack_from('<B', blob_data, offset)
        offset += 1

        fused_point = struct.unpack_from(f'<{fused_len}f', blob_data, offset)
        fused.append(np.asarray(fused_point).reshape(fused_dim))
        offset += fused_len * 4

        _pupil_mask, = struct.unpack_from('<B', blob_data, offset)
        offset += 1

        pupil_point = struct.unpack_from(f'<{pupil_len}f', blob_data, offset)
        pupil.append(np.asarray(pupil_point).reshape(pupil_dim))
        offset += pupil_len * 4

        glint_point = struct.unpack_from(f'<{glint_len}f', blob_data, offset)
        glint.append(np.asarray(glint_point).reshape(glint_dim))
        offset += glint_len * 4

    data = {
        'gaze_ref': gaze_ref,
        'fused': fused,
        'pupil': pupil,
        'glint': glint,
        'dscales': np.array(fused) ** 0,
        'component_offsets': np.zeros((defaults.MAX_SCANNERS, XYZ_SIZE)),
    }
    return data


def _parse_calibration_v7_blob(blob_data: bytes, _context: CalibrationContext) -> any:
    '''Parse the calibration v7 blob
    Args:
        bytes: [[gaze_ref, glint_mask, fused, pupil_mask, pupil, glint, dscales], ...]
        context: Any context used to help parse the data
    Returns:
        dict: Calibration blob data of the following form
        {
            gaze_ref: [NUM_POINTS][XYZ],
            fused: [NUM_POINTS][MAX_SCANNERS][XY]
            pupil: [NUM_POINTS][MAX_SCANNERS][XY]
            glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]
            dscales: [NUM_POINTS][MAX_SCANNERS][XY]
        }
    '''
    offset = 1
    gaze_ref = []
    fused = []
    pupil = []
    glint = []
    dscales = []

    feature_dim = (defaults.MAX_SCANNERS, NUM_SCAN_DIMS)
    glints_dim = (defaults.MAX_SCANNERS, defaults.N_PHOTODIODES * NUM_SCAN_DIMS)

    feature_len = np.prod(feature_dim)
    glints_len = np.prod(glints_dim)

    while offset < len(blob_data):
        gaze_point = struct.unpack_from('<3f', blob_data, offset)
        gaze_ref.append(np.asarray(gaze_point))
        offset += 12

        # _glint_mask, = struct.unpack_from('<B', blob_data, offset)
        offset += 1

        fused_point = struct.unpack_from(f'<{feature_len}f', blob_data, offset)
        fused.append(np.asarray(fused_point).reshape(feature_dim))
        offset += feature_len * 4

        # _pupil_mask, = struct.unpack_from('<B', blob_data, offset)
        offset += 1

        pupil_point = struct.unpack_from(f'<{feature_len}f', blob_data, offset)
        pupil.append(np.asarray(pupil_point).reshape(feature_dim))
        offset += feature_len * 4

        glint_point = struct.unpack_from(f'<{glints_len}f', blob_data, offset)
        glint.append(np.asarray(glint_point).reshape(glints_dim))
        offset += glints_len * 4

        dscales_point = struct.unpack_from(f'<{feature_len}f', blob_data, offset)
        dscales.append(np.asarray(dscales_point).reshape(feature_dim))
        offset += feature_len * 4

    data = {
        'gaze_ref': gaze_ref,
        'fused': fused,
        'pupil': pupil,
        'glint': glint,
        'dscales': dscales,
        'component_offsets': np.zeros((defaults.MAX_SCANNERS, XYZ_SIZE)),
    }
    return data


def _parse_calibration_v8_blob(blob_data: bytes, context: CalibrationContext) -> any:
    '''Parse the calibration v8 blob
    Args:
        bytes: [component_offsets, num_points, [gaze_ref, glint_mask, fused, pupil_mask, pupil, glint, dscales], ...]
        context: Any context used to help parse the data
    Returns:
        dict: Calibration blob data of the following form
        {
            gaze_ref: [NUM_POINTS][XYZ],
            fused: [NUM_POINTS][MAX_SCANNERS][XY]
            pupil: [NUM_POINTS][MAX_SCANNERS][XY]
            glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]
            dscales: [NUM_POINTS][MAX_SCANNERS][XY]
            component_offsets: [MAX_SCANNERS][XYZ]
        }
    '''
    # parse the component offsets data
    component_offsets_dim = (defaults.MAX_SCANNERS, XYZ_SIZE)
    component_offsets_len = np.prod(component_offsets_dim)
    component_offsets = struct.unpack_from(f'<{component_offsets_len}f', blob_data)
    # parse the rest of the data, which is just the v7 blob
    v7_data_offset = component_offsets_len * 4
    data = _parse_calibration_v7_blob(blob_data[v7_data_offset:], context)
    data['component_offsets'] = np.asarray(component_offsets).reshape(component_offsets_dim)
    return data


def _parse_calibration_v9_blob(blob_data: bytes, context: CalibrationContext) -> any:
    '''Parse the calibration v9 blob
    Args:
        bytes: [eye_position, component_offsets, num_points,
                [gaze_ref, glint_mask, fused, pupil_mask, pupil, glint, dscales], ...]
        context: Any context used to help parse the data
    Returns:
        dict: Calibration blob data of the following form
        {
            gaze_ref: [NUM_POINTS][XYZ],
            fused: [NUM_POINTS][MAX_SCANNERS][XY]
            pupil: [NUM_POINTS][MAX_SCANNERS][XY]
            glint: [NUM_POINTS][MAX_SCANNERS][NUM_PDS * XY]
            dscales: [NUM_POINTS][MAX_SCANNERS][XY]
            component_offsets: [MAX_SCANNERS][XYZ]
            eye_position: [MAX_SCANNERS][XYZ]
        }
    '''
    # parse the eye position data
    eye_position_dim = (defaults.MAX_SCANNERS, XYZ_SIZE)
    eye_position_len = np.prod(eye_position_dim)
    eye_position = struct.unpack_from(f'<{eye_position_len}f', blob_data)
    # parse the rest of the data, which is just the v8 blob
    v8_data_offset = eye_position_len * 4
    data = _parse_calibration_v8_blob(blob_data[v8_data_offset:], context)
    data['eye_position'] = np.asarray(eye_position).reshape(eye_position_dim)
    return data


def _create_autotune_v2_blob(data: any, _context: None) -> bytes:

    blob_data = []
    blob_data += struct.pack('<I', data['revision'])
    for eye in range(defaults.MAX_EYES):
        for axis in range(NUM_SCAN_DIMS):
            blob_data += struct.pack(f'<{defaults.N_PHOTODIODES}f', *data['offsets'][eye][axis])
    return blob_data


def _parse_autotune_v1_blob(blob_data: bytes, _context: None) -> any:

    blob_data_offset = 0
    config_data = []
    for eye in range(defaults.MAX_EYES):
        config_data.append([])
        for _ in range(NUM_SCAN_DIMS):
            data = struct.unpack_from(f'<{defaults.N_PHOTODIODES}f',
                                      blob_data,
                                      blob_data_offset)
            config_data[eye].append(data)
            blob_data_offset += defaults.N_PHOTODIODES * SIZEOF_FLOAT
    return {'offsets': config_data, 'revision': 0}


def _parse_autotune_v2_blob(blob_data: bytes, _context: None) -> any:
    # same as v1 but with an int32 revision header
    autotune_offsets_data = _parse_autotune_v1_blob(blob_data[4:], _context)
    autotune_offsets_data['revision'] = int.from_bytes(blob_data[:4], 'little')
    return autotune_offsets_data


def _create_dynamic_fusion_v2_blob(data: any, _context: None) -> bytes:

    def _load_sclera_transforms(data: any) -> bytes:
        blob_data = []
        for dim in range(NUM_SCAN_DIMS):
            blob_data += struct.pack(f'<{NUM_SCAN_DIMS}f', *data[dim])
        return blob_data

    def _load_sclera_shift(data: any) -> bytes:
        return struct.pack(f'<{NUM_SCAN_DIMS}f', *data)

    def _load_scale_factors(data: any) -> bytes:
        blob_data = []
        for pd_index in range(defaults.N_PHOTODIODES):
            blob_data += struct.pack(f'<{NUM_SCAN_DIMS}f', *data[pd_index])
        return blob_data

    blob_data = []
    blob_data += struct.pack('<I', data['revision'])
    blob_data += _load_sclera_transforms(data['sclera_transform'])
    blob_data += _load_sclera_shift(data['sclera_shift'])
    blob_data += _load_scale_factors(data['scale_factors'])
    blob_data += _load_scale_factors(data['pupil_offsets'])
    return blob_data


def _parse_dynamic_fusion_v1_blob(blob_data: bytes, _context: None) -> any:

    def _parse_sclera_transforms(blob_data: bytes, offset: int):
        transform_data = []
        for dim in range(NUM_SCAN_DIMS):
            transform_data.append([])
            transform_data[dim] = struct.unpack_from(f'<{NUM_SCAN_DIMS}f',
                                                     blob_data,
                                                     offset + dim * NUM_SCAN_DIMS * SIZEOF_FLOAT)
        return transform_data

    def _parse_sclera_shift(blob_data: bytes, offset: int):
        return struct.unpack_from(f'<{NUM_SCAN_DIMS}f', blob_data, offset)

    def _parse_scale_factors(blob_data: bytes, offset: int):
        scale_factors = []
        for pd_index in range(defaults.N_PHOTODIODES):
            scale_factors.append([])
            scale_factors[pd_index] = struct.unpack_from(f'<{NUM_SCAN_DIMS}f',
                                                         blob_data,
                                                         offset + pd_index * NUM_SCAN_DIMS * SIZEOF_FLOAT)
        return scale_factors

    fusion_configs_data = {'sclera_transform': [], 'sclera_shift': [], 'scale_factors': [], 'pupil_offsets': []}
    data_offset = 0
    fusion_configs_data['sclera_transform'] = _parse_sclera_transforms(blob_data, data_offset)
    data_offset += (NUM_SCAN_DIMS ** 2) * SIZEOF_FLOAT
    fusion_configs_data['sclera_shift'] = _parse_sclera_shift(blob_data, data_offset)
    data_offset += NUM_SCAN_DIMS * SIZEOF_FLOAT
    fusion_configs_data['scale_factors'] = _parse_scale_factors(blob_data, data_offset)
    data_offset += defaults.N_PHOTODIODES * NUM_SCAN_DIMS * SIZEOF_FLOAT
    fusion_configs_data['pupil_offsets'] = _parse_scale_factors(blob_data, data_offset)
    fusion_configs_data['revision'] = 0
    return fusion_configs_data


def _parse_dynamic_fusion_v2_blob(blob_data: bytes, _context: None) -> any:
    # same as v1 but with an int32 revision header
    fusion_configs_data = _parse_dynamic_fusion_v1_blob(blob_data[4:], _context)
    fusion_configs_data['revision'] = int.from_bytes(blob_data[:4], 'little')
    return fusion_configs_data


def _create_module_cal_v4_blob(data: any, _context: None) -> bytes:

    def _load_transform(data: any) -> bytes:
        blob_data = []
        for eye_data in data:
            for dim in range(NUM_SCAN_DIMS):
                blob_data += struct.pack(f'<{XYZ_SIZE}f', *eye_data[dim])
        return blob_data

    def _load_tune_params(data: any) -> bytes:
        blob_data = []
        for eye_data in data:
            blob_data += struct.pack(f'<{TUNE_REF_SIZE}H', *eye_data)
        return blob_data

    def _load_offset_transform(data: any) -> bytes:
        blob_data = []
        for eye_data in data:
            for coeff in range(NUM_SCAN_DIMS * XYZ_SIZE):
                blob_data += struct.pack(f'<{len(eye_data[coeff])}f', *eye_data[coeff])
        return blob_data

    blob_data = []
    blob_data += _load_transform([data[eye]['scan_to_angles'] for eye in range(defaults.MAX_EYES)])
    blob_data += _load_tune_params([data[eye]['reference_position'] for eye in range(defaults.MAX_EYES)])
    blob_data += _load_offset_transform([data[eye]['offset_transform'] for eye in range(defaults.MAX_EYES)])
    return blob_data


def _parse_module_cal_v4_blob(blob_data: bytes, _context: None) -> any:

    def _parse_transform(blob_data: bytes, offset: int):
        data_offset = 0
        transform = []
        for eye in range(defaults.MAX_EYES):
            transform.append([])
            for _ in range(NUM_SCAN_DIMS):
                transform[eye].append(struct.unpack_from(f'<{XYZ_SIZE}f',
                                                         blob_data,
                                                         data_offset + offset))
                data_offset += XYZ_SIZE * SIZEOF_FLOAT
        return transform

    def _parse_tune_params(blob_data: bytes, offset: int):
        data_offset = 0
        autotune_position = []
        for _ in range(defaults.MAX_EYES):
            autotune_position.append(struct.unpack_from(f'<{TUNE_REF_SIZE}H',
                                                        blob_data,
                                                        data_offset + offset))
            data_offset += TUNE_REF_SIZE * SIZEOF_USHORT
        return autotune_position

    def _parse_offset_transform(blob_data: bytes, offset: int):
        data_offset = 0
        offset_transform = []
        # calculate how many terms there are in the tune-invariance polynomial
        num_terms = (len(blob_data) - offset) // SIZEOF_FLOAT // (NUM_SCAN_DIMS * XYZ_SIZE) // defaults.MAX_EYES
        for eye in range(defaults.MAX_EYES):
            offset_transform.append([])
            for _ in range(NUM_SCAN_DIMS * XYZ_SIZE):
                offset_transform[eye].append(struct.unpack_from(f'<{num_terms}f',
                                                                blob_data,
                                                                data_offset + offset))

                data_offset += num_terms * SIZEOF_FLOAT
        return offset_transform

    blob_data_offset = 0
    scan_to_angles = _parse_transform(blob_data, blob_data_offset)
    blob_data_offset += defaults.MAX_EYES * NUM_SCAN_DIMS * XYZ_SIZE * SIZEOF_FLOAT
    reference_position = _parse_tune_params(blob_data, blob_data_offset)
    blob_data_offset += defaults.MAX_EYES * TUNE_REF_SIZE * SIZEOF_USHORT
    offset_transform = _parse_offset_transform(blob_data, blob_data_offset)
    return [{'scan_to_angles': scan_to_angles[eye],
             'reference_position': reference_position[eye],
             'offset_transform': offset_transform[eye]} for eye in range(defaults.MAX_EYES)]


def _create_module_cal_v5_blob(data: any, context: None) -> any:

    def _load_range(data: any) -> bytes:
        blob_data = []
        for eye_data in data:
            blob_data += struct.pack(f'<{MODULECAL_RANGE_SIZE}f', *eye_data)
        return blob_data

    blob_data = []
    blob_data += _create_module_cal_v4_blob(data, context)
    blob_data += _load_range([data[eye]['range'] for eye in range(defaults.MAX_EYES)])
    return blob_data


def _create_module_cal_v6_blob(data: any, context: None) -> any:

    def _load_coupling_transform(data: any) -> bytes:
        blob_data = []
        for eye_data in data:
            for dim in range(NUM_SCAN_DIMS):
                blob_data += struct.pack(f'<{MODULECAL_NUM_COUPLING_TERMS}f', *eye_data[dim])
        return blob_data

    blob_data = []
    blob_data += _create_module_cal_v5_blob(data, context)
    blob_data += _load_coupling_transform([data[eye]['coupling_transform'] for eye in range(defaults.MAX_EYES)])
    return blob_data


def _parse_module_cal_v5_blob(blob_data: bytes, context: None) -> any:
    def _parse_range(blob_data: bytes):
        modcal_range = []
        for eye in range(defaults.MAX_EYES):
            modcal_range.append(struct.unpack_from(f'<{MODULECAL_RANGE_SIZE}f',
                                                   blob_data, eye * MODULECAL_RANGE_SIZE * SIZEOF_FLOAT))
        return modcal_range

    # Parse as v4 blob minus module cal range param
    v5_blob = _parse_module_cal_v4_blob(blob_data[:-(defaults.MAX_EYES * MODULECAL_RANGE_SIZE * SIZEOF_FLOAT)], context)
    # Parse module_cal range portion of blob
    modcal_range = _parse_range(blob_data[-(defaults.MAX_EYES * MODULECAL_RANGE_SIZE * SIZEOF_FLOAT):])
    for eye in range(defaults.MAX_EYES):
        v5_blob[eye]['range'] = modcal_range[eye]
    return v5_blob


def _parse_module_cal_v6_blob(blob_data: bytes, context: None) -> any:
    def _parse_coupling_transform(blob_data: bytes):
        data_offset = 0
        transform = []
        for _ in range(defaults.MAX_EYES):
            transform.append([])
            for _ in range(NUM_SCAN_DIMS):
                eye_tf = struct.unpack_from(f'<{MODULECAL_NUM_COUPLING_TERMS}f', blob_data, data_offset)
                transform[-1].append(eye_tf)
                data_offset += MODULECAL_NUM_COUPLING_TERMS * SIZEOF_FLOAT
        return transform

    # Parse as v5 blob minus the coupling transform
    coupling_tf_size = defaults.MAX_EYES * MODULECAL_NUM_COUPLING_TERMS * NUM_SCAN_DIMS * SIZEOF_FLOAT
    v6_blob = _parse_module_cal_v5_blob(blob_data[:-coupling_tf_size],
                                        context)
    # Parse coupling transform portion of blob
    transform = _parse_coupling_transform(blob_data[-coupling_tf_size:])
    for eye in range(defaults.MAX_EYES):
        v6_blob[eye]['coupling_transform'] = transform[eye]
    return v6_blob


def _create_model_et_v2_blob(data: any, _context: None) -> bytes:

    def _load_fit_coefficients(data: any) -> bytes:
        padded_data = np.full((defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1), MODEL_ET_NUM_POLY_TERMS), np.nan)
        padded_data[:len(data), :] = data
        blob_data = []
        for dim in range(defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)):
            blob_data += struct.pack(f'<{MODEL_ET_NUM_POLY_TERMS}f', *padded_data[dim])
        return blob_data

    def _load_fit_intercepts(data: any) -> bytes:
        padded_data = np.full(defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1), np.nan)
        padded_data[:len(data)] = data
        return struct.pack(f'<{defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)}f', *padded_data)

    def _load_error_covariance(data: any) -> bytes:
        padded_data = np.full((defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1),
                               defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)), np.nan)
        padded_data[:len(data), :len(data[0])] = data
        blob_data = []
        for dim in range(defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)):
            blob_data += struct.pack(f'<{defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)}f', *padded_data[dim])
        return blob_data

    def _load_eye_offset(data: any) -> bytes:
        return struct.pack(f'<{XYZ_SIZE}f', *data)

    blob_data = []
    blob_data += struct.pack('<I', data['revision'])
    blob_data += _load_fit_coefficients(data['fit_coefficients'])
    blob_data += _load_fit_intercepts(data['fit_intercepts'])
    blob_data += _load_error_covariance(data['measurement_error_cov'])
    blob_data += _load_eye_offset(data['nominal_eye_offset'])
    return blob_data


def _parse_model_et_v1_blob(blob_data: bytes, _context: None) -> any:

    # in the first 3 helper functions, the np.nan values indicating inactive PDs must be dropped

    def _parse_fit_coefficients(blob_data: bytes, offset: int):
        data_offset = 0
        fit_coefficients = []
        for _ in range(defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)):
            fit_coefficients.append(struct.unpack_from(f'<{MODEL_ET_NUM_POLY_TERMS}f',
                                                       blob_data,
                                                       offset + data_offset))
            data_offset += MODEL_ET_NUM_POLY_TERMS * SIZEOF_FLOAT
        fit_coefficients = np.array(fit_coefficients)
        return fit_coefficients[np.all(np.isfinite(fit_coefficients), axis=1)]

    def _parse_fit_intercepts(blob_data: bytes, offset: int):
        fit_intercepts = np.array(struct.unpack_from(f'<{defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)}f',
                                                     blob_data,
                                                     offset))
        return fit_intercepts[np.isfinite(fit_intercepts)]

    def _parse_error_covariance(blob_data: bytes, offset: int):
        data_offset = 0
        error_cov = []
        for _ in range(defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)):
            error_cov.append(struct.unpack_from(f'<{defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)}f',
                                                blob_data,
                                                offset + data_offset))
            data_offset += defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1) * SIZEOF_FLOAT
        error_cov = np.array(error_cov)
        return np.asarray(error_cov[~np.all(np.isnan(error_cov), axis=0)][:, ~np.all(np.isnan(error_cov), axis=1)],
                          order='C')

    def _parse_eye_offset(blob_data: bytes, offset: int):
        return struct.unpack_from(f'<{XYZ_SIZE}f', blob_data, offset)

    model_params = {'fit_coefficients': [], 'fit_intercepts': [],
                    'measurement_error_cov': [], 'nominal_eye_offset': []}
    blob_data_offset = 0
    model_params['fit_coefficients'] = _parse_fit_coefficients(blob_data, blob_data_offset)
    blob_data_offset += defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1) * MODEL_ET_NUM_POLY_TERMS * SIZEOF_FLOAT
    model_params['fit_intercepts'] = _parse_fit_intercepts(blob_data, blob_data_offset)
    blob_data_offset += defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1) * SIZEOF_FLOAT
    model_params['measurement_error_cov'] = _parse_error_covariance(blob_data, blob_data_offset)
    blob_data_offset += ((defaults.MAX_EYES * (defaults.N_PHOTODIODES + 1)) ** 2) * SIZEOF_FLOAT
    model_params['nominal_eye_offset'] = _parse_eye_offset(blob_data, blob_data_offset)
    model_params['revision'] = 0
    return model_params


def _parse_model_et_v2_blob(blob_data: bytes, _context: None) -> any:
    # same as v1 but with an int32 revision header
    model_params = _parse_model_et_v1_blob(blob_data[4:], _context)
    model_params['revision'] = int.from_bytes(blob_data[:4], 'little')
    return model_params


def _create_model_priors_v2_blob(data: any, _context: None) -> bytes:

    blob_data = []
    blob_data += struct.pack('<I', data['revision'])
    for dim in range(NUM_SCAN_DIMS):
        for idim in range(PRIOR_INPUT_DIM):
            for idim2 in range(PRIOR_INPUT_DIM):
                blob_data += struct.pack(f'<{PRIOR_OUTPUT_DIM}f',
                                         *data['qinv'][dim][idim][idim2])
    for dim in range(NUM_SCAN_DIMS):
        for idim in range(PRIOR_INPUT_DIM):
            blob_data += struct.pack(f'<{PRIOR_OUTPUT_DIM}f',
                                     *data['mean'][dim][idim])
    return blob_data


def _parse_model_priors_v1_blob(blob_data: bytes, _context: None) -> any:

    blob_data_offset = 0
    transform_data = {'qinv': [], 'mean': []}
    for dim in range(NUM_SCAN_DIMS):
        transform_data['qinv'].append([])
        for idim in range(PRIOR_INPUT_DIM):
            transform_data['qinv'][dim].append([])
            for _ in range(PRIOR_INPUT_DIM):
                transform_data['qinv'][dim][idim].append(struct.unpack_from(
                    f'<{PRIOR_OUTPUT_DIM}f', blob_data, blob_data_offset))
                blob_data_offset += PRIOR_OUTPUT_DIM * SIZEOF_FLOAT

    for dim in range(NUM_SCAN_DIMS):
        transform_data['mean'].append([])
        for _ in range(PRIOR_INPUT_DIM):
            transform_data['mean'][dim].append(struct.unpack_from(
                f'<{PRIOR_OUTPUT_DIM}f', blob_data, blob_data_offset))
            blob_data_offset += PRIOR_OUTPUT_DIM * SIZEOF_FLOAT

    transform_data['revision'] = 0
    return transform_data


def _parse_model_priors_v2_blob(blob_data: bytes, _context: None) -> any:
    # same as v1 but with an int32 revision header
    transform_data = _parse_model_priors_v1_blob(blob_data[4:], _context)
    transform_data['revision'] = int.from_bytes(blob_data[:4], 'little')
    return transform_data


def _create_geometry_v3_blob(data: any, _context: namedtuple) -> bytes:

    blob_data = []
    blob_data += struct.pack('<I', data['revision'])
    blob_data += struct.pack('<f', data['scanner_separation'])
    blob_data += struct.pack(f'<{XYZ_SIZE}f', *np.array(data['incident_ray']).flatten())
    blob_data += struct.pack(f'<{XYZ_SIZE * XYZ_SIZE}f', *np.array(data['scanner_to_world_rotation']).flatten())
    blob_data += struct.pack(f'<{N_PDS * XYZ_SIZE}f', *np.array(data['photodiode_origins']).flatten())

    return blob_data


def _parse_geometry_v1_blob(blob_data: bytes, _context: None) -> any:

    offset = 0
    scanner_separation, = struct.unpack_from('<f', blob_data, offset)
    offset += 4
    incident_ray = struct.unpack_from(f'<{XYZ_SIZE}f', blob_data, offset)
    offset += 4 * XYZ_SIZE
    scanner_to_world_rotation = np.array(struct.unpack_from(f'<{XYZ_SIZE * XYZ_SIZE}f', blob_data, offset))
    scanner_to_world_rotation = scanner_to_world_rotation.reshape((XYZ_SIZE, XYZ_SIZE))

    return {
        'scanner_separation': scanner_separation,
        'incident_ray': incident_ray,
        'scanner_to_world_rotation': scanner_to_world_rotation
    }


def _parse_geometry_v2_blob(blob_data: bytes, _context: None) -> any:
    # same as v1 but with an int32 revision header
    geometry_data = _parse_geometry_v1_blob(blob_data[4:], _context)
    geometry_data['revision'] = int.from_bytes(blob_data[:4], 'little')
    return geometry_data


def _parse_geometry_v3_blob(blob_data: bytes, _context: None) -> any:
    # same as v2 but with photodiode origins
    v2_len = 56
    geometry_data = _parse_geometry_v2_blob(blob_data[:v2_len], _context)
    photodiode_origins = np.array(struct.unpack_from(f'<{N_PDS * XYZ_SIZE}f', blob_data, v2_len))
    geometry_data['photodiode_origins'] = photodiode_origins
    return geometry_data
