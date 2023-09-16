'''This module contains the definitions of AdHawk's eye tracking API'''

import dataclasses
import enum
import typing

from . import error


REQUEST_TIMEOUT = 8  # seconds


class APIRequestError(error.Error):
    '''Exception class indicating public api request failure'''

    def __init__(self, ackcode, msg='API Error'):
        super().__init__(f'{msg}: {errormsg(ackcode)}')
        self.ackcode = ackcode


class AckCodes(enum.IntEnum):
    '''List of acknowledgement payload values'''
    SUCCESS = 0
    FAILURE = 1
    INVALID_ARGUMENT = 2
    TRACKER_NOT_READY = 3
    EYES_NOT_FOUND = 4
    RIGHT_EYE_NOT_FOUND = 5
    LEFT_EYE_NOT_FOUND = 6
    NOT_CALIBRATED = 7
    NOT_SUPPORTED = 8
    SESSION_ALREADY_RUNNING = 9
    NO_CURRENT_SESSION = 10
    REQUEST_TIMEOUT = 11
    UNEXPECTED_RESPONSE = 12
    HARDWARE_FAULT = 13
    CAMERA_FAULT = 14
    BUSY = 15
    COMMUNICATION_ERROR = 16
    DEVICE_CALIBRATION_REQUIRED = 17
    PROCESS_INCOMPLETE = 18
    INACTIVE_INTERFACE = 19
    TRACKER_DISCONNECTED = 20


_ACK_CODE_STRINGS = {
    AckCodes.SUCCESS: '',
    AckCodes.FAILURE: 'Internal failure',
    AckCodes.INVALID_ARGUMENT: 'Invalid argument',
    AckCodes.TRACKER_NOT_READY: 'Trackers not ready',
    AckCodes.EYES_NOT_FOUND: 'No eyes detected',
    AckCodes.RIGHT_EYE_NOT_FOUND: 'Right eye not detected',
    AckCodes.LEFT_EYE_NOT_FOUND: 'Left eye not detected',
    AckCodes.NOT_CALIBRATED: 'Not calibrated',
    AckCodes.NOT_SUPPORTED: 'Not supported',
    AckCodes.SESSION_ALREADY_RUNNING: 'Data logging session already exists',
    AckCodes.NO_CURRENT_SESSION: 'No data logging session exists to stop',
    AckCodes.REQUEST_TIMEOUT: 'Request has timed out',
    AckCodes.UNEXPECTED_RESPONSE: 'Unexpected response',
    AckCodes.HARDWARE_FAULT: 'Hardware faulted',
    AckCodes.CAMERA_FAULT: 'Camera initialization failed',
    AckCodes.BUSY: 'System is busy',
    AckCodes.COMMUNICATION_ERROR: 'Communication error',
    AckCodes.DEVICE_CALIBRATION_REQUIRED: 'Device calibration is outdated',
    AckCodes.PROCESS_INCOMPLETE: 'Process was aborted or interrupted unexpectedly',
    AckCodes.INACTIVE_INTERFACE: 'Packet received from an inactive interface',
    AckCodes.TRACKER_DISCONNECTED: 'Tracker disconnected'
}


def errormsg(errcode):
    '''Returns the textual description associated with the specified error code'''
    return _ACK_CODE_STRINGS.get(errcode, f'Unknown error code {errcode}')


def check_result(retcode, failure_log):
    '''Checks result of a command and raises an exception in case of failures'''
    if retcode == AckCodes.SUCCESS:
        return
    raise APIRequestError(retcode, failure_log)


