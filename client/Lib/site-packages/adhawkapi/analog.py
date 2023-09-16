'''This modules contains the APIs related to the Analog Frontend application'''

import collections
import enum
import logging
import threading

import numpy as np

from adhawktools import recordingdata

from . import base, baseapp, error, registers, version


MAX_WAIT_TIME_S = 3
# number analog samples
MAX_SAMPLE_COUNT = 55000
# ringdown sampling configurations are determined by resosance detection objectives
RINGDOWN_SAMPLE_COUNT = 1024
RINGDOWN_SAMPLE_RESOLUTION = 12
RINGDOWN_SAMPLE_RATE = 42000

ADC_DEFAULT_REFERENCE_VOLTAGE = 3.3
DRIVE_REFERENCE_VOLTAGE = 3.3

Adc = collections.namedtuple('Adc', 'inputclock sampling_frequency')


class AnalogError(error.Error):
    '''Base exception class for all analog collection errors'''
    pass


@enum.unique
class ErrorType(enum.IntEnum):
    '''Analog error types'''
    COLLECTION_ERROR = 0
    TIMEOUT_ERROR = 1
    WINDOW_MEGASAMPLE_TRIGGER_ERROR = 2
    CHANNEL_BUSY = 3


class AnalogRuntimeError(AnalogError):
    '''Encountered an error during an analog collection'''

    def __init__(self, error_type, tr_id, chan=None):
        self.error_type = ErrorType(error_type)
        msg = f'Analog collection error on Tracker {tr_id + 1}'
        if chan is not None:
            msg += f' Channel {registers.AnalogChannelSelection(chan).name}'
        super().__init__(f'{msg}: {self.error_type.name}')


