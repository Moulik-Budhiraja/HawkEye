'''
Automatically generated using:
python register_generator.py --format PYTHON_REGS --output adhawkapi/registers.py
'''
import enum


# Banks
BANK_MEGALISA = 0x5
BANK_AUTOTUNE = 0x7
BANK_ANALOG = 0xB
BANK_ANALOGLISSAJOUS = 0xC
BANK_DEBUG = 0xFB
BANK_ISP = 0xFC
BANK_GENERAL1 = 0xFD
BANK_SPEC = 0xFE
BANK_GENERAL2 = 0xFF

# Registers

# Megalisa Registers
MEGALISA_Y_MAX = ('megalisa', 'y_max')
MEGALISA_Y_MIN = ('megalisa', 'y_min')
MEGALISA_X_MAX = ('megalisa', 'x_max')
MEGALISA_X_MIN = ('megalisa', 'x_min')
MEGALISA_STREAM_ENABLE = ('megalisa', 'stream_enable')

# Autotune Registers
AUTOTUNE_X_MIN = ('autotune', 'x_min')
AUTOTUNE_X_MAX = ('autotune', 'x_max')
AUTOTUNE_Y_MIN = ('autotune', 'y_min')
AUTOTUNE_Y_MAX = ('autotune', 'y_max')
AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_X_MIN = ('autotune', 'large_megalisa_subwindow_x_min')
AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_X_MAX = ('autotune', 'large_megalisa_subwindow_x_max')
AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_Y_MIN = ('autotune', 'large_megalisa_subwindow_y_min')
AUTOTUNE_LARGE_MEGALISA_SUBWINDOW_Y_MAX = ('autotune', 'large_megalisa_subwindow_y_max')
AUTOTUNE_NOMINAL_SUBWINDOW_X_MIN = ('autotune', 'nominal_subwindow_x_min')
AUTOTUNE_NOMINAL_SUBWINDOW_X_MAX = ('autotune', 'nominal_subwindow_x_max')
AUTOTUNE_NOMINAL_SUBWINDOW_Y_MIN = ('autotune', 'nominal_subwindow_y_min')
AUTOTUNE_NOMINAL_SUBWINDOW_Y_MAX = ('autotune', 'nominal_subwindow_y_max')
AUTOTUNE_CONTROL = ('autotune', 'control')
AUTOTUNE_ALGORITHM_SELECTION = ('autotune', 'algorithm_selection')
AUTOTUNE_LARGE_MEGALISA_XPHASE = ('autotune', 'large_megalisa_xphase')
AUTOTUNE_LARGE_MEGALISA_YPHASE = ('autotune', 'large_megalisa_yphase')
AUTOTUNE_NOMINAL_X_MIN = ('autotune', 'nominal_x_min')
AUTOTUNE_NOMINAL_X_MAX = ('autotune', 'nominal_x_max')
AUTOTUNE_NOMINAL_Y_MIN = ('autotune', 'nominal_y_min')
AUTOTUNE_NOMINAL_Y_MAX = ('autotune', 'nominal_y_max')

# Analog Registers
ANALOG_CHANNEL_SELECTION = ('analog', 'channel_selection')
ANALOG_SAMPLE_COUNT = ('analog', 'sample_count')
ANALOG_SETTLING_TIME = ('analog', 'settling_time')
ANALOG_ACTUATOR_BIAS_X = ('analog', 'actuator_bias_x')  # Deprecated
ANALOG_VCSEL_BIAS_CURRENT = ('analog', 'vcsel_bias_current')
ANALOG_ACTUATOR_BIAS_Y = ('analog', 'actuator_bias_y')  # Deprecated
ANALOG_HIGH_THRESHOLD_TRIGGER = ('analog', 'high_threshold_trigger')
ANALOG_LOW_THRESHOLD_TRIGGER = ('analog', 'low_threshold_trigger')
ANALOG_OBSERVER_WINDOW_SIZE = ('analog', 'observer_window_size')
ANALOG_MEGASAMPLE_ENABLE = ('analog', 'megasample_enable')
ANALOG_LISSAJOUS_ENABLE = ('analog', 'lissajous_enable')  # Deprecated
ANALOG_Y_MAX = ('analog', 'y_max')
ANALOG_Y_MIN = ('analog', 'y_min')
ANALOG_X_MAX = ('analog', 'x_max')
ANALOG_X_MIN = ('analog', 'x_min')
ANALOG_HIGH_THRESHOLD_TRIGGER_2 = ('analog', 'high_threshold_trigger_2')
ANALOG_LOW_THRESHOLD_TRIGGER_2 = ('analog', 'low_threshold_trigger_2')
ANALOG_SAMPLE_RATE = ('analog', 'sample_rate')
ANALOG_SAMPLE_RESOLUTION = ('analog', 'sample_resolution')
ANALOG_SAMPLE_FREQUENCY = ('analog', 'sample_frequency')