class PacketType(enum.IntEnum):
    '''Enum representing set of packet types'''
    # Streams
    EYETRACKING_STREAM = 0x01
    TRACKER_READY = 0x02
    GAZE = 0x03  # deprecated, use `EYETRACKING_STREAM`
    PUPIL_POSITION = 0x04  # deprecated, use `EYETRACKING_STREAM`
    PUPIL_DIAMETER = 0x05  # deprecated, use `EYETRACKING_STREAM`
    PER_EYE_GAZE = 0x06  # deprecated, use `EYETRACKING_STREAM`
    GAZE_IN_IMAGE = 0x07  # deprecated, use `EYETRACKING_STREAM`
    GAZE_IN_SCREEN = 0x08  # deprecated, use `EYETRACKING_STREAM`
    FEATURE_STREAM = 0x09
    CALIBRATION_ERROR = 0x10
    PULSE = 0x11
    GLINT = 0x12  # deprecated, use `FEATURE_STREAM`
    FUSE = 0x13  # deprecated, use `FEATURE_STREAM`
    PUPIL_ELLIPSE = 0x14  # deprecated, use `FEATURE_STREAM`
    PUPIL_CENTER = 0x15  # deprecated, not implemented on embedded
    TRACKER_STATUS = 0x16
    IMU = 0x17
    EVENTS = 0x18
    IMU_ROTATION = 0x19
    IRIS_IMAGE_DATA_STREAM = 0x20
    CONFIG_DUMP = 0x21
    MCU_TEMPERATURE = 0x22

    # Commands
    UDP_CONN = 0xc0
    END_UDP_CONN = 0xc2
    PING = 0xc5

    START_CALIBRATION = 0x81
    STOP_CALIBRATION = 0x82
    ABORT_CALIBRATION = 0x83
    REGISTER_CALIBRATION = 0x84
    TRIGGER_AUTOTUNE = 0x85
    START_VALIDATION = 0x86
    STOP_VALIDATION = 0x87
    REGISTER_VALIDATION = 0x88
    LOG_TIMESTAMPED_ANNOTATION = 0x8d
    RECENTER_CALIBRATION = 0x8f
    TRACKER_STATE = 0x90

    DELETE_BLOB = 0x91
    BLOB_SIZE = 0x92
    BLOB_DATA = 0x93
    LOAD_BLOB = 0x94
    SAVE_BLOB = 0x95

    START_LOG_SESSION = 0x96
    STOP_LOG_SESSION = 0x97
    REQUEST_BACKEND_VERSION = 0x98
    REQUEST_SYSTEM_INFO = 0x99

    PROPERTY_GET = 0x9a
    PROPERTY_SET = 0x9b

    SYSTEM_CONTROL = 0x9c

    IRIS_TRIGGER_CAPTURE = 0x9d
    TRIGGER_CONFIG_DUMP = 0x9e

    PROCEDURE_START = 0xb0
    PROCEDURE_STATUS = 0xb1

    CAMERA_USER_SETTINGS_SET = 0xd0

    START_CAMERA = 0xd2  # deprecated
    STOP_CAMERA = 0xd3  # deprecated
    START_VIDEO_STREAM = 0xd4
    STOP_VIDEO_STREAM = 0xd5
    REGISTER_SCREEN_BOARD = 0xd6
    START_SCREEN_TRACKING = 0xd7
    STOP_SCREEN_TRACKING = 0xd8

    def is_stream(self):
        '''Returns whether the packet is a stream'''
        return self < 0x80

    def header_len(self):
        '''Returns the request header length'''
        if self in (PacketType.PROPERTY_SET, PacketType.PROPERTY_GET,
                    PacketType.PROCEDURE_START, PacketType.PROCEDURE_STATUS):
            return 2
        return 1

    def __repr__(self):
        return f'{str(self.name).lower()} ({hex(self.value)})'


class SystemControlType(enum.IntEnum):
    '''List of supported commands for system control (0x9c)'''
    TRACKING = 1


class StreamControlBit(enum.IntEnum):
    '''Bits that control enabling or disabling a stream'''
    PUPIL_POSITION = 1 << 1
    PUPIL_DIAMETER = 1 << 2
    GAZE = 1 << 3
    PER_EYE_GAZE = 1 << 4
    GAZE_IN_IMAGE = 1 << 5
    GAZE_IN_SCREEN = 1 << 6

    MCU_TEMPERATURE = 1 << 22
    IMU_ROTATION = 1 << 23  # deprecated, use IMU_QUATERNION in EYETRACKING_STREAM
    PUPIL_CENTER = 1 << 24  # deprecated, not implemented on embedded
    EMBEDDED_INFO = 1 << 25
    CALIBRATION_ERROR = 1 << 26
    PULSE = 1 << 27
    GLINT = 1 << 28
    FUSE = 1 << 29
    PUPIL_ELLIPSE = 1 << 30
    IMU = 1 << 31


