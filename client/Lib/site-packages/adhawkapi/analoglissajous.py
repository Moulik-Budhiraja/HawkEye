'''This modules contains the APIs related to the Analog Lissajous application'''


import enum
import logging
import threading

from adhawktools import recordingdata

from . import baseapp, error, registers


MAX_WAIT_TIME_S = 10
DEFAULT_SAMPLE_COUNT = 500


@enum.unique
class ErrorType(enum.IntEnum):
    '''Analog error types'''
    COLLECTION_ERROR = 1
    BUSY_ERROR = 2


@enum.unique
class WarningType(enum.IntEnum):
    '''Analog error types'''
    OVERFLOW_WARNING = 1
    UNDERFLOW_WARNING = 2
    CAPTURE_STOPPED_WARNING = 3


class AnalogLissajousError(error.Error):
    '''Base exception class for analog lissajous errors'''


class AnalogLissajousApi(baseapp.BaseAppApi, app_id=12):
    '''API frontend for AdHawk's Analog Lissajous Application'''

    @enum.unique
    class DataType(enum.IntEnum):
        '''Analog received stream datatypes'''
        SEGMENT_STREAM = 0
        ERROR_STREAM = 1
        WARNING_STREAM = 2
        IMAGE_STREAM = 3
        END_OF_CAPTURE = 4
        INDEXED_SEGMENT = 5

    def add_callback_segment_data(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_iter_payload('<I', '<B')),
                                     self.DataType.SEGMENT_STREAM << 4 | self._app_id, key=func)

    def add_callback_error_data(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<H')),
                                     self.DataType.ERROR_STREAM << 4 | self._app_id, key=func)

    def add_callback_warning_data(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<H')),
                                     self.DataType.WARNING_STREAM << 4 | self._app_id, key=func)

    def add_callback_end_of_capture(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id),
                                     self.DataType.END_OF_CAPTURE << 4 | self._app_id, key=func)

    def add_callback_image_data(self, func):
        '''Add calback to retrieve indexed stream of the image data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<I100B')),
                                     self.DataType.IMAGE_STREAM << 4 | self._app_id, key=func)

    def add_callback_indexed_segment(self, func):
        '''Add calback to retrieve an indexed segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_iter_payload('<III', '<B')),
                                     self.DataType.INDEXED_SEGMENT << 4 | self._app_id, key=func)