class AnalogCollectionApi(baseapp.BaseAppApi, app_id=11):
    '''API frontend for AdHawk's AnalogFrontend Application'''

    @enum.unique
    class DataType(enum.IntEnum):
        '''Analog received stream datatypes'''
        ANALOG_STREAM = 0
        ERROR_DATA = 1
        ANALOG_WINDOW_STREAM = 2
        ANALOG_CHANNEL_WINDOW_STREAM = 3
        ANALOG_CHANNEL_ERROR_STREAM = 4
        ANALOG_FAST_CAPTURE_STREAM = 5

    def add_callback_analog_data(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<HHHHH')),
                                     self.DataType.ANALOG_STREAM << 4 | self._app_id,
                                     key=func)

    def add_callback_serial_analog_data(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<BBBBBBBBBBBBBB')),
                                     self.DataType.ANALOG_FAST_CAPTURE_STREAM << 4 | self._app_id,
                                     key=func)

    def add_callback_error(self, func):
        '''Add calback to retrieve a segment of the sampled data'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<H')),
                                     self.DataType.ERROR_DATA << 4 | self._app_id,
                                     key=func)

    def add_callback_analog_window_data(self, func):
        '''Add calback to retrieve analyzed window results'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<HHH')),
                                     self.DataType.ANALOG_WINDOW_STREAM << 4 | self._app_id,
                                     key=func)

    def add_callback_channel_window(self, func):
        '''Add calback to retrieve the channel id and results of the analyzed window'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<HHHH')),
                                     self.DataType.ANALOG_CHANNEL_WINDOW_STREAM << 4 | self._app_id,
                                     key=func)

    def add_callback_channel_error(self, func):
        '''Add calback to retrieve the the error raised by the channel'''
        self._callbacks.add_callback(lambda pkt: func(pkt.metadata.src_id,
                                                      *pkt.unpack_payload('<HH')),
                                     self.DataType.ANALOG_CHANNEL_ERROR_STREAM << 4 | self._app_id,
                                     key=func)


class AnalogCollection:
    '''A wrapper for handling and distributing streams of analog data'''

    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):
        self._done_cb = kwargs.get('done_cb', lambda _resonances: None)
        self._error_cb = kwargs.get('error_cb', lambda _msg: None)
        self._log_cb = kwargs.get('log_cb', lambda _data: None)
        self._diag_data = None
        self._window_data = None
        self._all_trackers = None
        self._expected_trackers = None
        self._expected_channels = None
        self._num_samples_collected = None
        self._num_samples_expected = None
        self._sample_resolution = None
        self._sample_rate = None
        self._timeseries_data = None
        self._channel = None
        self._opts = None
        self._api = None
        self._timer = None
        self._timeoutcv = None
        self._error = None
        self._megasampling = None
        self._adc_reference_voltage = ADC_DEFAULT_REFERENCE_VOLTAGE

    def setup_api(self, portname):
        '''
        Setup the resonance detection api for the provided tracker.
        If the port isn't provided, the expectation is that the API has already been created
        '''
        self._api = AnalogCollectionApi(portname)
        return self._api

    def _setup_callbacks(self):
        '''sets up api callbacks to be associated with this object's api'''
        self._api.add_callback_analog_data(self._handle_analog_stream)
        self._api.add_callback_serial_analog_data(self._handle_serial_analog_stream)
        self._api.add_callback_error(self._handle_error_stream)
        self._api.add_callback_analog_window_data(self._handle_analog_window_stream)
        self._api.add_callback_channel_window(self._handle_analog_channel_window_stream)
        self._api.add_callback_channel_error(self._handle_channel_error_stream)

    def _remove_api_callbacks(self):
        '''Removes the api com callbacks associated with this object'''
        self._api.remove_callback(self._handle_analog_stream)
        self._api.remove_callback(self._handle_serial_analog_stream)
        self._api.remove_callback(self._handle_error_stream)
        self._api.remove_callback(self._handle_analog_window_stream)
        self._api.remove_callback(self._handle_analog_channel_window_stream)
        self._api.remove_callback(self._handle_channel_error_stream)

    def _adc_result_to_voltage(self, result, resolution=12):
        return np.array(result) / (2**resolution - 1) * self._adc_reference_voltage

    def sample(self, channel, trackers=None, **opts):
        '''Start the process of analog collection on a requested channel'''
        if self._timer is not None:
            # another instance is already running
            self._timer.join()

        self._setup_callbacks()

        trackers = trackers or self._api.firmware_info.active_trackers
        printable_trackers = [tracker_id + 1 for tracker_id in trackers]
        logging.info(f'Starting analog collection on the {channel} channel on'
                     f' trackers {printable_trackers}')

        self._diag_data = recordingdata.RecordingData()
        self._all_trackers = set(trackers)
        self._expected_trackers = self._all_trackers.copy()
        if channel == registers.AnalogChannelSelection.SPARE_1_AND_SPARE_2:
            self._expected_channels = {registers.AnalogChannelSelection.SPARE_1,
                                       registers.AnalogChannelSelection.SPARE_2}
        else:
            self._expected_channels = set([channel])
        self._window_data = {}
        self._num_samples_collected = {tracker_id: 0 for tracker_id in self._all_trackers}
        self._num_samples_expected = opts.get('sample_count', RINGDOWN_SAMPLE_COUNT)
        self._sample_resolution = opts.get('sample_resolution', RINGDOWN_SAMPLE_RESOLUTION)
        self._sample_rate = opts.get('sample_rate', RINGDOWN_SAMPLE_RATE)
        if channel == registers.AnalogChannelSelection.RINGDOWN:
            self._sample_resolution = RINGDOWN_SAMPLE_RESOLUTION
            self._sample_rate = RINGDOWN_SAMPLE_RATE
        self._channel = channel
        self._opts = opts
        self._timeseries_data = {tracker_id: [0] * self._num_samples_expected
                                 for tracker_id in self._all_trackers}
        self._megasampling = opts.get('megasample', False)

        logging.debug(f'Expected Channels {self._expected_channels}')

        # the data is expected to be received in full within a short time frame
        self._error = None
        self._timeoutcv = threading.Condition()
        self._timer = threading.Thread(target=self._timeout)
        self._timer.start()
        self._start_next_tracker()

    def stop(self):
        '''Stop analog operation if running'''
        if self._timeoutcv is not None:
            with self._timeoutcv:
                self._timeoutcv.notify()

    def _start_next_tracker(self):
        tracker_id = next(iter(self._expected_trackers))
        try:
            # for firmware with analog collection config support, set safe default values
            self._api.set_register(registers.ANALOG_CHANNEL_SELECTION, self._channel.value, tracker_id)
            self._api.set_register(registers.ANALOG_SAMPLE_COUNT, self._num_samples_expected, tracker_id)
            self._api.set_register(registers.ANALOG_SETTLING_TIME,
                                   self._opts.get('settling_time', 100), tracker_id)
            if version.SemanticVersion.compare(self._api.firmware_info.api_version,
                                               version.SemanticVersion(0, 45, 0)) >= 0:
                self._api.set_register(registers.ANALOG_MEGASAMPLE_ENABLE,
                                       1 if self._megasampling else 0, tracker_id)
                self._api.set_register(registers.ANALOG_HIGH_THRESHOLD_TRIGGER,
                                       self._opts.get('high_threshold', 4095), tracker_id)
                self._api.set_register(registers.ANALOG_LOW_THRESHOLD_TRIGGER,
                                       self._opts.get('low_threshold', 0), tracker_id)
                self._api.set_register(registers.ANALOG_OBSERVER_WINDOW_SIZE,
                                       self._opts.get('window_size', 100), tracker_id)
            elif self._megasampling:
                raise base.MinimumAPIVersion(
                    f'Megasampling requires API 0.45.0 > {self._api.firmware_info.api_version}')

            if version.SemanticVersion.compare(self._api.firmware_info.api_version,
                                               version.SemanticVersion(0, 47, 0)) >= 0:
                self._api.set_register(registers.ANALOG_HIGH_THRESHOLD_TRIGGER_2,
                                       self._opts.get('high_threshold_2', 4095), tracker_id)
                self._api.set_register(registers.ANALOG_LOW_THRESHOLD_TRIGGER_2,
                                       self._opts.get('low_threshold_2', 0), tracker_id)
            elif self._channel == registers.AnalogChannelSelection.SPARE_1_AND_SPARE_2:
                raise base.MinimumAPIVersion(
                    f'2-channel sampling requires API 0.47.0 > {self._api.firmware_info.api_version}')

            if version.SemanticVersion.compare(self._api.firmware_info.api_version,
                                               version.SemanticVersion(0, 60, 0)) >= 0:
                self._api.set_register(registers.ANALOG_SAMPLE_RATE, self._sample_rate, tracker_id)
                self._api.set_register(registers.ANALOG_SAMPLE_RESOLUTION, self._sample_resolution, tracker_id)

            if version.SemanticVersion.compare(self._api.firmware_info.api_version,
                                               version.SemanticVersion(0, 86, 0)) >= 0:
                regval = self._api.get_register(registers.SPEC_ADC_REFERENCE_VOLTAGE)
                self._adc_reference_voltage = regval / 1000.0

        except error.Error as excp:
            self._error = AnalogError(
                f'Failed to configure analog collection on Tracker {tracker_id + 1}: {excp}')
            self.stop()
            return

        try:
            self._api.start(tracker_id)
        except error.Error as excp:
            self._error = AnalogError(
                f'Failed to start analog collection on Tracker {tracker_id + 1} '
                f'Channel {self._channel.name}: {excp}')
            self.stop()

    def _timeout(self):
        with self._timeoutcv:
            notified = self._timeoutcv.wait(MAX_WAIT_TIME_S * len(self._all_trackers))
            for tracker_id in self._all_trackers:
                try:
                    self._api.stop(tracker_id)
                except error.Error:
                    pass

        if self._error is not None:
            self._error_cb(self._error)
        elif not notified and (self._expected_trackers or self._expected_channels):
            self._error_cb(AnalogError('Did not receive the full set of analog data'))

        self._remove_api_callbacks()

    def _finalize(self):
        if self._megasampling:
            self._done_cb(self._window_data)
        elif self._channel == registers.AnalogChannelSelection.RINGDOWN:
            self._done_cb(self._timeseries_data)
        else:
            # Only ringdown supports multiple trackers, so simplify the results
            _trid, result = self._timeseries_data.popitem()
            self._done_cb(self._adc_result_to_voltage(result, resolution=self._sample_resolution))
        self._log_cb(self._diag_data)

    def _handle_end_of_analog_stream(self, tracker_id):
        logging.debug(f'Successfully collected analog data for tracker: {tracker_id + 1}')
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

        self._finalize()

    def _handle_error_stream(self, tracker_id, error_value):
        self._error = AnalogRuntimeError(error_value, tracker_id)

        self.stop()

    def _handle_serial_analog_stream(self, tracker_id, *samples):
        if self._num_samples_collected[tracker_id] >= self._num_samples_expected:
            # received data after completing a collection operation
            return

        for sample in samples:
            self._diag_data[f'{self._channel.name.lower()}_serial_data'][tracker_id].append(sample=sample)
            self._timeseries_data[tracker_id][self._num_samples_collected[tracker_id]] = sample
            self._num_samples_collected[tracker_id] += 1

            if self._num_samples_collected[tracker_id] >= self._num_samples_expected:
                self._handle_end_of_analog_stream(tracker_id)
                return

    def _handle_analog_stream(self, tracker_id, index, *samples):
        if index >= self._num_samples_expected:
            # bad index, won't collect
            return

        if self._num_samples_collected[tracker_id] >= self._num_samples_expected:
            # received data after completing a collection operation
            return

        for sample in samples:
            self._diag_data[f'{self._channel.name.lower()}_data'][tracker_id].append(sampleindex=index,
                                                                                     sample=sample)
            self._num_samples_collected[tracker_id] += 1
            self._timeseries_data[tracker_id][index] = sample
            index += 1

            if self._num_samples_collected[tracker_id] >= self._num_samples_expected:
                self._handle_end_of_analog_stream(tracker_id)
                return

    def _handle_analog_window_stream(self, tracker_id, maxval, minval, capturecount):
        self._diag_data[f'{self._channel.name.lower()}window_data'][tracker_id].append(max=maxval,
                                                                                       min=minval,
                                                                                       capturecount=capturecount)
        self._window_data[self._channel] = (
            *self._adc_result_to_voltage((maxval, minval)), capturecount)
        self._handle_end_of_analog_stream(tracker_id)

    def _handle_end_of_channel_stream(self, tracker_id, channel_id):
        with self._timeoutcv:
            try:
                self._expected_channels.remove(registers.AnalogChannelSelection(channel_id))
            except KeyError:
                # got an unexpected end of stream
                return
            if self._expected_channels:
                # still expecting data for other channels, stream NOT ended
                return

        self._handle_end_of_analog_stream(tracker_id)

    def _handle_analog_channel_window_stream(self, tracker_id, channel_id, *data):
        maxval, minval, capturecount = data
        self._diag_data[f'{registers.AnalogChannelSelection(channel_id).name.lower()}'
                        f'_window_data'][tracker_id].append(max=maxval,
                                                            min=minval,
                                                            capturecount=capturecount)

        self._window_data[registers.AnalogChannelSelection(channel_id)] = (
            *self._adc_result_to_voltage((maxval, minval)), capturecount)

        self._handle_end_of_channel_stream(tracker_id, channel_id)

    def _handle_channel_error_stream(self, tracker_id, channel_id, error_value):
        chan_sel = registers.AnalogChannelSelection(channel_id)

        self._diag_data[f'{chan_sel.name.lower()}_error_data'][tracker_id].append(
            name=chan_sel.name, id=channel_id, error=error_value)

        if error_value == ErrorType.WINDOW_MEGASAMPLE_TRIGGER_ERROR:
            # we don't want to terminate the operation in case other channels
            # detect a signal. so we'll just go through the normal pipeline here
            self._window_data[chan_sel] = (0, 0, 0)
            self._handle_end_of_channel_stream(tracker_id, channel_id)
        else:
            self._error = AnalogRuntimeError(error_value, tracker_id, channel_id)
            self.stop()