class EyeMask(enum.IntFlag):
    '''Specifies which tracker is valid'''
    UNUSED = 0x0
    RIGHT = 0x1
    LEFT = 0x2
    BINOCULAR = RIGHT | LEFT


class EyeTrackingStreamTypes(enum.IntEnum):
    '''The value corresponding to the et type'''
    GAZE = 1
    PER_EYE_GAZE = 2
    EYE_CENTER = 3
    PUPIL_POSITION = 4
    PUPIL_DIAMETER = 5
    GAZE_IN_IMAGE = 6
    GAZE_IN_SCREEN = 7
    IMU_QUATERNION = 8


class EyeTrackingStreamBits(enum.IntEnum):
    '''Bits used to enable/disable eye tracking streams'''
    GAZE = 1 << EyeTrackingStreamTypes.GAZE
    PER_EYE_GAZE = 1 << EyeTrackingStreamTypes.PER_EYE_GAZE
    EYE_CENTER = 1 << EyeTrackingStreamTypes.EYE_CENTER
    PUPIL_POSITION = 1 << EyeTrackingStreamTypes.PUPIL_POSITION
    PUPIL_DIAMETER = 1 << EyeTrackingStreamTypes.PUPIL_DIAMETER
    GAZE_IN_IMAGE = 1 << EyeTrackingStreamTypes.GAZE_IN_IMAGE
    GAZE_IN_SCREEN = 1 << EyeTrackingStreamTypes.GAZE_IN_SCREEN
    IMU_QUATERNION = 1 << EyeTrackingStreamTypes.IMU_QUATERNION


# properties defined on this class are mapped to point factories in influx_schema and must be maintained if it changes
@dataclasses.dataclass
class EyeTrackingStreamData:
    ''' Container for eye tracking data'''
    timestamp: float
    eye_mask: EyeMask
    gaze: typing.Any
    per_eye_gaze: typing.Any
    eye_center: typing.Any
    pupil_pos: typing.Any
    pupil_diameter: typing.Any
    gaze_in_image: typing.Any
    gaze_in_screen: typing.Any
    imu_quaternion: typing.Any


class FeatureStreamTypes(enum.IntEnum):
    '''The value corresponding to the feature type'''
    GLINT = 1
    FUSED = 2
    PUPIL_ELLIPSE = 3


class FeatureStreamBits(enum.IntEnum):
    '''Bits used to enable/disable feature streams'''
    GLINT = 1 << FeatureStreamTypes.GLINT
    FUSED = 1 << FeatureStreamTypes.FUSED
    PUPIL_ELLIPSE = 1 << FeatureStreamTypes.PUPIL_ELLIPSE


# properties defined on this class are mapped to point factories in influx_schema and must be maintained if it changes
@dataclasses.dataclass
class FeatureStreamData:
    ''' Container for feature data'''
    timestamp: float
    tracker_id: int
    glints: typing.Any
    fused: typing.Any
    ellipse: typing.Any


class StreamRates(enum.IntEnum):
    '''Enum representing the set of supported rates'''
    OFF = 0
    RATE_5 = 5
    RATE_30 = 30
    RATE_60 = 60
    RATE_90 = 90
    RATE_125 = 125
    RATE_200 = 200
    RATE_250 = 250
    RATE_333 = 333
    RATE_500 = 500


class BlobType(enum.IntEnum):
    '''Enum representing set of blob types'''
    CALIBRATION = 1
    MULTIGLINT = 2
    AUTOTUNE = 3
    DYNAMIC_FUSION = 4
    MODULE_CAL = 5
    MODEL_ET = 6
    MODEL_PRIORS = 7
    GEOMETRY = 8
    AUTOTUNE_MULTIGLINT = 9


class SystemInfo(enum.IntEnum):
    '''System info request types'''
    CAMERA_TYPE = 1
    DEVICE_SERIAL = 2
    FIRMWARE_API = 3
    FIRMWARE_VERSION = 4
    EYE_MASK = 5
    PRODUCT_ID = 6
    MULTI_INFO = 7
    BACKEND_VERSION = 8


class CameraType(enum.IntEnum):
    '''Enum respresenting the available cameras'''
    NOT_AVAILABLE = 0x00
    SMI = 0x01
    SMI_INV = 0x02
    QUANTA = 0x03
    QUANTA_INV = 0x04
    QUANTA2 = 0x05
    QUANTA2_INV = 0x06
    SINCERE = 0x07


