'''This module is used to map a config to a register or a blob item'''

import abc
import collections.abc
import contextlib
import enum
import logging

from . import BlobType, Error, EyeMask, blob_parsers, configs, defaults, normalize, registers, trackermodel, version


class DataSource(enum.IntEnum):
    '''The datasource for a particular config'''
    REGISTERS = 0
    BLOBS = 1


class ConfigHandlerInterface(abc.ABC):
    '''Abstract base class that specifies the model to hardware interface'''

    @abc.abstractmethod
    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        '''Update the hardware'''
        pass

    @abc.abstractmethod
    def read(self, api, configmodel, tracker_id, config, **extra_args):
        '''Read from the hardware and return the value in the form the model understands'''
        pass


class ModelToReg(ConfigHandlerInterface):
    '''Handler for a 1 to 1 mapping between a config in the model and a register'''

    source = DataSource.REGISTERS

    def __init__(self, regkey):
        self._regkey = regkey

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        api.set_register(self._regkey, value, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        return api.get_register(self._regkey, tracker_id)


class ModelToMultiReg(ConfigHandlerInterface):
    '''Handler for a 1 to many mapping between a config in the model and certain registers'''

    source = DataSource.REGISTERS

    def __init__(self, regkey):
        self._regkey = regkey

    def write(self, value, api, configmodel, _tracker_id, config, **extra_args):
        trids = api.firmware_info.active_trackers
        for trid in trids:
            api.set_register(self._regkey, value, trid)

    def read(self, api, configmodel, _tracker_id, config, **extra_args):
        trids = api.firmware_info.active_trackers
        return api.get_register(self._regkey, trids[0])


class ModelToBlob(ConfigHandlerInterface):
    '''Handler for a 1 to 1 mapping between a config in the model and a blob'''

    source = DataSource.BLOBS

    def __init__(self, blobtype):
        self._blobtype = blobtype

    def _get_blob_context(self, _api):
        '''Returns the context required for the blob'''
        return None

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        ctxt = self._get_blob_context(api)  # pylint: disable=assignment-from-none
        try:
            api.write_blob(self._blobtype, value, ctxt)
        except Error as excp:
            logging.warning(f'Unable to write {config}: {excp}')

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        ctxt = self._get_blob_context(api)  # pylint: disable=assignment-from-none
        try:
            return api.read_blob(self._blobtype, ctxt)
        except Error as excp:
            logging.warning(f'Unable to read {config}: {excp}')
            return {}


class ModelToSpecBlob(ModelToBlob):
    '''Class mapping a single configuration to blobs defined in product specs'''

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        # Never overwrite spec blobs
        pass

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        value = super().read(api, configmodel, tracker_id, config, **extra_args)
        return value.get('revision', 0) if isinstance(value, dict) else 0


class ModelToMultiglintBlob(ModelToBlob):
    '''Interface between the model and the multiglint blob'''

    def _get_blob_context(self, _api):
        return blob_parsers.MultiglintContext(defaults.MAX_EYES)


class ModelToCalibrationBlob(ModelToBlob):
    '''Interface between the model and the calibration blob'''

    def _get_blob_context(self, _api):
        return blob_parsers.CalibrationContext(EyeMask.BINOCULAR)


class ModelToSelectionRegister(ModelToReg):
    '''Interface the model properly with selection registers'''

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        register_value = api.get_register(self._regkey, tracker_id)
        if isinstance(register_value, collections.abc.Mapping):
            key, _val = register_value.popitem()
            return key
        return register_value


class ModelToRegBool(ModelToReg):
    '''Interface with the registers to return a boolean configuration'''

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        return bool(super().read(api, configmodel, tracker_id, config, **extra_args))


class APIVersion(ConfigHandlerInterface):
    '''Interface that translates the api version'''

    source = DataSource.REGISTERS

    def __init__(self):
        self._regkey = registers.GENERAL1_API_VERSION

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        vers = version.SemanticVersion.from_string(value)
        api.set_register(self._regkey, [vers.minor, vers.major])

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        minor, major = api.get_register(self._regkey)
        return str(version.SemanticVersion(major, minor, 0))


class NumTrackers(ConfigHandlerInterface):
    '''Interface that translates the number of trackers'''

    source = DataSource.REGISTERS

    def __init__(self):
        self._regkey = registers.GENERAL1_MULTI_DEVICES

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        current = api.get_register(self._regkey)
        current[2] = value
        api.set_register(self._regkey, current)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        return api.get_register(self._regkey)[2]


class ActiveEyes(ConfigHandlerInterface):
    '''Interface that translates the active eyes'''

    source = DataSource.REGISTERS

    def __init__(self):
        self._regkey = registers.SPEC_OCULAR_MODE

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        ocular_mode = 0
        for eye in value:
            ocular_mode |= 1 << eye
        api.set_register(self._regkey, ocular_mode)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        ocular_mode = registers.SpecOcularMode(api.get_register(self._regkey))
        active_eyes = [eye for eye in range(defaults.MAX_EYES) if ocular_mode.value & 1 << eye]
        return active_eyes


class PdGain(ConfigHandlerInterface):
    '''Interface that translates the pd gain setting between the model and registers'''

    source = DataSource.REGISTERS

    # Map of PD ID to the equivalent PD Gain Register
    _regmap = {
        0: registers.GENERAL1_PD0_GAIN,
        1: registers.GENERAL1_PD1_GAIN,
        2: registers.GENERAL1_PD2_GAIN,
        3: registers.GENERAL1_PD3_GAIN,
        4: registers.GENERAL1_PD4_GAIN,
        5: registers.GENERAL1_PD5_GAIN
    }

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if configmodel.get_value(trackermodel.construct_path(None, configs.SPEC_SHARED_DETECTOR_CAPABILITY)):
            return
        regkey = self._regmap[extra_args['pd_id']]
        api.set_register(regkey, value, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        if registers.SpecCapability.SHARED_DETECTOR_CAPABILITY in \
                api.get_register(registers.SPEC_CAPABILITY):
            # hardware does not support this, just return whats in the model
            return configmodel.get_value(trackermodel.construct_path(tracker_id, config, **extra_args))
        regkey = self._regmap[extra_args['pd_id']]
        return api.get_register(regkey, tracker_id)


class AutotuneControl(ConfigHandlerInterface):
    '''Interface that translates between the enable_diag and algorithm parameters in the model
    to the Autotune Control Register
    '''

    source = DataSource.REGISTERS

    def __init__(self):
        self._regkey = registers.AUTOTUNE_CONTROL

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        regvalues = [
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.AUTOTUNE_ENABLEDIAG)),
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.AUTOTUNE_ALGORITHM))]
        api.set_register(self._regkey, regvalues, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        regvalues = api.get_register(self._regkey, tracker_id)
        if config == configs.AUTOTUNE_ENABLEDIAG:
            return bool(regvalues[0])
        return regvalues[1]


class AutotuneComponentAlgorithm(ConfigHandlerInterface):
    '''Interface that translates between setting the different autotune component algorithms in the model
       to the Autotune component algorithms register'''

    source = DataSource.REGISTERS

    def __init__(self):
        self._regkey = registers.AUTOTUNE_ALGORITHM_SELECTION

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        # Step 3 and 4 are unused for now. Add them in as necessary
        regvalues = [
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.AUTOTUNE_ALGORITHM_STEP1)),
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.AUTOTUNE_ALGORITHM_STEP2)),
            0,
            0
        ]
        api.set_register(self._regkey, regvalues, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        regvalues = api.get_register(self._regkey, tracker_id)
        # Step 3 and 4 are unused for now. Add them in as necessary
        if config == configs.AUTOTUNE_ALGORITHM_STEP1:
            return regvalues[0]
        return regvalues[1]


class PdBitFields(ConfigHandlerInterface):
    '''Interface that translates between the model and registers for
       fields where the bit position represents the pd id
       '''

    source = DataSource.REGISTERS

    def __init__(self, configkey, regkey):
        self._configkey = configkey
        self._regkey = regkey

    @staticmethod
    def _get_max_pds(pd_type):
        '''Get the max pds based on the pd type'''
        if pd_type == 'pd':
            return defaults.N_PHOTODIODES
        if pd_type == 'pupilpd':
            return defaults.MAX_PUPIL_DETECTORS
        return defaults.MAX_SHARED_DETECTORS

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        choices = set()
        max_pds = self._get_max_pds(extra_args['pd_type'])
        for pd_id in range(max_pds):
            # Check the configuration for every pd, so we can construct the bitfield correctly
            value = configmodel.get_value(trackermodel.construct_path(
                tracker_id, self._configkey, pd_type=extra_args['pd_type'], pd_id=pd_id))
            if value:
                choices.add(pd_id)
        api.set_register(self._regkey, choices, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        choices = api.get_register(self._regkey, tracker_id)
        return extra_args['pd_id'] in choices


class PdEnable(PdBitFields):
    '''Interface to enable/disable the glint pds'''

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if not configmodel.get_value(trackermodel.construct_path(None, configs.SPEC_SHARED_DETECTOR_CAPABILITY)):
            super().write(value, api, configmodel, tracker_id, config, **extra_args)


class PupilPdEnable(PdBitFields):
    '''Interface to enable/disable the pupil pds'''

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if not configmodel.get_value(trackermodel.construct_path(None, configs.SPEC_SHARED_DETECTOR_CAPABILITY)):
            super().write(value, api, configmodel, tracker_id, config, **extra_args)


class DetectorEnable(PdBitFields):
    '''Interface to enable/disable detectors on boards with the shared detector capability'''

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if configmodel.get_value(trackermodel.construct_path(None, configs.SPEC_SHARED_DETECTOR_CAPABILITY)):
            super().write(value, api, configmodel, tracker_id, config, **extra_args)


class DetectorType(ModelToReg):
    '''Interface between the model and registers to get the type of detector'''

    source = DataSource.REGISTERS

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        regvalues = api.get_register(self._regkey)
        mask = 0xf << (4 * extra_args['pd_id'])
        regvalues = (regvalues & ~mask) | (value << (4 * extra_args['pd_id']))
        api.set_register(registers.SPEC_PD_TYPE, regvalues, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        regvalues = api.get_register(self._regkey, tracker_id)
        return (regvalues >> (4 * extra_args['pd_id'])) & 0xf


class SharedPdCapability(ConfigHandlerInterface):
    '''Interface between the model and registers to determine if the device supports shared pds'''

    source = DataSource.REGISTERS

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        capabilities = api.get_register(registers.SPEC_CAPABILITY)
        if value:
            capabilities.append(registers.SpecCapability.SHARED_DETECTOR_CAPABILITY)
        else:
            try:
                capabilities.remove(registers.SpecCapability.SHARED_DETECTOR_CAPABILITY)
            except ValueError:
                pass
        api.set_register(registers.SPEC_CAPABILITY, capabilities)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        capabilities = api.get_register(registers.SPEC_CAPABILITY)
        return registers.SpecCapability.SHARED_DETECTOR_CAPABILITY in capabilities


class PupilPdGain(ConfigHandlerInterface):
    '''Interface that translates the pd gain setting between the model and registers'''

    source = DataSource.REGISTERS

    # Map of PD ID to the equivalent PD Gain Register
    _regmap = {
        0: registers.GENERAL1_PUPILPD0_GAIN,
        1: registers.GENERAL1_PUPILPD1_GAIN,
    }

    def __init__(self, configkey):
        self._configkey = configkey

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if configmodel.get_value(trackermodel.construct_path(None, configs.SPEC_SHARED_DETECTOR_CAPABILITY)):
            return
        regvalues = [
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.PD_GAIN, **extra_args)),
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.PD_GAINBOOST, **extra_args))
        ]

        api.set_register(self._regmap[extra_args['pd_id']], regvalues, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        if registers.SpecCapability.SHARED_DETECTOR_CAPABILITY in \
                api.get_register(registers.SPEC_CAPABILITY):
            # hardware does not support this, just return whats in the model
            return configmodel.get_value(trackermodel.construct_path(tracker_id, config, **extra_args))
        regvalues = api.get_register(self._regmap[extra_args['pd_id']], tracker_id)
        if self._configkey == configs.PD_GAINBOOST:
            return regvalues[1] == 1  # The gain boost configuration is a boolean
        return regvalues[0]


class SharedPdGain(ConfigHandlerInterface):
    '''Interface that translates the gain settings between the model and registers for shared detectors
    These detectors have common, glint and pupil gains that can be configured separately
    all mapped to a single register.
    '''
    source = DataSource.REGISTERS

    def __init__(self, configkey):
        self._configkey = configkey

    # Map of Shared PD ID to the equivalent PD Gain Register
    _regmap = {
        0: registers.GENERAL1_GLINT_AND_PUPIL_PD0_GAINS,
        1: registers.GENERAL1_GLINT_AND_PUPIL_PD1_GAINS,
        2: registers.GENERAL1_GLINT_AND_PUPIL_PD2_GAINS
    }

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if not configmodel.get_value(trackermodel.construct_path(None, configs.SPEC_SHARED_DETECTOR_CAPABILITY)):
            return
        regvalues = [
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.PD_COMMONGAIN, **extra_args)) - 1,
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.PD_GLINTGAIN, **extra_args)) - 1,
            configmodel.get_value(trackermodel.construct_path(tracker_id, configs.PD_PUPILGAIN, **extra_args)) - 1
        ]
        api.set_register(self._regmap[extra_args['pd_id']], regvalues, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        if registers.SpecCapability.SHARED_DETECTOR_CAPABILITY not in \
                api.get_register(registers.SPEC_CAPABILITY):
            # hardware does not support this, just return whats in the model
            return configmodel.get_value(trackermodel.construct_path(tracker_id, config, **extra_args))
        regvalues = api.get_register(self._regmap[extra_args['pd_id']], tracker_id)
        idx = [configs.PD_COMMONGAIN, configs.PD_GLINTGAIN, configs.PD_PUPILGAIN]
        return regvalues[idx.index(self._configkey)] + 1


@contextlib.contextmanager
def cache_and_restore(regapi, tracker_id, reglist):
    '''Context manager that caches and restores a list of registers
    if the code within the context raises any exceptions.

    This is useful if there are multiple registers being set for a single
    configuration change. If there is a failure in a single transaction,
    we can roll the entire change set back

    It re-raises the same exception once the rollback is completed
    '''
    cache = []
    for reg in reglist:
        cache.append(regapi.get_register(reg, tracker_id))
    try:
        yield cache
    except Exception:  # pylint: disable=broad-except
        for reg, cache in zip(reglist, cache):
            regapi.set_register(reg, cache, tracker_id)
        raise


class LaserConfig(ConfigHandlerInterface):
    '''Handle laser configuration changes'''

    source = DataSource.REGISTERS

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        if config == configs.TRACKER_LASERCURRENTPCT:
            max_val = api.get_register(registers.SPEC_MAX_VCSEL_CURRENT, tracker_id)
            value = normalize.normalize(value, (0, 100), (0, max_val))

        # update the hardware
        api.set_register(registers.GENERAL1_LASER_CURRENT, value, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        value = api.get_register(registers.GENERAL1_LASER_CURRENT, tracker_id)
        if config == configs.TRACKER_LASERCURRENTPCT:
            max_val = api.get_register(registers.SPEC_MAX_VCSEL_CURRENT, tracker_id)
            value = normalize.normalize(value, (0, max_val), (0, 100))
        return value


class TrackerSize(ConfigHandlerInterface):
    '''Interface that translates between the tracker size values (width or height) to min, max
    in the x or y dimension'''

    source = DataSource.REGISTERS

    def __init__(self, mean_config, min_reg, max_reg, spec_min_reg, spec_max_reg):
        self._mean_config = mean_config
        self._min_reg = min_reg
        self._max_reg = max_reg
        self._spec_min_reg = spec_min_reg
        self._spec_max_reg = spec_max_reg

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        # get the mean from the configs
        mean = configmodel.get_value(trackermodel.construct_path(tracker_id, self._mean_config))

        # given the updated size and the mean, find the min and max
        min_val = mean - (value / 2)
        max_val = mean + (value / 2)

        if config.endswith('pct'):
            # convert the pct values to absolute values using the restricted range from the spec
            spec_min_val = api.get_register(self._spec_min_reg, tracker_id)
            spec_max_val = api.get_register(self._spec_max_reg, tracker_id)
            min_val = normalize.normalize(min_val, (0, 100), (spec_min_val, spec_max_val))
            max_val = normalize.normalize(max_val, (0, 100), (spec_min_val, spec_max_val))

        with cache_and_restore(api, tracker_id, [self._min_reg, self._max_reg]):
            # update the hardware
            api.set_register(self._min_reg, min_val, tracker_id)
            api.set_register(self._max_reg, max_val, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        min_val = api.get_register(self._min_reg, tracker_id)
        max_val = api.get_register(self._max_reg, tracker_id)
        if config.endswith('pct'):
            # convert the absolute values to pct values using the restricted range from the spec
            spec_min_val = api.get_register(self._spec_min_reg, tracker_id)
            spec_max_val = api.get_register(self._spec_max_reg, tracker_id)
            min_val = normalize.normalize(min_val, (spec_min_val, spec_max_val), (0, 100))
            max_val = normalize.normalize(max_val, (spec_min_val, spec_max_val), (0, 100))
        return int(round(max_val - min_val))


class TrackerMean(ConfigHandlerInterface):
    '''Interface that translates between tracker mean values to min, max
    in the x or y dimension'''

    source = DataSource.REGISTERS

    def __init__(self, size_config, min_reg, max_reg, spec_min_reg, spec_max_reg):
        self._size_config = size_config
        self._min_reg = min_reg
        self._max_reg = max_reg
        self._spec_min_reg = spec_min_reg
        self._spec_max_reg = spec_max_reg

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):

        # get the size from the configs
        size = configmodel.get_value(trackermodel.construct_path(tracker_id, self._size_config))
        # given the updated mean and the size, find the min and max
        min_val = value - (size / 2)
        max_val = value + (size / 2)

        if config.endswith('pct'):
            # convert the pct values to absolute values using the restricted range from the spec
            spec_min_val = api.get_register(self._spec_min_reg, tracker_id)
            spec_max_val = api.get_register(self._spec_max_reg, tracker_id)
            min_val = normalize.normalize(min_val, (0, 100), (spec_min_val, spec_max_val))
            max_val = normalize.normalize(max_val, (0, 100), (spec_min_val, spec_max_val))

        with cache_and_restore(api, tracker_id, [self._min_reg, self._max_reg]):
            # update the hardware
            api.set_register(self._min_reg, min_val, tracker_id)
            api.set_register(self._max_reg, max_val, tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        min_val = api.get_register(self._min_reg, tracker_id)
        max_val = api.get_register(self._max_reg, tracker_id)
        if config.endswith('pct'):
            # convert the pct values to absolute values using the restricted range from the spec
            spec_max_val = api.get_register(self._spec_max_reg, tracker_id)
            spec_min_val = api.get_register(self._spec_min_reg, tracker_id)
            min_val = normalize.normalize(min_val, (spec_min_val, spec_max_val), (0, 100))
            max_val = normalize.normalize(max_val, (spec_min_val, spec_max_val), (0, 100))
        return int(round((min_val + max_val) / 2))


class DeadTimeEnableConfig(ConfigHandlerInterface):
    '''Interface that handles converting boolean dead time enable to dead time mode selection'''

    source = DataSource.REGISTERS

    def __init__(self):
        self._regkey = registers.GENERAL1_DEAD_TIME_MODE

    def write(self, value, api, configmodel, tracker_id, config, **extra_args):
        '''Update the hardware'''
        api.set_register(
            self._regkey,
            registers.General1DeadTimeMode.NO_DEAD_TIME if value is False else
            registers.General1DeadTimeMode.CONSTANT_TIME_HALF_CYCLE_MAX,
            tracker_id)

    def read(self, api, configmodel, tracker_id, config, **extra_args):
        '''Read from the hardware and return the value in the form the model understands'''
        register_value = api.get_register(self._regkey, tracker_id)
        if isinstance(register_value, collections.abc.Mapping):
            key, _val = register_value.popitem()
            return key in (registers.General1DeadTimeMode.CONSTANT_TIME_HALF_CYCLE_MAX,
                           registers.General1DeadTimeMode.CONSTANT_TIME_FULL_CYCLE_MAX)
        return register_value in (registers.General1DeadTimeMode.CONSTANT_TIME_HALF_CYCLE_MAX,
                                  registers.General1DeadTimeMode.CONSTANT_TIME_FULL_CYCLE_MAX)


# pylint: disable=line-too-long
_CONFIG_HANDLER_MAP = {
    configs.GENERAL_APIVERSION: APIVersion(),
    configs.GENERAL_FIRMWAREVERSION: ModelToReg(registers.SPEC_BUILD),
    configs.GENERAL_NUMTRACKERS: NumTrackers(),
    configs.GENERAL_ACTIVEEYES: ActiveEyes(),
    configs.EYETRACKER_PUPIL_OFFSET: ModelToReg(registers.GENERAL1_PUPIL_OFFSET),
    configs.EYETRACKER_ALG_PIPELINE: ModelToSelectionRegister(registers.GENERAL1_ALG_PIPELINE),
    configs.EYETRACKER_REALTIME_Z_ENABLE: ModelToRegBool(registers.GENERAL1_REALTIME_Z_ENABLE),
    configs.METRICS_FLASH_ERASE_COUNT: ModelToReg(registers.GENERAL2_FLASH_ERASE_COUNT),
    configs.METRICS_FLASH_WRITE_COUNT: ModelToReg(registers.GENERAL2_FLASH_WRITE_COUNT),
    configs.METRICS_LIFETIME_COUNTER: ModelToReg(registers.GENERAL1_LIFETIME_COUNTER),
    configs.SPEC_PRODUCT_ID: ModelToSelectionRegister(registers.SPEC_PRODUCT_ID),
    configs.SPEC_BOARD_TYPE: ModelToSelectionRegister(registers.ISP_BOARD_TYPE),
    configs.SPEC_SERIAL_NUM: ModelToReg(registers.SPEC_SERIAL_NUMBER),
    configs.SPEC_SHARED_DETECTOR_CAPABILITY: SharedPdCapability(),
    configs.SPEC_DEVICE_TUNE_VERSION: ModelToReg(registers.SPEC_DEVICE_TUNE_VERSION),
    configs.SPEC_DEVICE_TUNE_DATE: ModelToReg(registers.SPEC_DEVICE_TUNE_DATE),
    configs.SPEC_MCU_CLOCK: ModelToReg(registers.GENERAL1_MCU_CLOCK),
    configs.SPEC_CAMERA: ModelToReg(registers.SPEC_CAMERA),
    configs.SPEC_OCULAR_MODE: ModelToReg(registers.SPEC_OCULAR_MODE),
    configs.TRACKER_LASERCURRENT: LaserConfig(),
    configs.TRACKER_LASERCURRENTPCT: LaserConfig(),
    configs.TRACKER_MODULATIONFREQUENCY: ModelToReg(registers.GENERAL1_MODULATION_FREQUENCY),
    configs.TRACKER_MODULATIONDUTYCYCLE: ModelToReg(registers.GENERAL1_MODULATION_DUTY_CYCLE),
    configs.TRACKER_FREQUENCY: ModelToReg(registers.GENERAL1_CONFIGURED_X_FREQUENCY),
    configs.TRACKER_YFREQUENCY: ModelToReg(registers.GENERAL1_CONFIGURED_Y_FREQUENCY),
    configs.TRACKER_XRESONANCEFREQUENCY: ModelToReg(registers.SPEC_RES_FREQ_X),
    configs.TRACKER_YRESONANCEFREQUENCY: ModelToReg(registers.SPEC_RES_FREQ_Y),
    configs.TRACKER_XPHASE: ModelToReg(registers.GENERAL1_X_PHASE),
    configs.TRACKER_YPHASE: ModelToReg(registers.GENERAL1_Y_PHASE),
    configs.TRACKER_GLINTPWFILTERTHRESHOLD_MAX: ModelToReg(registers.GENERAL1_GLINT_PW_FILTER_MAX_THRESHOLD),
    configs.TRACKER_GLINTPWFILTERTHRESHOLD_MIN: ModelToReg(registers.GENERAL1_GLINT_PW_FILTER_MIN_THRESHOLD),
    configs.TRACKER_PUPILPWFILTERTHRESHOLD_MAX: ModelToReg(registers.GENERAL1_PUPIL_PW_FILTER_MAX_THRESHOLD),
    configs.TRACKER_PUPILPWFILTERTHRESHOLD_MIN: ModelToReg(registers.GENERAL1_PUPIL_PW_FILTER_MIN_THRESHOLD),
    configs.TRACKER_XMEAN: TrackerMean(
        configs.TRACKER_WIDTH,
        registers.MEGALISA_X_MIN, registers.MEGALISA_X_MAX,
        registers.SPEC_X_MIN, registers.SPEC_X_MAX),
    configs.TRACKER_YMEAN: TrackerMean(
        configs.TRACKER_HEIGHT,
        registers.MEGALISA_Y_MIN, registers.MEGALISA_Y_MAX,
        registers.SPEC_Y_MIN, registers.SPEC_Y_MAX),
    configs.TRACKER_WIDTH: TrackerSize(
        configs.TRACKER_XMEAN,
        registers.MEGALISA_X_MIN, registers.MEGALISA_X_MAX,
        registers.SPEC_X_MIN, registers.SPEC_Y_MAX),
    configs.TRACKER_HEIGHT: TrackerSize(
        configs.TRACKER_YMEAN,
        registers.MEGALISA_Y_MIN, registers.MEGALISA_Y_MAX,
        registers.SPEC_Y_MIN, registers.SPEC_Y_MAX),
    configs.TRACKER_XMEAN_PCT: TrackerMean(
        configs.TRACKER_WIDTH_PCT,
        registers.MEGALISA_X_MIN, registers.MEGALISA_X_MAX,
        registers.SPEC_X_MIN, registers.SPEC_X_MAX),
    configs.TRACKER_YMEAN_PCT: TrackerMean(
        configs.TRACKER_HEIGHT_PCT,
        registers.MEGALISA_Y_MIN, registers.MEGALISA_Y_MAX,
        registers.SPEC_Y_MIN, registers.SPEC_Y_MAX),
    configs.TRACKER_WIDTH_PCT: TrackerSize(
        configs.TRACKER_XMEAN_PCT,
        registers.MEGALISA_X_MIN, registers.MEGALISA_X_MAX,
        registers.SPEC_X_MIN, registers.SPEC_Y_MAX),
    configs.TRACKER_HEIGHT_PCT: TrackerSize(
        configs.TRACKER_YMEAN_PCT,
        registers.MEGALISA_Y_MIN, registers.MEGALISA_Y_MAX,
        registers.SPEC_Y_MIN, registers.SPEC_Y_MAX),
    configs.TRACKER_XDEADTIME: ModelToReg(registers.GENERAL1_DEAD_TIME_X),
    configs.TRACKER_YDEADTIME: ModelToReg(registers.GENERAL1_DEAD_TIME_Y),
    configs.TRACKER_DEADTIMEMODE: ModelToSelectionRegister(registers.GENERAL1_DEAD_TIME_MODE),
    configs.TRACKER_DEADTIME_ENABLE: DeadTimeEnableConfig(),
    configs.TRACKER_COMPONENT_OFFSET_X: ModelToReg(registers.GENERAL1_COMPONENT_OFFSET_X),
    configs.TRACKER_COMPONENT_OFFSET_Y: ModelToReg(registers.GENERAL1_COMPONENT_OFFSET_Y),
    configs.TRACKER_COMPONENT_OFFSET_Z: ModelToReg(registers.GENERAL1_COMPONENT_OFFSET_Z),
    configs.TRACKER_SUBWINDOWING_ENABLE: ModelToReg(registers.GENERAL1_SUB_WINDOWING_ENABLE),
    configs.TRACKER_SUBWINDOWING_X_MIN: ModelToReg(registers.GENERAL1_SUB_WINDOWING_X_MIN),
    configs.TRACKER_SUBWINDOWING_Y_MIN: ModelToReg(registers.GENERAL1_SUB_WINDOWING_Y_MIN),
    configs.TRACKER_SUBWINDOWING_X_MAX: ModelToReg(registers.GENERAL1_SUB_WINDOWING_X_MAX),
    configs.TRACKER_SUBWINDOWING_Y_MAX: ModelToReg(registers.GENERAL1_SUB_WINDOWING_Y_MAX),
    configs.TRACKER_EYE_MODEL_POS_X: ModelToReg(registers.GENERAL1_MODEL_EYE_POSITION_X),
    configs.TRACKER_EYE_MODEL_POS_Y: ModelToReg(registers.GENERAL1_MODEL_EYE_POSITION_Y),
    configs.TRACKER_EYE_MODEL_POS_Z: ModelToReg(registers.GENERAL1_MODEL_EYE_POSITION_Z),
    configs.TRACKER_OPERATIONAL_XPHASE: ModelToReg(registers.GENERAL1_OPERATIONAL_X_PHASE),
    configs.TRACKER_OPERATIONAL_YPHASE: ModelToReg(registers.GENERAL1_OPERATIONAL_Y_PHASE),
    configs.TRACKER_METRICS_LIFETIME_RUNNING_COUNTER: ModelToReg(registers.GENERAL1_LIFETIME_COUNTER_RUNNING),
    configs.TRACKER_SPECS_MAX_LASER_CURRENT: ModelToReg(registers.SPEC_MAX_VCSEL_CURRENT),
    configs.TRACKER_SPECS_XMIN: ModelToReg(registers.SPEC_X_MIN),
    configs.TRACKER_SPECS_XMAX: ModelToReg(registers.SPEC_X_MAX),
    configs.TRACKER_SPECS_YMIN: ModelToReg(registers.SPEC_Y_MIN),
    configs.TRACKER_SPECS_YMAX: ModelToReg(registers.SPEC_Y_MAX),
    configs.TRACKER_ANALOG_SAMPLE_PHASE: ModelToReg(registers.ANALOGLISSAJOUS_SAMPLE_PHASE),
    (configs.PD_ENABLE, 'pd'): PdEnable(configs.PD_ENABLE, registers.GENERAL1_PD_ENABLE),
    (configs.PD_GAIN, 'pd'): PdGain(),
    (configs.PD_GAINBOOST, 'pd'): PdBitFields(configs.PD_GAINBOOST, registers.GENERAL1_PD_GAIN_BOOST),
    (configs.PD_ENABLE, 'pupilpd'): PupilPdEnable(configs.PD_ENABLE, registers.GENERAL1_PUPILPD_ENABLE),
    (configs.PD_GAIN, 'pupilpd'): PupilPdGain(configs.PD_GAIN),
    (configs.PD_GAINBOOST, 'pupilpd'): PupilPdGain(configs.PD_GAINBOOST),
    (configs.PD_GLINTENABLE, 'detector'): DetectorEnable(configs.PD_GLINTENABLE, registers.GENERAL1_PD_ENABLE),
    (configs.PD_PUPILENABLE, 'detector'): DetectorEnable(configs.PD_PUPILENABLE, registers.GENERAL1_PUPILPD_ENABLE),
    (configs.PD_COMMONGAIN, 'detector'): SharedPdGain(configs.PD_COMMONGAIN),
    (configs.PD_GLINTGAIN, 'detector'): SharedPdGain(configs.PD_GLINTGAIN),
    (configs.PD_PUPILGAIN, 'detector'): SharedPdGain(configs.PD_PUPILGAIN),
    (configs.PD_DETECTORTYPE, 'detector'): DetectorType(registers.SPEC_PD_TYPE),
    configs.AUTOTUNE_XRANGE_MIN: ModelToReg(registers.AUTOTUNE_X_MIN),
    configs.AUTOTUNE_XRANGE_MAX: ModelToReg(registers.AUTOTUNE_X_MAX),
    configs.AUTOTUNE_YRANGE_MIN: ModelToReg(registers.AUTOTUNE_Y_MIN),
    configs.AUTOTUNE_YRANGE_MAX: ModelToReg(registers.AUTOTUNE_Y_MAX),
    configs.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_X_MIN: ModelToReg(registers.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_X_MIN),
    configs.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_X_MAX: ModelToReg(registers.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_X_MAX),
    configs.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_Y_MIN: ModelToReg(registers.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_Y_MIN),
    configs.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_Y_MAX: ModelToReg(registers.AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_Y_MAX),
    configs.AUTOTUNE_NOMINAL_SUBWINDOW_X_MIN: ModelToReg(registers.AUTOTUNE_NOMINAL_SUBWINDOW_X_MIN),
    configs.AUTOTUNE_NOMINAL_SUBWINDOW_X_MAX: ModelToReg(registers.AUTOTUNE_NOMINAL_SUBWINDOW_X_MAX),
    configs.AUTOTUNE_NOMINAL_SUBWINDOW_Y_MIN: ModelToReg(registers.AUTOTUNE_NOMINAL_SUBWINDOW_Y_MIN),
    configs.AUTOTUNE_NOMINAL_SUBWINDOW_Y_MAX: ModelToReg(registers.AUTOTUNE_NOMINAL_SUBWINDOW_Y_MAX),
    configs.AUTOTUNE_ENABLEDIAG: AutotuneControl(),
    configs.AUTOTUNE_ALGORITHM: AutotuneControl(),
    configs.AUTOTUNE_ALGORITHM_STEP1: AutotuneComponentAlgorithm(),
    configs.AUTOTUNE_ALGORITHM_STEP2: AutotuneComponentAlgorithm(),
    configs.AUTOTUNE_LARGE_MEGALISA_XPHASE: ModelToReg(registers.AUTOTUNE_LARGE_MEGALISA_XPHASE),
    configs.AUTOTUNE_LARGE_MEGALISA_YPHASE: ModelToReg(registers.AUTOTUNE_LARGE_MEGALISA_YPHASE),
    configs.AUTOTUNE_NOMINAL_X_MIN: ModelToReg(registers.AUTOTUNE_NOMINAL_X_MIN),
    configs.AUTOTUNE_NOMINAL_X_MAX: ModelToReg(registers.AUTOTUNE_NOMINAL_X_MAX),
    configs.AUTOTUNE_NOMINAL_Y_MIN: ModelToReg(registers.AUTOTUNE_NOMINAL_Y_MIN),
    configs.AUTOTUNE_NOMINAL_Y_MAX: ModelToReg(registers.AUTOTUNE_NOMINAL_Y_MAX),
    configs.BLOB_SPEC_REV_AUTOTUNE: ModelToSpecBlob(BlobType.AUTOTUNE),
    configs.BLOB_SPEC_REV_DYNAMIC_FUSION: ModelToSpecBlob(BlobType.DYNAMIC_FUSION),
    configs.BLOB_SPEC_REV_MODEL_ET: ModelToSpecBlob(BlobType.MODEL_ET),
    configs.BLOB_SPEC_REV_MODEL_PRIORS: ModelToSpecBlob(BlobType.MODEL_PRIORS),
    configs.BLOB_SPEC_REV_GEOMETRY: ModelToSpecBlob(BlobType.GEOMETRY),
    configs.BLOB_TUNING_MULTIGLINT: ModelToMultiglintBlob(BlobType.MULTIGLINT),
    configs.BLOB_TUNING_MODULE_CAL: ModelToBlob(BlobType.MODULE_CAL),
    configs.BLOB_TUNING_AUTOTUNE_MULTIGLINT: ModelToMultiglintBlob(BlobType.AUTOTUNE_MULTIGLINT),
    configs.BLOB_USER_CALIBRATION: ModelToCalibrationBlob(BlobType.CALIBRATION),
    configs.ANALOGLISSAJOUS_CAPTURE_TIME: ModelToMultiReg(registers.ANALOGLISSAJOUS_CAPTURE_TIME),
    configs.ANALOGLISSAJOUS_SEGMENT_COUNT: ModelToMultiReg(registers.ANALOGLISSAJOUS_SEGMENT_COUNT),
    configs.ANALOGLISSAJOUS_SAMPLE_COUNT: ModelToMultiReg(registers.ANALOGLISSAJOUS_SAMPLE_COUNT),
    configs.ANALOGLISSAJOUS_SAMPLE_RATE: ModelToMultiReg(registers.ANALOGLISSAJOUS_SAMPLE_RATE),
    configs.ANALOGLISSAJOUS_IMAGE_WIDTH: ModelToMultiReg(registers.ANALOGLISSAJOUS_IMAGE_WIDTH),
    configs.ANALOGLISSAJOUS_IMAGE_CORRECTION_TYPE: ModelToMultiReg(registers.ANALOGLISSAJOUS_IMAGE_CORRECTION_TYPE),
    configs.ANALOGLISSAJOUS_IMAGE_GENERATION_ALGORITHM: ModelToMultiReg(registers.ANALOGLISSAJOUS_IMAGE_GENERATION_ALGORITHM),
    configs.ANALOGLISSAJOUS_STARTUP_PERIOD: ModelToMultiReg(registers.ANALOGLISSAJOUS_STARTUP_PERIOD),
    configs.ANALOGLISSAJOUS_NEGATIVE_SLEW: ModelToMultiReg(registers.ANALOGLISSAJOUS_NEGATIVE_SLEW),
    configs.ANALOGLISSAJOUS_SATURATION_LIMIT_HIGH: ModelToMultiReg(registers.ANALOGLISSAJOUS_SATURATION_LIMIT_HIGH),
    configs.ANALOGLISSAJOUS_SATURATION_LIMIT_LOW: ModelToMultiReg(registers.ANALOGLISSAJOUS_SATURATION_LIMIT_LOW),
    configs.ANALOGLISSAJOUS_SEGMENT_FORWARDING: ModelToMultiReg(registers.ANALOGLISSAJOUS_SEGMENT_FORWARDING),
    configs.ANALOGLISSAJOUS_IMAGE_POSTPROCESSING: ModelToMultiReg(registers.ANALOGLISSAJOUS_IMAGE_POSTPROCESSING),
}


def get_handler(config_key: str) -> ConfigHandlerInterface:
    '''Given a config_key string, returns the appropriate handler'''
    return _CONFIG_HANDLER_MAP[config_key]
