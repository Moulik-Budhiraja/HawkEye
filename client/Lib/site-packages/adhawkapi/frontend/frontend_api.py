'''High-level module that facilitates communication with the AdHawk Backend service'''

import ctypes
import logging
import typing
import warnings

from ..publicapi import (
    AckCodes,
    APIRequestError,
    BlobType,
    CameraResolution,
    CameraUserSettings,
    EyeMask,
    EyeTrackingStreamTypes,
    FeatureStreamTypes,
    LogMode,
    MarkerSequenceMode,
    PacketType,
    ProcedureType,
    PropertyType,
    StreamControlBit,
    SystemControlType,
    SystemInfo
)
from . import handlers


class FrontendApi:
    '''This class provides the ability to:
        - Send commands to the AdHawk Backend Service
        - Register for data streams from the AdHawk Backend Service

    The control commands can be executed in blocking or non-blocking mode.
    Provide `callback=handler` as a keyword argument to the function to receive the response asynchronously.
    If the callback argument is not provided, the response is returned synchronously.

    Blocking calls must be made on the main thread. If a blocking call fails, `adhawkapi.APIRequestError` is raised.

    Sample Usage:

        import adhawkapi
        import adhawkapi.frontend
        import time

        def glint_handler(trackerid, timestamp, xpos, ypos, pd):
            print(locals())

        def handle_tracker_status_response(*response):
            if response[0] == adhawkapi.AckCodes.SUCCESS:
                tracker_status = response[1]
                print(tracker_status)
            else:
                print(adhawkapi.errormsg(response[0]))

        api = adhawkapi.frontend.FrontendApi()
        api.start()

        # Registering for data streams
        api.register_stream_handler(adhawkapi.PacketType.GLINT, glint_handler)
        api.set_stream_control(adhawkapi.PacketType.GLINT, 60)
        time.sleep(1)
        api.register_stream_handler(adhawkapi.PacketType.GLINT, None)
        api.set_stream_control(adhawkapi.PacketType.GLINT, 0)

        # Executing synchronously
        try:
            api.trigger_autotune()
        except adhawkapi.APIRequestError as exc:
            print(exc)

        # Executing asynchronously
        api.get_tracker_status(handle_tracker_status_response)

        api.shutdown()
    '''

    # pylint: disable=too-many-public-methods

    _STREAM_ENABLE_BIT_MAPPING = {
        PacketType.CALIBRATION_ERROR: StreamControlBit.CALIBRATION_ERROR,
        PacketType.PULSE: StreamControlBit.PULSE,
        PacketType.PUPIL_CENTER: StreamControlBit.PUPIL_CENTER,
        PacketType.IMU: StreamControlBit.IMU,
        PacketType.IMU_ROTATION: StreamControlBit.IMU_ROTATION,
        PacketType.MCU_TEMPERATURE: StreamControlBit.MCU_TEMPERATURE,
    }

    _LEGACY_ET_STREAM_MAP = {
        PacketType.GAZE: EyeTrackingStreamTypes.GAZE,
        PacketType.PER_EYE_GAZE: EyeTrackingStreamTypes.PER_EYE_GAZE,
        PacketType.PUPIL_POSITION: EyeTrackingStreamTypes.PUPIL_POSITION,
        PacketType.PUPIL_DIAMETER: EyeTrackingStreamTypes.PUPIL_DIAMETER,
        PacketType.GAZE_IN_IMAGE: EyeTrackingStreamTypes.GAZE_IN_IMAGE,
        PacketType.GAZE_IN_SCREEN: EyeTrackingStreamTypes.GAZE_IN_SCREEN,
    }

    _LEGACY_FEATURE_STREAM_MAP = {
        PacketType.GLINT: FeatureStreamTypes.GLINT,
        PacketType.FUSE: FeatureStreamTypes.FUSED,
        PacketType.PUPIL_ELLIPSE: FeatureStreamTypes.PUPIL_ELLIPSE,
    }

    def __init__(self, eye_mask=EyeMask.BINOCULAR, ble_device_name=None):
        '''
        Args:
            eye_mask (EyeMask): Indicates the ocular mode of the device
        '''
        self._logger = logging.getLogger(__name__)
        self._handler = handlers.PacketHandler(eye_mask, ble_device_name)
        self._stream_enable = ctypes.c_uint32(0)
        self._eye_mask = eye_mask
        self._tracker_connected = False
        self._tracker_connect_cb = lambda *args: None
        self._tracker_disconnect_cb = lambda *args: None

    @property
    def eye_mask(self):
        '''Returns the current eye mask'''
        return self._eye_mask

    @eye_mask.setter
    def eye_mask(self, eye_mask):
        '''Update the eye mask'''
        self._eye_mask = eye_mask
        self._handler.set_eye_mask(eye_mask)

    def start(self, backend_connect_cb=None, backend_disconnect_cb=None,
              tracker_connect_cb=None, tracker_disconnect_cb=None, **kwargs):
        '''Start communication with adhawk backend'''
        self._logger.info('Starting communication with backend.')
        if 'connect_cb' in kwargs:
            self._tracker_connect_cb = kwargs.get('connect_cb')
        elif tracker_connect_cb is not None:
            self._tracker_connect_cb = lambda _resultcode: tracker_connect_cb()
        if 'disconnect_cb' in kwargs:
            self._tracker_disconnect_cb = kwargs.get('disconnect_cb')
        elif tracker_disconnect_cb is not None:
            self._tracker_disconnect_cb = lambda _resultcode: tracker_disconnect_cb()

        # ignore result code in backend callbacks
        if backend_connect_cb is not None:
            self._handler.register_handler(PacketType.UDP_CONN,
                                           lambda _resultcode: backend_connect_cb())
        if backend_disconnect_cb is not None:
            self._handler.register_handler(PacketType.END_UDP_CONN,
                                           lambda _resultcode: backend_disconnect_cb())
        self._handler.register_handler(PacketType.TRACKER_STATUS, self.tracker_cb)

        return self._handler.start()

    def tracker_cb(self, resultcode):
        '''Used for tracker connect / disconnect callback'''
        if resultcode == AckCodes.TRACKER_DISCONNECTED:
            if self._tracker_disconnect_cb is not None:
                self._tracker_disconnect_cb(False)
            self._tracker_connected = False
        else:
            if not self._tracker_connected:
                if self._tracker_connect_cb is not None:
                    self._tracker_connect_cb(False)
                self._tracker_connected = True

    def shutdown(self):
        '''Stop all data streams and shutdown comms'''
        self._stream_enable = ctypes.c_uint32(0)
        return self._handler.shutdown()

    def enable_tracking(self, enable, callback=None):
        '''Enable or disable eye tracking'''
        self._handler.request(PacketType.SYSTEM_CONTROL, SystemControlType.TRACKING, enable, callback=callback)

    def register_stream_handler(self, stream_type, handler=None):
        '''Register a callback for specific stream types
        Setting the handler to None unregisters the callback for the stream
        '''
        self._handler.register_stream_handler(stream_type, handler)

    def get_tracker_status(self, callback=None):
        '''Get the status of the tracker'''
        self._handler.request(PacketType.TRACKER_STATE, callback=callback)

    def log_annotation(self, annotid, parent, name, data=None, timestamp=None, callback=None):
        '''Send a user-defind annotation to the eye tracking system

        Args:
            annotid (str): String to identify the annotation id. Can be 0 or ''
            parent (str): String to identify the parent annotation id. Can be 0 or ''

            name (str):
                A namespace-formatted, descriptive string label to describe the annotation. The names before
                the final section should be the descriptor, and the final section should be "start" or "end"
                e.g. "Test.start", "Test.end", "Test.info", "Autotune.start" "Autotune.end"
                - Must be utf-8 compatable

            data (dict, optional): json-compatable dict object that contains annotation data
            timestamp (num, optional): Manually set a timestamp for this annotation. Note that this is
                                       automatically included if left as default. Defaults to None
            callback (func(data, ), optional): Asynchronous callback handler
        '''
        self._handler.request(
            PacketType.LOG_TIMESTAMPED_ANNOTATION,
            annotid, parent, name, data, timestamp,
            callback=callback)

    def start_log_session(self, log_mode: LogMode, pre_defined_tags=None, user_defined_tags=None, callback=None):
        '''Signal backend to begin a data logging session'''
        if log_mode < LogMode.OCULAR:
            raise APIRequestError(AckCodes.INVALID_ARGUMENT)
        res = self._handler.request(
            PacketType.START_LOG_SESSION,
            log_mode, pre_defined_tags, user_defined_tags,
            callback=callback)
        return res[1] if res is not None else None

    def stop_log_session(self, callback=None):
        '''Signal backend to end a data logging session'''
        self._handler.request(PacketType.STOP_LOG_SESSION, callback=callback)

    def start_camera_capture(self, resolution_index: CameraResolution,
                             correct_distortion: bool = False,
                             callback=None):
        '''
        Signal backend to start the camera
        Args:
            resolution_index: image resolution
            correct_distortion: correct the lens distortion in the image
            callback: callback that receives the ack
        '''
        self._handler.request(PacketType.START_CAMERA, resolution_index, correct_distortion,
                              callback=callback)

    def stop_camera_capture(self, callback=None):
        '''Signal backend to stop the camera'''
        self._handler.request(PacketType.STOP_CAMERA, callback=callback)

    def start_video_stream(self, ipv4: str, port, callback=None):
        '''register the ipv4 and port to receive the video stream'''
        self._handler.request(PacketType.START_VIDEO_STREAM, ipv4, port, callback=callback)

    def stop_video_stream(self, ipv4: str, port, callback=None):
        '''unregister the ipv4 and port from receiving the video stream'''
        self._handler.request(PacketType.STOP_VIDEO_STREAM, ipv4, port, callback=callback)

    def start_calibration_gui(self, mode: MarkerSequenceMode, n_points, marker_size_mm: float, randomize: bool,
                              fov: tuple = None, callback=None):
        '''
        Signal backend to start the calibration and display the GUI
        Args:
            mode: see supported modes in MarkerSequenceMode
            n_points: number of the calibration points
            marker_size_mm: size of the aruco marker in mm
            randomize (bool): boolean specifying whether the target sequence should be shuffled
            fov (tuple): only required for fixed-gaze modes. A tuple of 4 values specifying the grid size
            (horizontal and vertical) in degrees and the  grid shift in degrees (horizontal and vertical)
            callback: callback that receives the ack
        '''
        self._handler.request(PacketType.PROCEDURE_START, ProcedureType.CALIBRATION_GUI, mode, n_points,
                              marker_size_mm, randomize, fov, callback=callback)

    def start_validation_gui(self, mode: MarkerSequenceMode, n_rows, n_columns, marker_size_mm: float, randomize,
                             fov=None, callback=None):
        '''
        Signal backend to start the validation and display the GUI
        Args:
            mode: see supported modes in MarkerSequenceMode
            n_rows: number of rows in the grid
            n_columns: number of the columns in the grid
            marker_size_mm: size of the aruco marker in mm
            randomize (bool): boolean specifying whether the target sequence should be shuffled
            fov (tuple): only required for fixed-gaze modes. A tuple of 4 values specifying the grid size
            (horizontal and vertical) in degrees and the  grid shift in degrees (horizontal and vertical)
            callback: callback that receives the ack
        '''
        self._handler.request(PacketType.PROCEDURE_START, ProcedureType.VALIDATION_GUI, mode, n_rows, n_columns,
                              marker_size_mm, randomize, fov, callback=callback)

    def quick_start_gui(self, mode: MarkerSequenceMode, marker_size_mm: float, returning_user: bool = False,
                        callback=None):
        '''
        Signal backend to display the marker sequence GUI for quickstart procedure'
        Args:
            mode: see supported modes in MarkerSequenceMode
            marker_size_mm: size of the aruco marker in mm
            returning_user (bool): indicates whether it's a returning user
            None or zero if no saved calibration blob exists.
            callback: callback that receives the ack
        '''''
        self._handler.request(PacketType.PROCEDURE_START, ProcedureType.QUICKSTART_GUI, mode, marker_size_mm,
                              returning_user, callback=callback)

    def autotune_gui(self, mode: MarkerSequenceMode, marker_size_mm: float, callback=None):
        '''
        Signal backend to display the marker sequence GUI for autotune'
        Args:
            mode: see supported modes in MarkerSequenceMode
            marker_size_mm: size of the aruco marker in mm
            callback: callback that receives the ack
        '''''
        self._handler.request(PacketType.PROCEDURE_START, ProcedureType.AUTOTUNE_GUI, mode, marker_size_mm,
                              callback=callback)

    def register_screen_board(self, screen_width: float, screen_height: float, aruco_dic: int, marker_ids: list,
                              markers: list, callback=None):
        '''
        Signal backend to define a new aruco board that defines the screen
        Args:
            screen_width (float): screen width in meters
            screen_height (float): screen height in meters
            aruco_dic (int): index of a OpenCV aruco predefined dictionary
            (https://docs.opencv.org/4.5.3/d9/d6a/group__aruco.html#gac84398a9ed9dd01306592dd616c2c975)
            marker_ids (list of integers): list of integers specifying the id of the markers
            markers (list): list containing a list of 3 floats that specify the x and y position of the bottom
            left corner of each marker in the board coordinate system and the size of the board.
            e.g. [[x1,y1,w1], [x2,y2,w2], ...]
            callback: callback that receives the ack
        '''
        self._handler.request(PacketType.REGISTER_SCREEN_BOARD, screen_width, screen_height, aruco_dic,
                              marker_ids, markers, callback=callback)

    def start_screen_tracking(self, callback=None):
        '''Signal backend to start the screen tracking '''
        self._handler.request(PacketType.START_SCREEN_TRACKING, callback=callback)

    def stop_screen_tracking(self, callback=None):
        '''Signal backend to stop the screen tracking '''
        self._handler.request(PacketType.STOP_SCREEN_TRACKING, callback=callback)

    def start_calibration(self, callback=None):
        '''Signal backend to start the calibration procedure'''
        self._handler.request(PacketType.START_CALIBRATION, callback=callback)

    def stop_calibration(self, callback=None):
        '''Signal backend to stop the calibration procedure and start calibrator'''
        self._handler.request(PacketType.STOP_CALIBRATION, callback=callback)

    def abort_calibration(self, callback=None):
        '''Signal backend to abort the calibration procedure'''
        self._handler.request(PacketType.ABORT_CALIBRATION, callback=callback)

    def register_calibration_point(self, x_pos, y_pos, z_pos, callback=None):
        '''Register a reference point to calibrate to'''
        self._handler.request(PacketType.REGISTER_CALIBRATION, x_pos, y_pos, z_pos, callback=callback)

    def load_calibration(self, cal_id, callback=None):
        '''Load a previously saved calibration

        Args:
            cal_id (int): Unique identifier specifying the calibration to load
        '''
        self._handler.request(PacketType.LOAD_BLOB, BlobType.CALIBRATION, cal_id, callback=callback)

    def save_calibration(self, callback=None):
        '''Save the current calibration data

        Returns:
            int - identifier representing the saved calibration data
        '''
        res = self._handler.request(PacketType.SAVE_BLOB, BlobType.CALIBRATION, callback=callback)
        return res[1] if res is not None else None

    def delete_calibration(self, cal_id, callback=None):
        '''Delete the current calibration data

        Args:
            cal_id (int): Unique identifier specifying the calibration to load
        '''
        self._handler.request(PacketType.DELETE_BLOB, cal_id, callback=callback)

    def start_validation(self, callback=None):
        '''Signal backend to start the validation procedure'''
        self._handler.request(PacketType.START_VALIDATION, callback=callback)

    def stop_validation(self, callback=None):
        '''Signal backend to stop the validation procedure'''
        self._handler.request(PacketType.STOP_VALIDATION, callback=callback)

    def register_validation_point(self, x_pos, y_pos, z_pos, callback=None):
        '''Register a reference point to validate to'''
        self._handler.request(PacketType.REGISTER_VALIDATION, x_pos, y_pos, z_pos, callback=callback)

    def recenter_calibration(self, x_pos, y_pos, z_pos, callback=None):
        '''Register a reference point to calibrate to'''
        self._handler.request(PacketType.RECENTER_CALIBRATION, x_pos, y_pos, z_pos, callback=callback)

    def trigger_autotune(self, args=None, callback=None):
        '''Signal to start autotune procedure with optional input parameter args containing
           a reference gaze vector [x, y, z]'''
        self._handler.request(PacketType.TRIGGER_AUTOTUNE, args, callback=callback)

    def iris_trigger_capture(self, callback=None):
        '''Signal to start autotune precedure'''
        self._handler.request(PacketType.IRIS_TRIGGER_CAPTURE, callback=callback)

    def trigger_device_calibration(self, callback=None):
        '''Signal to start the device calibration procedure'''
        self._handler.request(PacketType.PROCEDURE_START, ProcedureType.DEVICE_CALIBRATION,
                              callback=callback)

    def get_device_calibration_status(self, callback=None):
        '''Get the status of the current device calibration'''
        res = self._handler.request(PacketType.PROCEDURE_STATUS, ProcedureType.DEVICE_CALIBRATION,
                                    callback=callback)
        return res[2] if res is not None else None

    def trigger_update_firmware(self, callback=None):
        '''Signal to start the firmware update procedure'''
        self._handler.request(PacketType.PROCEDURE_START, ProcedureType.UPDATE_FIRMWARE,
                              callback=callback)

    def get_update_firmware_status(self, callback=None):
        '''Get the status of the current firmware update'''
        res = self._handler.request(PacketType.PROCEDURE_STATUS, ProcedureType.UPDATE_FIRMWARE,
                                    callback=callback)
        return res[2] if res is not None else None

    def request_system_info(self, system_info_index, callback=None):
        '''Read system information from backend'''
        return self._handler.request(PacketType.REQUEST_SYSTEM_INFO, system_info_index, callback=callback)

    def request_backend_version(self, callback=None):
        '''Request the current version of AdHawk Backend'''
        return self._handler.request(PacketType.REQUEST_BACKEND_VERSION, callback=callback)

    def request_multi_system_info(self, *multi_args, callback=None):
        '''Read a system info request from backend with multiple system info types in a single packet'''
        return self._handler.request(
            PacketType.REQUEST_SYSTEM_INFO, SystemInfo.MULTI_INFO, *multi_args, callback=callback)

    def set_component_offsets(self, right_x, right_y, right_z, left_x, left_y, left_z, callback=None):
        '''Set the scanner/detector component offsets from nominal '''
        self._handler.request(
            PacketType.PROPERTY_SET, PropertyType.COMPONENT_OFFSETS,
            right_x, right_y, right_z, left_x, left_y, left_z,
            callback=callback)

    def get_component_offsets(self, callback=None):
        '''Returns the scanner/detector component offsets from nominal'''
        res = self._handler.request(
            PacketType.PROPERTY_GET, PropertyType.COMPONENT_OFFSETS,
            callback=callback)
        return res[2:] if res is not None else None

    def set_stream_control(self, stream_types, stream_rate, callback=None):
        '''Sets the stream rate for the specified streams. Setting the stream rate to 0 Hz disables the stream'''
        stream_types = stream_types if isinstance(stream_types, typing.Iterable) else [stream_types]

        unsupported_streams = [stream_type
                               for stream_type in stream_types
                               if stream_type not in self._STREAM_ENABLE_BIT_MAPPING]
        if unsupported_streams:
            et_streams = [stream_type for stream_type in unsupported_streams
                          if stream_type in self._LEGACY_ET_STREAM_MAP]
            if et_streams:
                self._logger.warning(f'Using deprecated ET streams {et_streams}, use new et stream control'
                                     ' rates may not work as expected. Callback may return unexpected results'
                                     'get_stream_control will not show the streams enabled')
                mapped = [self._LEGACY_ET_STREAM_MAP[stream_type] for stream_type in et_streams]
                self.set_et_stream_control(mapped, stream_rate > 0, callback=callback)
                for stream_type in et_streams:
                    unsupported_streams.remove(stream_type)
                    stream_types.remove(stream_type)

            feature_streams = [stream_type for stream_type in unsupported_streams
                               if stream_type in self._LEGACY_FEATURE_STREAM_MAP]
            if feature_streams:
                self._logger.warning(f'Using deprecated Feature streams {feature_streams},'
                                     ' use new feature stream control'
                                     ' rates may not work as expected. Callback may return unexpected results'
                                     'get_stream_control will not show the streams enabled')
                mapped = [self._LEGACY_FEATURE_STREAM_MAP[stream_type] for stream_type in feature_streams]
                self.set_feature_stream_control(mapped, stream_rate > 0, callback=callback)
                for stream_type in feature_streams:
                    unsupported_streams.remove(stream_type)
                    stream_types.remove(stream_type)
            if unsupported_streams:
                raise APIRequestError(AckCodes.NOT_SUPPORTED, f'Unsupported streams: {unsupported_streams}')

        if not stream_types:
            return

        stream_bits = 0
        for stream_type in stream_types:
            stream_bits |= self._STREAM_ENABLE_BIT_MAPPING[stream_type]
        self._handler.request(
            PacketType.PROPERTY_SET, PropertyType.STREAM_CONTROL,
            stream_bits, stream_rate,
            callback=callback)

    def set_et_stream_control(self, stream_types, enable, callback=None):
        '''Enables or disables the specified streams'''
        stream_types = stream_types if isinstance(stream_types, typing.Iterable) else [stream_types]

        unsupported_streams = [stream_type
                               for stream_type in stream_types
                               if stream_type not in EyeTrackingStreamTypes]
        if unsupported_streams:
            raise APIRequestError(AckCodes.NOT_SUPPORTED, f'Unsupported streams: {unsupported_streams}')

        stream_bits = 0
        for stream_type in stream_types:
            stream_bits |= 1 << stream_type
        self._handler.request(
            PacketType.PROPERTY_SET, PropertyType.EYETRACKING_STREAMS,
            stream_bits, enable, callback=callback)

    def get_et_stream_control(self, callback=None):
        '''Get the global eyetracking stream control mask'''
        res = self._handler.request(PacketType.PROPERTY_GET, PropertyType.EYETRACKING_STREAMS,
                                    callback=callback)
        return res[2] if res is not None else None

    def set_feature_stream_control(self, stream_types, enable, callback=None):
        '''Enables or disables the specified streams'''
        stream_types = stream_types if isinstance(stream_types, typing.Iterable) else [stream_types]

        unsupported_streams = [stream_type
                               for stream_type in stream_types
                               if stream_type not in FeatureStreamTypes]
        if unsupported_streams:
            raise APIRequestError(AckCodes.NOT_SUPPORTED, f'Unsupported streams: {unsupported_streams}')

        stream_bits = 0
        for stream_type in stream_types:
            stream_bits |= 1 << stream_type
        self._handler.request(
            PacketType.PROPERTY_SET, PropertyType.FEATURE_STREAMS,
            stream_bits, enable, callback=callback)

    def get_feature_stream_control(self, callback=None):
        '''Get the global feature stream control mask'''
        res = self._handler.request(PacketType.PROPERTY_GET, PropertyType.FEATURE_STREAMS,
                                    callback=callback)
        return res[2] if res is not None else None

    def set_et_stream_rate(self, et_stream_rate, callback=None):
        '''Sets the global eyetracking rate'''
        self._handler.request(
            PacketType.PROPERTY_SET, PropertyType.EYETRACKING_RATE,
            et_stream_rate, callback=callback)

    def get_et_stream_rate(self, callback=None):
        '''Get the global eye tracking rate'''
        res = self._handler.request(PacketType.PROPERTY_GET, PropertyType.EYETRACKING_RATE,
                                    callback=callback)
        return res[2] if res is not None else None

    def get_stream_control(self, stream_type, callback=None):
        '''Get the stream rate for a single stream. 0 Hz means the stream is disabled'''
        if stream_type in self._LEGACY_ET_STREAM_MAP:
            self._logger.warning(
                f'Deprecated use of get_stream_control use et stream control for {stream_type}')
            et_rate = self.get_et_stream_rate()
            et_mask = self.get_et_stream_control()
            if et_rate is not None and et_mask is not None:
                ctl_bit = 1 << self._LEGACY_ET_STREAM_MAP[stream_type]
                return et_rate if et_mask & ctl_bit else 0
            return None
        if stream_type in self._LEGACY_FEATURE_STREAM_MAP:
            self._logger.warning(
                f'Deprecated use of get_stream_control use feature stream control for {stream_type}')
            et_rate = self.get_et_stream_rate()
            feature_mask = self.get_feature_stream_control()
            if et_rate is not None and feature_mask is not None:
                ctl_bit = 1 << self._LEGACY_FEATURE_STREAM_MAP[stream_type]
                return et_rate if feature_mask & ctl_bit else 0
            return None
        if stream_type not in self._STREAM_ENABLE_BIT_MAPPING:
            raise ValueError(f'Invalid stream type {stream_type}')

        stream_bit = self._STREAM_ENABLE_BIT_MAPPING[stream_type]
        res = self._handler.request(
            PacketType.PROPERTY_GET, PropertyType.STREAM_CONTROL, stream_bit,
            callback=callback)
        return res[2] if res is not None else None

    def set_event_control(self, event_control_bit, enabled, callback=None):
        '''Enables or disables an event'''
        self._handler.request(
            PacketType.PROPERTY_SET, PropertyType.EVENT_CONTROL,
            event_control_bit, enabled,
            callback=callback)

    def get_event_control(self, event_control_bit, callback=None):
        '''Check if the event is enabled or disabled'''
        res = self._handler.request(
            PacketType.PROPERTY_GET, PropertyType.EVENT_CONTROL, event_control_bit,
            callback=callback)
        return res[2] if res is not None else None

    def get_normalized_eye_offsets(self, callback=None):
        '''Returns the estimated eye offsets as measured from the nominal eye'''
        res = self._handler.request(
            PacketType.PROPERTY_GET, PropertyType.NORMALIZED_EYE_OFFSETS,
            callback=callback)
        return res[2:] if res is not None else None

    def get_nominal_eye_offsets(self, callback=None):
        '''Returns the estimated eye offsets as measured from the nominal eye'''
        res = self._handler.request(
            PacketType.PROPERTY_GET, PropertyType.NOMINAL_EYE_OFFSETS,
            callback=callback)
        return res[2:] if res is not None else None

    @staticmethod
    def set_ipd(ipd, callback=None):
        '''(Deprecated) Set the interpupillary distance'''
        del ipd
        del callback
        warnings.warn('set_ipd() has been deprecated.', DeprecationWarning)
        raise APIRequestError(AckCodes.NOT_SUPPORTED)

    @staticmethod
    def get_ipd(callback=None):
        '''(Deprecated) Get the interpupillary distance'''
        del callback
        warnings.warn('get_ipd() has been deprecated.', DeprecationWarning)
        raise APIRequestError(AckCodes.NOT_SUPPORTED)

    def set_camera_user_settings(self, camera_user_setting: CameraUserSettings, value, callback=None):
        ''' Set a camera user setting '''
        self._handler.request(
            PacketType.CAMERA_USER_SETTINGS_SET, camera_user_setting, value, callback=callback)