# Analog Lissajous Registers
ANALOGLISSAJOUS_CAPTURE_TIME = ('analoglissajous', 'capture_time')
ANALOGLISSAJOUS_SEGMENT_COUNT = ('analoglissajous', 'segment_count')
ANALOGLISSAJOUS_SAMPLE_COUNT = ('analoglissajous', 'sample_count')
ANALOGLISSAJOUS_SAMPLE_RATE = ('analoglissajous', 'sample_rate')
ANALOGLISSAJOUS_Y_MAX = ('analoglissajous', 'y_max')
ANALOGLISSAJOUS_Y_MIN = ('analoglissajous', 'y_min')
ANALOGLISSAJOUS_X_MAX = ('analoglissajous', 'x_max')
ANALOGLISSAJOUS_X_MIN = ('analoglissajous', 'x_min')
ANALOGLISSAJOUS_SAMPLE_PHASE = ('analoglissajous', 'sample_phase')
ANALOGLISSAJOUS_IMAGE_WIDTH = ('analoglissajous', 'image_width')
ANALOGLISSAJOUS_IMAGE_CORRECTION_TYPE = ('analoglissajous', 'image_correction_type')
ANALOGLISSAJOUS_IMAGE_GENERATION_ALGORITHM = (
    'analoglissajous',
    'image_generation_algorithm',
)
ANALOGLISSAJOUS_STARTUP_PERIOD = ('analoglissajous', 'startup_period')
ANALOGLISSAJOUS_NEGATIVE_SLEW = ('analoglissajous', 'negative_slew')
ANALOGLISSAJOUS_SATURATION_LIMIT_HIGH = ('analoglissajous', 'saturation_limit_high')
ANALOGLISSAJOUS_SATURATION_LIMIT_LOW = ('analoglissajous', 'saturation_limit_low')
ANALOGLISSAJOUS_SEGMENT_FORWARDING = ('analoglissajous', 'segment_forwarding')
ANALOGLISSAJOUS_IMAGE_POSTPROCESSING = ('analoglissajous', 'image_postprocessing')

# DEBUG Registers
DEBUG_CONFIG_GPIO = ('debug', 'config_gpio')
DEBUG_WRITE_GPIO = ('debug', 'write_gpio')
DEBUG_READ_GPIO = ('debug', 'read_gpio')
DEBUG_SET_PWM = ('debug', 'set_pwm')
DEBUG_SET_DC_ENABLE = ('debug', 'set_dc_enable')

# ISP Registers
ISP_PROGRAMMING_MODE = ('isp', 'programming_mode')
ISP_VERSION = ('isp', 'version')
ISP_BOARD_TYPE = ('isp', 'board_type')
ISP_CHECKSUM = ('isp', 'checksum')
ISP_INACTIVE_IMAGE = ('isp', 'inactive_image')
ISP_STABLE_IMAGE = ('isp', 'stable_image')
ISP_BOOTLOADER_VERSION = ('isp', 'bootloader_version')
ISP_FLUSH_BUFFER = ('isp', 'flush_buffer')
ISP_READ_ERROR = ('isp', 'read_error')
ISP_TARGET_ISP_VERSION = ('isp', 'target_isp_version')
ISP_TARGET_BUILD_ID = ('isp', 'target_build_id')
ISP_STATUS = ('isp', 'status')
ISP_SAFE_MODE = ('isp', 'safe_mode')
ISP_RESET_MCU = ('isp', 'reset_mcu')

