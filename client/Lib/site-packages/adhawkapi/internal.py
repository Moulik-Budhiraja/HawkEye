'''This module contains the definitions for AdHawk's private eye tracking API'''

import dataclasses
import enum
import math
import struct
import typing

from . import apipacket


class PacketType(enum.IntEnum):
    '''Enum for internal packet types'''

    V2 = 0xa0  # pylint: disable=invalid-name
    CONTROL = 0xa1
    EMBEDDED_INFO = 0xa2
    ANALYTICS = 0xa3
    RAW_PULSE_V3 = 0xa4
    RAW_PULSE_V2 = 0xa5
    DEBUG_ANNOTATION = 0xa6
    FAULT_INFO = 0xae
    DEBUG_MSG = 0xaf

    def is_stream(self):
        '''Returns whether the packet is a stream'''
        return self in (PacketType.EMBEDDED_INFO, PacketType.RAW_PULSE_V2, PacketType.RAW_PULSE_V3)

    def header_len(self):
        '''Returns the request header length'''
        if self == PacketType.CONTROL:
            return 2
        return 1

    def __repr__(self):
        return f'{str(self.name).lower()} ({hex(self.value)})'


class ControlType(enum.IntEnum):
    '''List of supported commands through internal control API (0xa1)'''
    START = 1  # deprecated - see System Control
    STOP = 2  # deprecated - see System Control
    LOG_MODE = 3
    AUTOPHASE = 4
    REFUSE = 5  # obsolete, glint-only fusion legacy
    RELOAD = 6
    PULSE_STREAM_CONFIG = 7
    LASER_SAFETY_CONTROL = 8
    SCANBOX = 9


class PropertyType(enum.IntEnum):
    '''Enum representing set of internal property types'''
    # 1-5 are reserved for public usage
    SCAN_REGION = 6
    SCAN_POWER = 7
    DETECTOR_SENSITIVITY = 8
    LOW_POWER_CONTROL = 10
    PUPIL_OFFSET = 11
    INTERFACE_CONTROL = 12
    AUTOTUNE_PHYS_MODEL_RESIDUALS = 16
    ALGORITHM_PIPELINE = 18


class ScanboxType(enum.IntEnum):
    '''List of scanbox types for setscanbox api (0xa1, 0x09)'''
    AUTOTUNE = 1
    NOMINAL = 2


class AnalyticsStreamType(enum.IntEnum):
    '''List of analytics related streams from the eye tracking module (0xa3)'''
    AUTOTUNE = 1
    CALIBRATION = 2
    ANNOTATIONS = 3
    AUTOPHASE = 4
    BLOB = 5
    HOST_INFO = 6
    SESSION_INFO = 7  # deprecated
    SESSION_INFO_V2 = 8


class AutotuneAnalyticsType(enum.IntEnum):
    '''List of autotune related analytics streams (0xa3, 1)'''
    END_OF_TUNE = 0
    ALGORITHM_ID = 1
    TUNING_RESULT = 2
    OLD_TUNING_RESULT = 3  # deprecated
    JITTER_PULSE_DATA = 10  # deprecated
    DIAG_DATA = 12
    ERROR_CODE = 14


class AutotuneAnalyticsDiagType(enum.IntEnum):
    '''List of autotune analytics diag types (0xa3, 1, 12, 0)'''
    ALG_TYPE = 0  # deprecated
    AUTOTUNE_PULSE = 1
    LINESWEEP_PULSE = 2  # deprecated
    PHASE_OFFSET = 3
    FEATURE_DATA = 4
    PHYSMODEL_DATA = 5
    REF_GAZE_VECTOR = 6
    SUB_WINDOW = 7


class CalibrationAnalyticsType(enum.IntEnum):
    '''List of calibration related analytics streams (0xa3, 2)'''
    CALPOINT = 1
    GAZE = 2
    GLINT = 3
    GLINT_V2 = 4
    CALPOINT_GAZE = 5
    MODEL_FEATURES = 6
    MODEL_STATES = 7
    DSCALES = 8
    PRECISION = 9


@enum.unique
class Annotations(enum.IntEnum):
    '''List of annotation analytics (0xa3, 3)'''
    CALIBRATION_START = 0
    CALIBRATION_END = 1
    CALIBRATION_ABORT = 2
    CALIBRATION_POINT = 3
    RECENTER = 4
    AUTOTUNE_START = 5
    AUTOTUNE_END = 6
    DATASTREAM = 7
    AUTOPHASE_END = 8
    FUSION_FUSED = 9
    CALIBRATION_SAMPLE = 10
    VALIDATION_START = 11
    VALIDATION_END = 12
    VALIDATION_POINT = 13
    VALIDATION_SAMPLE = 14
    AUTOPHASE_START = 15
    ALGORITHM_PIPELINE_UPDATE = 16


class HostInfoTypes(enum.IntEnum):
    '''The Host Info types (0xa3, 6)'''
    APPVERSION = 1
    OSNAME = 2


class PdType(enum.IntFlag):
    '''Flags indicating the type of pd'''
    UNUSED = 0
    GLINT = 1
    PUPIL = 2
    SHARED = GLINT | PUPIL