class AnalogLissajous:
    '''A wrapper for handling and distributing streams of segment analog data'''

    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):
        self._segment_stream_cb = kwargs.get('segment_stream_cb', lambda _phase, _samples: None)
        self._image_received_cb = kwargs.get('image_received_cb', lambda _image_right, _image_left: None)
        self._done_cb = kwargs.get('done_cb', lambda: None)
        self._error_cb = kwargs.get('error_cb', lambda _msg: None)
        self._log_cb = kwargs.get('log_cb', lambda _data: None)
        self._api = None
        self._diag_data = None
        self._all_trackers = None
        self._expected_trackers = None
        self._num_samples_collected = None
        self._num_samples_expected = None
        self._error = None
        self._timer = None
        self._timeoutcv = None
        self._segments = None
        self._image_data = None
        self._image_width = None
        self._num_indexed_data_expected = None
        self._num_image_data_collected = None

    def setup_api(self, portname):
        '''Create api and set all related callbacks'''
        self._api = AnalogLissajousApi(portname)
        self._api.add_callback_segment_data(self._handle_segment_stream)
        self._api.add_callback_error_data(self._handle_error)
        self._api.add_callback_warning_data(self._handle_warning)
        self._api.add_callback_image_data(self._handle_image_stream)
        self._api.add_callback_end_of_capture(self._handle_end_of_capture)
        self._api.add_callback_indexed_segment(self._handle_indexed_segment)

        return self._api

    def remove_api_callbacks(self):
        ''' Removes all callbacks from api once no longer needed '''
        if self._api is not None:
            self._api.remove_callback(self._handle_segment_stream)
            self._api.remove_callback(self._handle_error)
            self._api.remove_callback(self._handle_warning)
            self._api.remove_callback(self._handle_image_stream)
            self._api.remove_callback(self._handle_end_of_capture)
            self._api.remove_callback(self._handle_indexed_segment)

    def capture(self, trackers=None, **opts):
        '''Start iris capture on given tracker(s), one tracker at a time'''

        if self._timer is not None:
            # another instance is already running
            self._timer.join()

        trackers = trackers or self._api.firmware_info.active_trackers
        printable_trackers = [tracker_id + 1 for tracker_id in trackers]
        logging.info(f'Starting iris capture on trackers {printable_trackers}')

        self._diag_data = recordingdata.RecordingData()
        self._all_trackers = set(trackers)
        self._expected_trackers = self._all_trackers.copy()
        self._num_samples_collected = {tracker_id: 0 for tracker_id in self._all_trackers}
        self._num_samples_expected = opts.get('sample_count', DEFAULT_SAMPLE_COUNT)

        # image data and indexed segment data streams are expected to be a constant size of 100
        self._num_indexed_data_expected = 100
        self._num_image_data_collected = {tracker_id: 0 for tracker_id in self._all_trackers}
        self._image_width = opts.get('image_width', 120)
        self._image_data = {tracker_id: [0] * int(self._image_width ** 2)
                            for tracker_id in self._all_trackers}

        # the data is expected to be received in full within a short time frame
        self._error = None
        self._timeoutcv = threading.Condition()
        self._timer = threading.Thread(target=self._timeout)
        self._timer.start()
        self._start_next_tracker()

    def _start_next_tracker(self):
        tracker_id = next(iter(self._expected_trackers))
        try:
            x_max = self._api.get_register(registers.MEGALISA_X_MAX, tracker_id)
            x_min = self._api.get_register(registers.MEGALISA_X_MIN, tracker_id)
            y_max = self._api.get_register(registers.MEGALISA_Y_MAX, tracker_id)
            y_min = self._api.get_register(registers.MEGALISA_Y_MIN, tracker_id)

            self._api.set_register(registers.ANALOGLISSAJOUS_X_MAX, x_max, tracker_id)
            self._api.set_register(registers.ANALOGLISSAJOUS_X_MIN, x_min, tracker_id)
            self._api.set_register(registers.ANALOGLISSAJOUS_Y_MAX, y_max, tracker_id)
            self._api.set_register(registers.ANALOGLISSAJOUS_Y_MIN, y_min, tracker_id)

            self._api.start(tracker_id)
        except error.Error as excp:
            self._error = AnalogLissajousError(
                logging.warning(f'Failed to start analog lissajous collection on Tracker {tracker_id + 1}: {excp}'))
            self.stop()

    def stop(self):
        '''Stop app if running'''
        if self._timeoutcv is not None:
            with self._timeoutcv:
                self._timeoutcv.notify()

    def _timeout(self):
        with self._timeoutcv:
            notified = self._timeoutcv.wait(MAX_WAIT_TIME_S)
            for tracker_id in self._all_trackers:
                try:
                    self._api.stop(tracker_id)
                except error.Error:
                    pass

        if self._error is not None:
            self._error_cb(self._error)
        elif not notified and self._expected_trackers:
            self._error_cb(AnalogLissajousError('Did not receive the full set of expected data'))
        self._done_cb()

    def _handle_end_of_data_capture(self, tracker_id):
        logging.info(f'Successfully captured iris data for tracker: {tracker_id + 1}')
        with self._timeoutcv:
            try:
                self._expected_trackers.remove(tracker_id)
            except KeyError:
                # got an unexpected end of collection
                return
            if self._expected_trackers:
                # still expecting more trackers. start the next tracker
                # but since we're on the callback from api layer, we have to
                # create another thread to issue the requests
                threading.Thread(target=self._start_next_tracker).start()
                return
            self._timeoutcv.notify()

        image_right = self._image_data.get(0, None)
        image_left = self._image_data.get(1, None)
        if image_right:
            image_right = image_right.copy()
        if image_left:
            image_left = image_left.copy()
        self._image_received_cb(image_right, image_left)
        self._log_cb(self._diag_data)

    def _handle_indexed_segment(self, tracker_id, index, phase, polarity, *samples):
        logging.debug(f'tracker_id={tracker_id}, phase={phase}, len={len(samples)}')
        if self._num_indexed_data_expected != len(samples):
            logging.debug(f'Received segment with missing data. '
                          f'expected={self._num_indexed_data_expected}, received={len(samples)}')
            return

        self._diag_data['indexed_segment'][tracker_id].append(phase=phase, polarity=polarity,
                                                              index=index, samples=samples)

    def _handle_segment_stream(self, tracker_id, phase, *samples):
        if self._num_samples_expected != len(samples):
            logging.debug(f'Received segment with missing data. '
                          f'expected={self._num_samples_expected}, received={len(samples)}')
            return

        self._diag_data['segment'][tracker_id].append(phase=phase, samples=samples)

        self._segment_stream_cb(phase, samples)

    def _handle_error(self, tracker_id, error_value):
        self._error = AnalogLissajousError(f'Tracker {tracker_id}: {ErrorType(error_value).name}')
        self._handle_end_of_data_capture(tracker_id)

    def _handle_warning(self, tracker_id, warning_value):
        logging.warning(f'Tracker {tracker_id + 1}: {WarningType(warning_value).name}')
        if WarningType(warning_value) == WarningType.CAPTURE_STOPPED_WARNING:
            self._handle_end_of_data_capture(tracker_id)

    def _handle_image_stream(self, tracker_id, index, *data):
        if tracker_id not in self._all_trackers:
            return
        logging.debug({f'tracker_id={tracker_id}, index={index}, len(data)={len(data)}'})
        if self._num_indexed_data_expected != len(data):
            logging.debug(f'Received image stream with missing data. '
                          f'expected={self._num_indexed_data_expected}, received={len(data)}')
            return

        if index >= self._image_width**2:
            return

        if self._num_image_data_collected[tracker_id] >= self._image_width**2:
            return

        self._image_data[tracker_id][index:] = data
        self._diag_data['image'][tracker_id].append(index=index, data=data)
        self._num_image_data_collected[tracker_id] += self._num_indexed_data_expected

    def _handle_end_of_capture(self, tracker_id):
        logging.warning(f'Tracker {tracker_id + 1}: End of Capture')
        self._handle_end_of_data_capture(tracker_id)