# General 1 Registers
GENERAL1_API_VERSION = ('general1', 'api_version')
GENERAL1_MULTI_DEVICES = ('general1', 'multi_devices')
GENERAL1_LASER_CURRENT = ('general1', 'laser_current')
GENERAL1_RAW_ADC = ('general1', 'raw_adc')
GENERAL1_CONFIGURED_X_FREQUENCY = ('general1', 'configured_x_frequency')
GENERAL1_MODULATION_FREQUENCY = ('general1', 'modulation_frequency')
GENERAL1_MODULATION_DUTY_CYCLE = ('general1', 'modulation_duty_cycle')
GENERAL1_CONFIGURED_Y_FREQUENCY = ('general1', 'configured_y_frequency')
GENERAL1_PD_CONFIG_STATUS = ('general1', 'pd_config_status')
GENERAL1_X_PHASE = ('general1', 'x_phase')
GENERAL1_Y_PHASE = ('general1', 'y_phase')
GENERAL1_PD_ENABLE = ('general1', 'pd_enable')
GENERAL1_PD0_GAIN = ('general1', 'pd0_gain')
GENERAL1_PD1_GAIN = ('general1', 'pd1_gain')
GENERAL1_PD2_GAIN = ('general1', 'pd2_gain')
GENERAL1_PD3_GAIN = ('general1', 'pd3_gain')
GENERAL1_PD4_GAIN = ('general1', 'pd4_gain')
GENERAL1_PD5_GAIN = ('general1', 'pd5_gain')
GENERAL1_GLINT_PW_FILTER_MAX_THRESHOLD = ('general1', 'glint_pw_filter_max_threshold')
GENERAL1_GLINT_PW_FILTER_MIN_THRESHOLD = ('general1', 'glint_pw_filter_min_threshold')
GENERAL1_PD_GAIN_BOOST = ('general1', 'pd_gain_boost')
GENERAL1_PUPIL_OFFSET = ('general1', 'pupil_offset')
GENERAL1_PUPIL_PW_FILTER_MAX_THRESHOLD = ('general1', 'pupil_pw_filter_max_threshold')
GENERAL1_PUPIL_PW_FILTER_MIN_THRESHOLD = ('general1', 'pupil_pw_filter_min_threshold')
GENERAL1_OPERATIONAL_X_FREQUENCY = ('general1', 'operational_x_frequency')
GENERAL1_OPERATIONAL_Y_FREQUENCY = ('general1', 'operational_y_frequency')
GENERAL1_PUPILPD_ENABLE = ('general1', 'pupilpd_enable')
GENERAL1_PUPILPD0_GAIN = ('general1', 'pupilpd0_gain')
GENERAL1_PUPILPD1_GAIN = ('general1', 'pupilpd1_gain')
GENERAL1_DEAD_TIME_X = ('general1', 'dead_time_x')
GENERAL1_DEAD_TIME_Y = ('general1', 'dead_time_y')
GENERAL1_DEAD_TIME_MODE = ('general1', 'dead_time_mode')
GENERAL1_OPERATIONAL_X_PHASE = ('general1', 'operational_x_phase')
GENERAL1_OPERATIONAL_Y_PHASE = ('general1', 'operational_y_phase')
GENERAL1_GLINT_AND_PUPIL_PD0_GAINS = ('general1', 'glint_and_pupil_pd0_gains')
GENERAL1_GLINT_AND_PUPIL_PD1_GAINS = ('general1', 'glint_and_pupil_pd1_gains')
GENERAL1_GLINT_AND_PUPIL_PD2_GAINS = ('general1', 'glint_and_pupil_pd2_gains')
GENERAL1_PD_STATE = ('general1', 'pd_state')
GENERAL1_MCU_CLOCK = ('general1', 'mcu_clock')
GENERAL1_ALG_PIPELINE = ('general1', 'alg_pipeline')
GENERAL1_USB_HUB_MODE = ('general1', 'usb_hub_mode')
GENERAL1_LIFETIME_COUNTER = ('general1', 'lifetime_counter')
GENERAL1_LIFETIME_COUNTER_RUNNING = ('general1', 'lifetime_counter_running')
GENERAL1_PD0_CONTROL = ('general1', 'pd0_control')
GENERAL1_COMPONENT_OFFSET_X = ('general1', 'component_offset_x')
GENERAL1_COMPONENT_OFFSET_Y = ('general1', 'component_offset_y')
GENERAL1_COMPONENT_OFFSET_Z = ('general1', 'component_offset_z')
GENERAL1_SUB_WINDOWING_ENABLE = ('general1', 'sub_windowing_enable')
GENERAL1_SUB_WINDOWING_X_MIN = ('general1', 'sub_windowing_x_min')
GENERAL1_SUB_WINDOWING_Y_MIN = ('general1', 'sub_windowing_y_min')
GENERAL1_REALTIME_Z_ENABLE = ('general1', 'realtime_z_enable')
GENERAL1_MODEL_EYE_POSITION_X = ('general1', 'model_eye_position_x')
GENERAL1_MODEL_EYE_POSITION_Y = ('general1', 'model_eye_position_y')
GENERAL1_MODEL_EYE_POSITION_Z = ('general1', 'model_eye_position_z')
GENERAL1_SUB_WINDOWING_X_MAX = ('general1', 'sub_windowing_x_max')
GENERAL1_SUB_WINDOWING_Y_MAX = ('general1', 'sub_windowing_y_max')

