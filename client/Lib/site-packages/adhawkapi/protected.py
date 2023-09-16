'''This module provides a set of APIs to manipulate protected attributes in TROS'''

import contextlib
import logging
import typing

from . import base, blob_api, defaults, error, product_defs, publicapi, register_api, registers


class PersonalizeApi(register_api.RegisterApi):
    '''Provides a protected API to program device specific attributes'''

    def reload(self):
        '''Exposes the _rebuild_firmware_info method'''
        self._rebuild_firmware_info()


class PersonalizationSettings(typing.NamedTuple):
    '''Contains all the personalization settings for a device'''
    product_id: registers.SpecProductId
    serial_num: str
    ocular_mode: registers.SpecOcularMode


DEFAULT_DEAD_TIME = 100
# iris imaging defaults
DEFAULT_IRIS_CAPTURE_TIME = 500
DEFAULT_IRIS_SEGMENT_COUNT = 10
DEFAULT_IRIS_SAMPLE_COUNT = 500
DEFAULT_IRIS_SAMPLE_RATE = 2000000
DEFAULT_IRIS_SAMPLE_PHASE = 140
DEFAULT_IRIS_IMAGE_WIDTH = 200
DEFAULT_IRIS_IMAGE_CORRECTION = registers.AnaloglissajousImageCorrectionType.COSINE
DEFAULT_IRIS_IMAGE_ALGORITHM = registers.AnaloglissajousImageGenerationAlgorithm.ONE_PIXEL_AVERAGING
DEFAULT_IRIS_IMAGE_POSTPROCESSING = registers.AnaloglissajousImagePostprocessing.AVERAGE
DEFAULT_IRIS_STARTUP_PERIOD = 100
DEFAULT_IRIS_NEGATIE_SLEW = -120
DEFAULT_IRIS_SATURATION_LIMIT_HIGH = 200
DEFAULT_IRIS_SATURATION_LIMIT_LOW = 120