class BlobVersion(enum.Enum):
    '''Enum representing current version of each blob type'''
    CALIBRATION = 9
    MULTIGLINT = 2
    AUTOTUNE = 2
    DYNAMIC_FUSION = 2
    MODULE_CAL = 6
    MODEL_ET = 2
    MODEL_PRIORS = 2
    GEOMETRY = 3
    AUTOTUNE_MULTIGLINT = 1


class PropertyType(enum.IntEnum):
    '''Enum representing set of property types'''
    AUTOTUNE_POSITION = 1
    STREAM_CONTROL = 2
    IPD = 3  # deprecated
    COMPONENT_OFFSETS = 4
    EVENT_CONTROL = 5
    # 6-8 are reserved for internal usage
    NORMALIZED_EYE_OFFSETS = 9
    # 10 is reserved for internal usage
    # 11 is reserved for internal usage
    # 12 is reserved for internal usage
    EYETRACKING_RATE = 13
    EYETRACKING_STREAMS = 14
    FEATURE_STREAMS = 15
    # 16 is reserved for internal usage
    NOMINAL_EYE_OFFSETS = 17


class ProcedureType(enum.IntEnum):
    '''Enum representing set of procedure types'''
    DEVICE_CALIBRATION = 1
    UPDATE_FIRMWARE = 2
    CALIBRATION_GUI = 3
    VALIDATION_GUI = 4
    AUTOTUNE_GUI = 5
    QUICKSTART_GUI = 6


@enum.unique
class Events(enum.IntEnum):
    '''Main different event types'''
    # indicating a confirmed combined blink event
    BLINK = 1
    # indicating the per-eye eye close event
    EYE_CLOSED = 2
    # indicating the per-eye eye open event
    EYE_OPENED = 3
    # indicating the trackloss start event
    TRACKLOSS_START = 4
    # indicating the trackloss end event
    TRACKLOSS_END = 5
    # indicating the confirmed combined saccade
    SACCADE = 6
    # indicating the per-eye saccade onset/start
    SACCADE_START = 7
    # indicating the per-eye saccade offset/end
    SACCADE_END = 8
    # information about a validation point
    VALIDATION_SAMPLE = 9
    # information about overall validation quality
    VALIDATION_SUMMARY = 10
    # indicating that a procedure has been started
    PROCEDURE_STARTED = 11
    # indicating that a procedure has ended and information about the the final results
    PROCEDURE_ENDED = 12
    # indicating the MCU external gpio trigger event
    EXTERNAL_TRIGGER = 13


class EventControlBit(enum.IntEnum):
    '''Bits that control enabling or disabling an event'''
    BLINK = 1 << 0
    EYE_CLOSE_OPEN = 1 << 1
    TRACKLOSS_START_END = 1 << 2
    SACCADE = 1 << 3
    SACCADE_START_END = 1 << 4
    VALIDATION_RESULTS = 1 << 5
    PROCEDURE_START_END = 1 << 6
    PRODECURE_START_END = 1 << 6  # TRSW-6535 typo deprecated in v5.11
    EXTERNAL_TRIGGER = 1 << 7


class CameraResolution(enum.IntEnum):
    '''Enum representing set of image resolutions supported by the camera module'''
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class LogMode(enum.IntEnum):
    '''The type of data to be logged'''
    NONE = 1               # Disable data logging
    BASIC = 2              # Device configs and tuning documents
    OCULAR = 3             # Basic + documents (autophase, autotune, calibration, validation)
    DIAGNOSTICS_LITE = 4   # Ocular + streams + eye features + accepted pulses
    DIAGNOSTICS_FULL = 5   # Ocular + streams + eye features + all pulses


class MarkerSequenceMode(enum.IntEnum):
    '''Enum representing 4 modes for the marker sequence window'''
    FIXED_HEAD = 0
    FIXED_GAZE = 1
    FIXED_HEAD_FOUR_MARKERS = 2
    FIXED_GAZE_FOUR_MARKERS = 3


class CameraUserSettings(enum.IntEnum):
    ''' Enum representing various settings that change the behaviour of the camera manager and marker sequence '''
    GAZE_DEPTH = 1
    PARALLAX_CORRECTION = 2
    SAMPLING_DURATION = 3