# Spec Registers
SPEC_PRODUCT_CATEGORY = ('spec', 'product_category')
SPEC_CAPABILITY = ('spec', 'capability')
SPEC_CAMERA = ('spec', 'camera')
SPEC_DEVICE_TUNE_VERSION = ('spec', 'device_tune_version')
SPEC_DEVICE_TUNE_DATE = ('spec', 'device_tune_date')
SPEC_BUILD = ('spec', 'build')
SPEC_SERIAL_NUMBER = ('spec', 'serial_number')
SPEC_X_MAX = ('spec', 'x_max')
SPEC_X_MIN = ('spec', 'x_min')
SPEC_Y_MAX = ('spec', 'y_max')
SPEC_Y_MIN = ('spec', 'y_min')
SPEC_MAX_VCSEL_CURRENT = ('spec', 'max_vcsel_current')
SPEC_MAX_DUTY_CYCLE = ('spec', 'max_duty_cycle')
SPEC_SCANNER_ORIENTATION = ('spec', 'scanner_orientation')
SPEC_PRODUCT_ID = ('spec', 'product_id')
SPEC_SCANNER_FAULT_REACTION = ('spec', 'scanner_fault_reaction')
SPEC_PD_ORDER = ('spec', 'pd_order')
SPEC_PD_TYPE = ('spec', 'pd_type')
SPEC_RES_FREQ_X = ('spec', 'res_freq_x')
SPEC_RES_FREQ_Y = ('spec', 'res_freq_y')
SPEC_OCULAR_MODE = ('spec', 'ocular_mode')
SPEC_X1_RESISTANCE_CAL_MULTIPLIER = ('spec', 'x1_resistance_cal_multiplier')
SPEC_X1_RESISTANCE_CAL_OFFSET = ('spec', 'x1_resistance_cal_offset')
SPEC_X2_RESISTANCE_CAL_MULTIPLIER = ('spec', 'x2_resistance_cal_multiplier')
SPEC_X2_RESISTANCE_CAL_OFFSET = ('spec', 'x2_resistance_cal_offset')
SPEC_Y1_RESISTANCE_CAL_MULTIPLIER = ('spec', 'y1_resistance_cal_multiplier')
SPEC_Y1_RESISTANCE_CAL_OFFSET = ('spec', 'y1_resistance_cal_offset')
SPEC_Y2_RESISTANCE_CAL_MULTIPLIER = ('spec', 'y2_resistance_cal_multiplier')
SPEC_Y2_RESISTANCE_CAL_OFFSET = ('spec', 'y2_resistance_cal_offset')
SPEC_VCSEL_FORWARD_VOLTAGE_CAL_MULTIPLIER = (
    'spec',
    'vcsel_forward_voltage_cal_multiplier',
)
SPEC_VCSEL_FORWARD_VOLTAGE_CAL_OFFSET = ('spec', 'vcsel_forward_voltage_cal_offset')
SPEC_RESONANCE_CAL_MULTIPLIER = ('spec', 'resonance_cal_multiplier')
SPEC_RESONANCE_CAL_OFFSET = ('spec', 'resonance_cal_offset')
SPEC_OPTICAL_POWER_MAIN_CAL_MULTIPLIER = ('spec', 'optical_power_main_cal_multiplier')
SPEC_OPTICAL_POWER_MAIN_CAL_OFFSET = ('spec', 'optical_power_main_cal_offset')
SPEC_OPTICAL_POWER_BG_CAL_MULTIPLIER = ('spec', 'optical_power_bg_cal_multiplier')
SPEC_OPTICAL_POWER_BG_CAL_OFFSET = ('spec', 'optical_power_bg_cal_offset')
SPEC_VCSEL_DRIVE_CAL_MULTIPLIER = ('spec', 'vcsel_drive_cal_multiplier')
SPEC_VCSEL_DRIVE_CAL_OFFSET = ('spec', 'vcsel_drive_cal_offset')
SPEC_ADC_REFERENCE_VOLTAGE = ('spec', 'adc_reference_voltage')
SPEC_VCSEL_FORWARD_VOLTAGE_GAIN = ('spec', 'vcsel_forward_voltage_gain')
SPEC_BOARD_SERIAL_NUMBER = ('spec', 'board_serial_number')
SPEC_VCSEL_SAFETY_THRESHOLD = ('spec', 'vcsel_safety_threshold')