class Personalizer:
    '''Helper class for personalizing hardware devices'''

    def __init__(self, *args, **kwargs):
        self._api = PersonalizeApi(*args, **kwargs)
        self._board_id = self._api.get_register(registers.ISP_BOARD_TYPE)
        serial_num = self._api.get_register(registers.SPEC_SERIAL_NUMBER)
        product_id = self._api.get_register(registers.SPEC_PRODUCT_ID)
        try:
            ocular_mode = registers.SpecOcularMode(
                self._api.get_register(registers.SPEC_OCULAR_MODE))
        except base.MinimumAPIVersion:
            ocular_mode = registers.SpecOcularMode.BINOCULAR

        try:
            self._settings = PersonalizationSettings(
                registers.SpecProductId(product_id), serial_num, ocular_mode)
        except ValueError as excp:
            raise error.InternalError(f'Unsupported product ID: {excp}')

    @property
    def api_version(self):
        '''Returns the firmware api version'''
        return self._api.firmware_info.api_version

    @property
    def supported_products(self):
        '''Returns the list of supported products for the current hardware'''
        return [(spec.DISPLAY_NAME, spec.PRODUCT_ID)
                for spec in product_defs.by_board(self._board_id)]

    @property
    def settings(self):
        '''Returns the current personalization settings from the hardware'''
        return self._settings

    def personalize(self, configs: PersonalizationSettings = None):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        '''Personalize the device according the provided info'''
        if configs is None:
            configs = self._settings

        spec = product_defs.by_id(configs.product_id)
        assert spec.BOARD_TYPE == self._board_id

        control_caps = list(spec.CONTROL_CAPS)
        num_trackers = len(spec.TRACKER_CAPS)
        num_devices = num_trackers + 1

        try:
            self._api.set_register(registers.SPEC_OCULAR_MODE, configs.ocular_mode)
        except base.MinimumAPIVersion:
            if configs.ocular_mode != registers.SpecOcularMode.BINOCULAR:
                raise base.MinimumAPIVersion('Monocular mode is not supported in this firmware. Please upgrade.')

        if configs.ocular_mode == registers.SpecOcularMode.BINOCULAR:
            # Single tracker optimization allows frequency tuning on monocular devices
            # Binocular devices personalized as monocular can have this capability set as well
            # If re-personalizing to binocular, remove the single tracker optimization capability
            with contextlib.suppress(ValueError):
                control_caps.remove(registers.SpecCapability.SINGLE_TRACKER_OPTIMIZATION)

        self._api.set_register(registers.GENERAL1_MULTI_DEVICES, [num_devices, 0, num_trackers])
        self._api.set_register(registers.SPEC_PRODUCT_ID, configs.product_id)
        self._api.set_register(registers.SPEC_PRODUCT_CATEGORY, spec.PRODUCT_CATEGORY)
        self._api.set_register(registers.SPEC_CAMERA, spec.CAMERA_TYPE)
        self._api.set_register(registers.SPEC_CAPABILITY, control_caps)
        self._api.set_register(registers.SPEC_SERIAL_NUMBER, configs.serial_num)

        self._api.set_register(registers.GENERAL2_FLUSH, 1)

        for tracker_id in range(defaults.MAX_SCANNERS):

            self._api.set_register(registers.SPEC_CAPABILITY, spec.TRACKER_CAPS[tracker_id], tracker_id)
            pd_order_enc = 0
            for pd_id in reversed(spec.PD_ORDER[tracker_id]):
                pd_order_enc = (pd_order_enc << 4) + (pd_id & 0xf)
            pd_type_enc = 0
            for value in reversed(spec.PD_TYPE[tracker_id]):
                pd_type_enc = (pd_type_enc << 4) + (value & 0xf)
            self._api.set_register(registers.SPEC_PD_ORDER, pd_order_enc, tracker_id)
            with contextlib.suppress(base.MinimumAPIVersion):
                self._api.set_register(registers.SPEC_PD_TYPE, pd_type_enc, tracker_id)
            self._api.set_register(registers.SPEC_SCANNER_ORIENTATION, spec.SCANNER_ORIENTATION[tracker_id], tracker_id)
            self._api.set_register(registers.SPEC_X_MAX, defaults.DEFAULT_X_MAX, tracker_id)
            self._api.set_register(registers.SPEC_X_MIN, defaults.DEFAULT_X_MIN, tracker_id)
            self._api.set_register(registers.SPEC_Y_MAX, defaults.DEFAULT_Y_MAX, tracker_id)
            self._api.set_register(registers.SPEC_Y_MIN, defaults.DEFAULT_Y_MIN, tracker_id)
            self._api.set_register(registers.GENERAL1_DEAD_TIME_X, DEFAULT_DEAD_TIME, tracker_id)
            self._api.set_register(registers.GENERAL1_DEAD_TIME_Y, DEFAULT_DEAD_TIME, tracker_id)

            self._api.set_register(registers.SPEC_MAX_VCSEL_CURRENT, spec.MAX_LASER_CURRENT, tracker_id)
            laser_current = self._api.get_register(registers.GENERAL1_LASER_CURRENT, tracker_id)
            if laser_current > spec.MAX_LASER_CURRENT:
                self._api.set_register(registers.GENERAL1_LASER_CURRENT, spec.MAX_LASER_CURRENT, tracker_id)

            self._api.set_register(registers.SPEC_MAX_DUTY_CYCLE, spec.MAX_DUTY_CYCLE, tracker_id)
            duty_cycle = self._api.get_register(registers.GENERAL1_MODULATION_DUTY_CYCLE, tracker_id)
            if duty_cycle > spec.MAX_DUTY_CYCLE:
                self._api.set_register(registers.GENERAL1_MODULATION_DUTY_CYCLE, spec.MAX_DUTY_CYCLE, tracker_id)

            # set defaults for the productized iris imaging app
            with contextlib.suppress(base.MinimumAPIVersion):
                self._api.set_register(registers.ANALOGLISSAJOUS_CAPTURE_TIME,
                                       DEFAULT_IRIS_CAPTURE_TIME, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_SEGMENT_COUNT,
                                       DEFAULT_IRIS_SEGMENT_COUNT, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_SAMPLE_COUNT,
                                       DEFAULT_IRIS_SAMPLE_COUNT, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_SAMPLE_RATE,
                                       DEFAULT_IRIS_SAMPLE_RATE, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_SAMPLE_PHASE,
                                       DEFAULT_IRIS_SAMPLE_PHASE, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_IMAGE_WIDTH,
                                       DEFAULT_IRIS_IMAGE_WIDTH, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_IMAGE_CORRECTION_TYPE,
                                       DEFAULT_IRIS_IMAGE_CORRECTION, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_IMAGE_GENERATION_ALGORITHM,
                                       DEFAULT_IRIS_IMAGE_ALGORITHM, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_IMAGE_POSTPROCESSING,
                                       DEFAULT_IRIS_IMAGE_POSTPROCESSING, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_STARTUP_PERIOD,
                                       DEFAULT_IRIS_STARTUP_PERIOD, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_NEGATIVE_SLEW,
                                       DEFAULT_IRIS_NEGATIE_SLEW, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_SATURATION_LIMIT_HIGH,
                                       DEFAULT_IRIS_SATURATION_LIMIT_HIGH, tracker_id)
                self._api.set_register(registers.ANALOGLISSAJOUS_SATURATION_LIMIT_LOW,
                                       DEFAULT_IRIS_SATURATION_LIMIT_LOW, tracker_id)

        self._api.set_register(registers.GENERAL2_FLUSH, 1)
        self._api.reload()

        # Attempt to write each of the blob constants
        spec_blob_map = {
            'FUSION_CONSTS': publicapi.BlobType.DYNAMIC_FUSION,
            'MODEL_ET': publicapi.BlobType.MODEL_ET,
            'MODEL_PRIORS': publicapi.BlobType.MODEL_PRIORS,
            'GEOMETRY': publicapi.BlobType.GEOMETRY,
        }

        for spec_key, blob_type in spec_blob_map.items():
            spec_data = getattr(spec, spec_key)
            if spec_data is not None:
                try:
                    blob_api.write_blob(blob_type, spec_data)
                except error.Error as exc:
                    logging.error(exc)

    def shutdown(self):
        '''Shutdown the personalizer API'''
        self._api.shutdown()