class AlgorithmPipeline(enum.IntFlag):
    '''Algorithm pipeline types'''
    PUPIL_ONLY = 0
    RESEARCH = 1
    SLIP_TOLERANT = 2


# Packet Definitions

@dataclasses.dataclass
class AnalyticsAutotuneEndofTune(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.END_OF_TUNE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    pass

    @classmethod
    def payload_format(cls):
        # This packet has no data
        return '<'


@dataclasses.dataclass
class AnalyticsAutotuneAlgorithmId(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.ALGORITHM_ID
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    step: int
    algorithm: int

    @classmethod
    def payload_format(cls):
        return '<2B'


@dataclasses.dataclass
class AnalyticsAutotuneTuningResult(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.TUNING_RESULT
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    step: int
    tunable_key: int
    tunable_value: int

    @classmethod
    def payload_format(cls):
        return '<B2H'

    @staticmethod
    def _tunable_name(tunable):
        tunable_names = [
            'xmin',
            'xmax',
            'ymin',
            'ymax',
            'lasercurrent'
        ]
        return tunable_names[tunable]

    def data(self):
        return {
            self._tunable_name(self.tunable_key): self.tunable_value
        }


@dataclasses.dataclass
class AnalyticsAutotuneDiagPulse(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.DIAG_DATA,
    apipacket.Wildcard.WILDCARD,  # step
    AutotuneAnalyticsDiagType.AUTOTUNE_PULSE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    timestamp: int
    xstamp: int
    ystamp: int
    pw: int  # pylint: disable=invalid-name
    encamp: int
    dwell: int
    # fields initialized later from unpacked data
    pdid: int = dataclasses.field(init=False)

    @classmethod
    def payload_format(cls):
        return '<6H'

    def __post_init__(self):
        self.pdid = (self.encamp >> 12) & 0xf


@dataclasses.dataclass
class AnalyticsAutotuneDiagPhaseOffset(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.DIAG_DATA,
    apipacket.Wildcard.WILDCARD,  # step
    AutotuneAnalyticsDiagType.PHASE_OFFSET
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    xphase: float
    yphase: float

    @classmethod
    def payload_format(cls):
        return '<2f'


@dataclasses.dataclass
class AnalyticsAutotuneDiagFeatureData(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.DIAG_DATA,
    apipacket.Wildcard.WILDCARD,  # step
    AutotuneAnalyticsDiagType.FEATURE_DATA
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    pupil_x: float
    pupil_y: float
    glints_x: list[float]
    glints_y: list[float]

    @classmethod
    def payload_format(cls):
        return '<14f'

    @classmethod
    def unpack(cls, pkt: bytes) -> tuple[int, typing.Any]:
        pkt_len = cls._header_len + struct.calcsize(cls.payload_format())
        features = struct.unpack_from(cls.payload_format(), pkt, cls._header_len)
        pupil_x, pupil_y = features[0:2]
        glints_x = features[2::2]
        glints_y = features[3::2]
        return pkt_len, (
            pupil_x, pupil_y,
            glints_x, glints_y
        )

    def pack(self) -> bytes:
        raise NotImplementedError


@dataclasses.dataclass
class AnalyticsAutotuneDiagPhysModelData(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerId
    AutotuneAnalyticsType.DIAG_DATA,
    apipacket.Wildcard.WILDCARD,  # step
    AutotuneAnalyticsDiagType.PHYSMODEL_DATA
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    offset_x: float
    offset_y: float
    offset_z: float
    gaze_az: float
    gaze_el: float

    @classmethod
    def payload_format(cls):
        return '<5f'


@dataclasses.dataclass
class AnalyticsAutotuneDiagRefGazeVector(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerId
    AutotuneAnalyticsType.DIAG_DATA,
    apipacket.Wildcard.WILDCARD,  # step
    AutotuneAnalyticsDiagType.REF_GAZE_VECTOR
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    x_comp: float
    y_comp: float
    z_comp: float

    @classmethod
    def payload_format(cls):
        return '<3f'

    def data(self) -> list:
        return [self.x_comp, self.y_comp, self.z_comp]


@dataclasses.dataclass
class AnalyticsAutotuneDiagSubWindow(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerId
    AutotuneAnalyticsType.DIAG_DATA,
    apipacket.Wildcard.WILDCARD,  # step
    AutotuneAnalyticsDiagType.SUB_WINDOW
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    @classmethod
    def payload_format(cls):
        return '<4f'


@dataclasses.dataclass
class AnalyticsAutotuneErrorCode(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOTUNE,
    apipacket.Wildcard.WILDCARD,  # trackerid
    AutotuneAnalyticsType.ERROR_CODE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    step: int
    error: int

    @classmethod
    def payload_format(cls):
        return '<2B'


@dataclasses.dataclass
class AnalyticsAnnotationsAutophaseEnd(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.ANNOTATIONS, Annotations.AUTOPHASE_END
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    # pylint: disable=invalid-name
    timestamp: float
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def payload_format(cls):
        return '<5f'

    @classmethod
    def unpack(cls, pkt: bytes) -> tuple[int, typing.Any]:
        pkt_len = cls._header_len + struct.calcsize(cls.payload_format())
        data = map(math.degrees, struct.unpack_from(cls.payload_format(), pkt, cls._header_len))
        return pkt_len, data

    def pack(self) -> bytes:
        header = struct.pack(self._header_format, *self._header)
        data = struct.pack(self.payload_format(), map(math.radians, dataclasses.astuple(self)))
        return header + data


@dataclasses.dataclass
class AnalyticsAutophase(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.AUTOPHASE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    trackerid: int
    pdindex: int
    timestamp: float
    pw: float  # pylint: disable=invalid-name
    xphase: float
    yphase: float

    @classmethod
    def payload_format(cls):
        return '<2B4f'


@dataclasses.dataclass
class CalibrationSample(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.ANNOTATIONS, Annotations.CALIBRATION_SAMPLE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    timestamp: float
    gaze_ref_x: float
    gaze_ref_y: float
    gaze_ref_z: float
    glint_x0: float
    glint_y0: float
    glint_x1: float
    glint_y1: float
    pupil_x0: float
    pupil_y0: float
    pupil_x1: float
    pupil_y1: float

    @classmethod
    def payload_format(cls):
        return '<12f'


@dataclasses.dataclass
class AnalyticsCalibrationCalpoint(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.CALPOINT
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    # pylint: disable=invalid-name
    x: float
    y: float
    z: float

    @classmethod
    def payload_format(cls):
        return '<3f'


@dataclasses.dataclass
class AnalyticsCalibrationGaze(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.GAZE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    # pylint: disable=invalid-name
    x: float
    y: float
    z: float

    @classmethod
    def payload_format(cls):
        return '<3f'


@dataclasses.dataclass
class AnalyticsCalibrationGlintV2(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.GLINT_V2
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    glint_mask: int
    glint_x0: float
    glint_y0: float
    glint_x1: float
    glint_y1: float
    pupil_mask: int
    pupil_x0: float
    pupil_y0: float
    pupil_x1: float
    pupil_y1: float

    @classmethod
    def payload_format(cls):
        return '<B4fB4f'


@dataclasses.dataclass
class AnalyticsCalibrationCalpointGaze(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.CALPOINT_GAZE
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    cal_data_x: float
    cal_data_y: float
    cal_data_z: float
    gaze_data_x: float
    gaze_data_y: float
    gaze_data_z: float

    @classmethod
    def payload_format(cls):
        return '<6f'

    def data(self) -> dict:
        return {
            'cal_data': {
                'x': self.cal_data_x,
                'y': self.cal_data_y,
                'z': self.cal_data_z},
            'gaze_data': {
                'x': self.gaze_data_x,
                'y': self.gaze_data_y,
                'z': self.gaze_data_z}
        }


@dataclasses.dataclass
class AnalyticsCalibrationModelFeatures(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.MODEL_FEATURES
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    pupil_x0: float
    pupil_y0: float
    glints_x0: list[float]
    glints_y0: list[float]
    pupil_x1: float
    pupil_y1: float
    glints_x1: list[float]
    glints_y1: list[float]

    @classmethod
    def payload_format(cls):
        return '<28f'

    @classmethod
    def unpack(cls, pkt):
        pkt_len = cls._header_len + struct.calcsize(cls.payload_format())
        features = struct.unpack_from(cls.payload_format(), pkt, cls._header_len)
        features0 = features[:len(features) // 2]
        features1 = features[len(features) // 2:]
        pupil_x0, pupil_y0 = features0[0:2]
        glints_x0 = features0[2::2]
        glints_y0 = features0[3::2]
        pupil_x1, pupil_y1 = features1[0:2]
        glints_x1 = features1[2::2]
        glints_y1 = features1[3::2]
        return pkt_len, (
            pupil_x0, pupil_y0,
            glints_x0, glints_y0,
            pupil_x1, pupil_y1,
            glints_x1, glints_y1
        )

    def pack(self):
        raise NotImplementedError


@dataclasses.dataclass
class AnalyticsCalibrationModelState(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.MODEL_STATES
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    offset_x0: float
    offset_y0: float
    offset_z0: float
    gaze_az0: float
    gaze_el0: float
    offset_x1: float
    offset_y1: float
    offset_z1: float
    gaze_az1: float
    gaze_el1: float

    @classmethod
    def payload_format(cls):
        return '<10f'


@dataclasses.dataclass
class AnalyticsCalibrationDscales(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.DSCALES
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    dscale_x0: float
    dscale_y0: float
    dscale_x1: float
    dscale_y1: float

    @classmethod
    def payload_format(cls):
        return '<4f'


@dataclasses.dataclass
class AnalyticsCalibrationPrecision(apipacket.ApiPacket, header=(
    PacketType.ANALYTICS, AnalyticsStreamType.CALIBRATION, CalibrationAnalyticsType.PRECISION
)):
    '''Subclass of apipacket.ApiPacket registering the given header'''
    precision: float

    @classmethod
    def payload_format(cls):
        return '<f'