# General 2 Registers
GENERAL2_RESET = ('general2', 'reset')
GENERAL2_START = ('general2', 'start')
GENERAL2_STOP = ('general2', 'stop')
GENERAL2_WIPE = ('general2', 'wipe')
GENERAL2_FLUSH = ('general2', 'flush')
GENERAL2_RELOAD = ('general2', 'reload')
GENERAL2_TRACKER_STATUS = ('general2', 'tracker_status')
GENERAL2_FLASH_WRITE_COUNT = ('general2', 'flash_write_count')
GENERAL2_FLASH_ERASE_COUNT = ('general2', 'flash_erase_count')
GENERAL2_LASER_STATUS = ('general2', 'laser_status')
GENERAL2_ERASE_FILE = ('general2', 'erase_file')
GENERAL2_REBUILD_RECORDS_TABLE = ('general2', 'rebuild_records_table')
GENERAL2_VCSEL_SELF_TEST = ('general2', 'vcsel_self_test')
GENERAL2_TRIGGER_SAFEMODE = ('general2', 'trigger_safemode')


class AutotuneControlAlgorithm(enum.IntEnum):
    '''Available choices for the register'''

    ANALOG = 0
    DIGITAL_BOX_SWEEP = 1
    DIGITAL_LINE_SWEEP = 2
    DIGITAL_LINE_SWEEP_V2 = 3
    BOX_SIZING = 4


class AnalogChannelSelection(enum.IntEnum):
    '''Available choices for the register'''

    RINGDOWN = 0
    X1_RESISTANCE = 1
    X2_RESISTANCE = 2
    Y1_RESISTANCE = 3
    Y2_RESISTANCE = 4
    VCSEL_FORWARDVOLTAGE = 5
    SPARE_1 = 6
    SPARE_2 = 7
    SPARE_1_AND_SPARE_2 = 8


class AnaloglissajousImageCorrectionType(enum.IntEnum):
    '''Available choices for the register'''

    NONE = 0
    WRAP = 1
    COSINE = 2


class AnaloglissajousImageGenerationAlgorithm(enum.IntEnum):
    '''Available choices for the register'''

    ONE_PIXEL_AVERAGING = 0
    FOUR_PIXEL_AVERAGING = 1


class AnaloglissajousImagePostprocessing(enum.IntEnum):
    '''Available choices for the register'''

    NONE = 0
    AVERAGE = 1
    MEDIAN = 2


class DebugConfigGpioMode(enum.IntEnum):
    '''Available choices for the register'''

    INPUT = 0
    OUTPUT = 1


class DebugWriteGpioLevel(enum.IntEnum):
    '''Available choices for the register'''

    LOW = 0
    HIGH = 1


class DebugSetPwmAxis(enum.IntEnum):
    '''Available choices for the register'''

    X1_AXIS = 0
    X2_AXIS = 1
    Y1_AXIS = 2
    Y2_AXIS = 3


