'''This module provides Autotune related APIs

Autotune application is responsible for handling the initial tuning of
laser current, frequency, scan range, etc. to handle both variation in
devices and in people (and maybe in operating conditions)

'''

import enum

from adhawktools import model, recordingdata

from . import configs, register_api, trackermodel
from .capi.py import libah_api
from .internal import PacketType


ERROR_MAP = {
    0: 'Glint not found',
    1: 'Invalid frequency setting',
    2: 'Glint not found: laser power may be too high',
    3: 'Glint not found: laser power may be too low',
    4: 'Attempting to take too many steps during line sweep in X axis',
    5: 'Attempting to take too many steps during line sweep in Y axis',
    6: 'Selected algorithm is not supported',
    8: 'Autophase not ready, please ensure you are looking straight ahead while auto-tuning',
    9: 'Pupil feature not detected, please ensure you are looking straight ahead while auto-tuning',
    10: 'Glint feature not detected, please ensure you are looking straight ahead while auto-tuning',
    11: 'Failed to solve for the desired scan range',
    12: 'Failed to solve for the eye position',
    13: 'Autotune result was out of bounds'
}


def autotune_message(errorcode):
    '''map autotune errorcode to error message'''
    return ERROR_MAP[errorcode]


class DataType(enum.IntEnum):
    '''Various data types streamed by the autotune application'''
    END_OF_TUNE = 0
    ERROR_DATA = 14


class Algorithm(enum.IntEnum):
    '''Available autotune algorithms'''
    NO_OP = 0
    LINESWEEP = 1
    GLINT_BASED_BOX_SIZING = 2
    PHYSMODEL = 3
    LASER = 4


class AutoTuneApi(register_api.RegisterApi):
    '''Customized api class to collect autotune analytics data'''

    def register_analytics(self, report_analytics_cb):
        '''Register callback for analytics streams from embedded eye tracker'''
        self._callbacks.add_callback(lambda pkt: report_analytics_cb(pkt.payload),
                                     PacketType.ANALYTICS, key=report_analytics_cb)


class AutoTune:
    '''This class provides the ability to execute the autotune application in
    the microcode and retrieve the result

    Args:
        port (str): portname of the eye tracking hardware
        configmodel (ConfigModel): configuration model for tracker if available
        log_cb (callback(data)): callback to handle result and data logging

    '''

    def __init__(self, port, configmodel=None, log_cb=None):
        self._configmodel = configmodel
        self._log_cb = log_cb
        self._trackers_awaiting_results = None
        self._diag_data = None
        self._api = AutoTuneApi(port)
        self._api.register_analytics(self._handle_diag_info)

    def trigger(self, trackers, recording_configs, data=None):
        '''Start the autotune process'''

        self._trackers_awaiting_results = set(trackers)
        # Reinitialize diag_data because its cleared on finalize
        self._diag_data = recordingdata.RecordingData(configs=recording_configs)

        libah_api.trigger_autotune(data)

        if self._configmodel is not None:
            paths = []
            for trid in trackers:
                conf_keys = [configs.TRACKER_XMEAN_PCT, configs.TRACKER_XMEAN,
                             configs.TRACKER_YMEAN_PCT, configs.TRACKER_YMEAN,
                             configs.TRACKER_WIDTH_PCT, configs.TRACKER_WIDTH,
                             configs.TRACKER_HEIGHT_PCT, configs.TRACKER_HEIGHT,
                             configs.TRACKER_LASERCURRENTPCT, configs.TRACKER_LASERCURRENT,
                             configs.TRACKER_EYE_MODEL_POS_X, configs.TRACKER_EYE_MODEL_POS_Y,
                             configs.TRACKER_EYE_MODEL_POS_Z]
                for conf_key in conf_keys:
                    paths.append(trackermodel.construct_path(trid, conf_key))
            paths.append(configs.BLOB_TUNING_MULTIGLINT)

            self._configmodel.load(model.Subsystem.HARDWARE, paths)
            updated_configs = self._configmodel.paths_to_dict(paths)
            return updated_configs

        return None

    def _finalize(self):
        if self._log_cb is not None:
            self._log_cb(self._diag_data)
        self._trackers_awaiting_results = None
        self._diag_data = None

    def _handle_diag_info(self, data):
        if self._diag_data is None or data[0] != 1:
            return

        trackerid = data[1]
        info_type = data[2]
        self._diag_data['data'][str(trackerid)].append(
            info_type=info_type, info=list(data[3:]))
        if info_type in (DataType.END_OF_TUNE, DataType.ERROR_DATA):
            self._trackers_awaiting_results.remove(trackerid)
            if not self._trackers_awaiting_results:
                self._finalize()