class AnalogMeasurement:
    '''Provides a convenience interface for running resonance frequency measurements

    It handles the asynchronous nature of the resonance detection, and provides
    a simple blocking interface that triggers the resonance detection and waits
    for its completion.

    '''
    # Devices running FW prior to 0.104.0 won't have access to the sampling frequency API, so set a
    # default as the result of the previous calculation that used hard-coded values:
    #
    # sampling_frequency = inputclock / prescaler / (resolution + scancycles)

    RINGDOWN_SAMPLE_FREQUENCY = 42113

    def __init__(self, portname):
        self._end_of_measurement = threading.Condition()
        self._measurement_result = None
        self._detection = AnalogCollection(done_cb=self._measurement_done,
                                           error_cb=self._measurement_error)
        self._api = self._detection.setup_api(portname)

    @property
    def adc_params(self):
        '''Returns the sampling frequency from the device'''
        mcu_clock = self._api.get_register(registers.GENERAL1_MCU_CLOCK)
        if version.SemanticVersion.compare(self._api.firmware_info.api_version,
                                           version.SemanticVersion(0, 104, 0)) >= 0:
            # currently we assume that the adc_params is the same between trackers
            sampling_freq = self._api.get_register(registers.ANALOG_SAMPLE_FREQUENCY, 0)
        else:
            sampling_freq = self.RINGDOWN_SAMPLE_FREQUENCY
        return Adc(mcu_clock, sampling_freq)

    def sample(self, channel, trackers=None, **opts):
        '''Run the resonance measurement routine and return the results'''

        # Check if tracker is valid first:
        for tracker_id in trackers:
            if tracker_id not in self._api.firmware_info.active_trackers:
                raise error.CommunicationError(f'Tracker {tracker_id + 1} is not active.')

        self._detection.sample(channel, trackers, **opts)
        with self._end_of_measurement:
            self._end_of_measurement.wait()
        success, data = self._measurement_result
        if success:
            return data
        raise data

    def _measurement_done(self, results):
        with self._end_of_measurement:
            self._measurement_result = (True, results)
            self._end_of_measurement.notify()

    def _measurement_error(self, excp):
        with self._end_of_measurement:
            self._measurement_result = (False, excp)
            self._end_of_measurement.notify()