class IspBoardType(enum.IntEnum):
    '''Available choices for the register'''

    DEVBOARDV1 = 0
    V3DAC = 1
    V3PWM = 2
    V4DAC = 3
    DEVBOARDV2 = 4
    DIGIBRD = 5
    DEVBOARDV3 = 6
    SPIADAPTER = 7
    COMBRD = 8
    VIBRANIUMCOMBRD = 9
    HYBRIDV1 = 10
    VIBRANIUM = 11
    STDEVSHIELD = 12
    COPPERHUB = 13
    COPPERFACEPLATE = 14
    SAMSUNGHUB = 15
    COPPEREYETUBE = 16
    SAMSUNGV1 = 17
    EVK3 = 18
    EVK3HUB = 19
    BINOCULARHYBRIDV1 = 20
    BINOCULARHYBRIDHUBV1 = 21
    COPPER427HUB = 22
    EVK3_1 = 23
    SAMSUNGV2 = 24
    FPGADEVBOARDV1 = 25
    SPIADAPTERV2 = 26
    PCCREYETRACKERV1 = 27
    PCCRPUPILV1 = 28
    PCCRHUBV1 = 29
    BINOCULARHYBRIDV2 = 30
    BINOCULARHYBRIDHUBV2 = 31
    STM32SPIADAPTER = 32
    SINGLEMCUV1 = 33
    DEVBOARDV4 = 35
    SINGLEMCU3PD = 36
    STL5DEVSHIELDV1 = 37
    AHSM3ET = 38
    AHSM3SPIADAPTER = 39
    AHSM3_3PD = 40
    DEVBOARDV4_3PD = 41
    L5_EVK_V1 = 42
    L5_EVK_V1_3PD = 43
    DEVBOARDV5 = 44
    ZAPATA_V1 = 45
    EVK4 = 46
    DEVBOARDV5_ALC = 48
    L5_EVK_SR21 = 49
    AMBON_SHIELD = 50
    L5_EVK_SR21_IRIS = 51
    DEVBOARDV6 = 52
    INT_V1 = 53
    INT_V1_IRIS = 54
    MERLIN22 = 55
    LP_INT_V2 = 56
    EVK4_V2 = 57
    MERLIN2 = 58
    HONEYCOMB_V1 = 59
    EVK4_WIRELESS = 60
    VIRTUALCLIENT = 4294967295


class General1PdConfigStatus(enum.IntEnum):
    '''Available choices for the register'''

    PD0 = 0
    PD1 = 1
    PD2 = 2
    PD3 = 3
    PD4 = 4
    PD5 = 5
    PUPILPD0 = 6
    PUPILPD1 = 7


class General1PdEnable(enum.IntEnum):
    '''Available choices for the register'''

    PD0 = 0
    PD1 = 1
    PD2 = 2
    PD3 = 3
    PD4 = 4
    PD5 = 5


class General1PdGainBoost(enum.IntEnum):
    '''Available choices for the register'''

    PD0 = 0
    PD1 = 1
    PD2 = 2
    PD3 = 3
    PD4 = 4
    PD5 = 5


class General1PupilpdEnable(enum.IntEnum):
    '''Available choices for the register'''

    PUPILPD0 = 0
    PUPILPD1 = 1
    PUPILPD2 = 2


class General1DeadTimeMode(enum.IntEnum):
    '''Available choices for the register'''

    NO_DEAD_TIME = 0
    CONSTANT_TIME_HALF_CYCLE_MAX = 1
    CONSTANT_TIME_FULL_CYCLE_MAX = 2


class General1PdState(enum.IntEnum):
    '''Available choices for the register'''

    PD0_E = 0
    PD1_E = 1
    PD2_E = 2
    PD3_E = 3
    PD4_E = 4
    PD5_E = 5
    PUPILPD0_E = 6
    PUPILPD1_E = 7
    PD0_D = 16
    PD1_D = 17
    PD2_D = 18
    PD3_D = 19
    PD4_D = 20
    PD5_D = 21
    PUPILPD0_D = 22
    PUPILPD1_D = 23


class General1AlgPipeline(enum.IntEnum):
    '''Available choices for the register'''

    PUPIL = 0
    RESEARCH = 1
    SLIP_TOLERANT = 2


class General1UsbHubMode(enum.IntEnum):
    '''Available choices for the register'''

    HUB_MODE = 0
    BYPASS_MODE = 1


class SpecProductCategory(enum.IntEnum):
    '''Available choices for the register'''

    OTHER = 0
    HMD = 1
    SINGLE_TRACKER = 5


class SpecCapability(enum.IntEnum):
    '''Available choices for the register'''

    EYE_TRACKER = 0
    RIGHT_EYE = 1
    LEFT_EYE = 2
    EMBEDDED_FRONTEND = 9
    EMBEDDED_ET = 11
    PUPIL_TRACKER = 12
    SHARED_DETECTOR_CAPABILITY = 15
    SINGLE_TRACKER_OPTIMIZATION = 16
    DIRECT_DETECTOR_CONTROL = 17
    LASER_SAFETY_BYPASS = 18
    FUNDAMENTAL_DRIVE = 19
    LOW_POWER_TRACKER = 20
    FORCE_AC_DRIVE = 21


class SpecCamera(enum.IntEnum):
    '''Available choices for the register'''

    NOT_AVAILABLE = 0
    SMI = 1
    SMI_INV = 2
    QUANTA = 3
    QUANTA_INV = 4
    QUANTA2 = 5
    QUANTA2_INV = 6
    SINCERE = 7


class SpecScannerOrientation(enum.IntEnum):
    '''Available choices for the register'''

    SWAPPEDXY = 0
    FLIPPEDX = 1
    FLIPPEDY = 2


class SpecProductId(enum.IntEnum):
    '''Available choices for the register'''

    UNKNOWN = 0
    EXPERIMENTAL = 1
    AHSM = 2
    CUOAP = 3
    EVK3P1 = 4
    EVK3P2 = 5
    EVK3P4 = 6
    GARC5 = 7
    GTK = 8
    AHSM2 = 9
    EVK3P5 = 10
    SWALLOW = 11
    AHSM3A1 = 12
    AHSM3A2 = 13
    SPARROW = 14
    EVK3P6 = 15
    EVK4P0 = 16
    GANNET = 17
    SPARROWG3 = 18
    EVK3P6G3 = 19
    AHSM3J = 20
    MFGBENCH = 21
    MFGBENCHG3 = 22
    AHSM3A1MOCKUP = 23
    AHSM3A2MOCKUP = 24
    AHSM3K = 25
    EVK5P0 = 26
    AHSM3KL = 27
    ZAPATA = 28
    HWBENCH = 29
    HOBBY = 30
    EVK4P1 = 31
    DARTER = 32
    SR21A = 33
    SR21B = 34
    AMBON_SHIELD = 35
    SWALLOW21 = 36
    SR21C = 37
    FALCON21_V5 = 38
    ALBATROSS21 = 39
    FALCON21 = 40
    MINDLINK_2P5MM = 41
    MFGBENCH_LONGEVITY = 42
    MERLIN22 = 43
    FALCON21_3GPD = 44
    DARTERFOLDED3P2 = 46
    FALCON2 = 47
    MERLIN2 = 48
    ALBATROSS2 = 49
    MFGBENCH_LONGEVITY_2P5MM = 50
    EVK3P6G3_INT = 51
    EVK4P1_TEST = 52
    FALCON2_LP = 53
    MERLIN3 = 54
    MERLIN2_INT_V1 = 55
    DODO = 56
    EVK4_WIRELESS = 57
    MFGBENCH_LONGEVITY_2P5MM_8P80_M11P65 = 58


class SpecOcularMode(enum.IntEnum):
    '''Available choices for the register'''

    RIGHT = 1
    LEFT = 2
    BINOCULAR = 3


class General2TrackerStatus(enum.IntEnum):
    '''Available choices for the register'''

    LASER_SELF_TEST_FAULT = 0
    LASER_OVERCURRENT_FAULT = 1
    LASER_MONITOR_FAULT = 2
    POWER_MODE_WATCHDOG = 3
    FILE_CORRUPTION_FAULT = 4


class General2LaserStatus(enum.IntEnum):
    '''Available choices for the register'''

    LASER_SELF_TEST_WARNING = 0
    LASER_OVERCURRENT_WARNING = 1
    LASER_MONITOR_WARNING = 2


class General2EraseFile(enum.IntEnum):
    '''Available choices for the register'''

    SETTINGS_FILE = 0
    BLOB_FILE = 1
    AUTOSAVE_FILE = 2
    FAULT_FILE = 3


class General2VcselSelfTest(enum.IntEnum):
    '''Available choices for the register'''

    LASER_SELF_TEST_PASSED = 0
    LASER_SELF_TEST_NOT_SUPPORTED = 1
    FAULT_ASSERTED_BEFORE_TEST_ERROR = 2
    FAULT_ASSERTION_STEP_ERROR = 3
    FAULT_CLEAR_STEP_ERROR = 4
    RAMP_UP_STEP_ERROR = 5
