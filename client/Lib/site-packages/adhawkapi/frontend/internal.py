'''This module provides the ability to issue internal commands to the AdHawk Backend Service'''

from . import handlers
from .. import internal
from .. import publicapi


class InternalApi:
    '''This class provides the ability to:
        - Send internal commands to the AdHawk Backend Service
        - Register for internal data streams from the AdHawk Backend Service

    The control commands can be executed in blocking or non-blocking mode.
    Provide `callback=handler` as a keyword argument to the function to receive the response asynchronously.
    If the callback argument is not provided, the response is returned synchronously.

    Blocking calls must be made on the main thread. If a blocking call fails, `adhawkapi.APIRequestError` is raised.

    Sample Usage:
        import adhawkapi
        import adhawkapi.frontend.internal as internal

        api = internal.InternalApi()
        api.start()
        api.configure_pulse_stream(True, True)
        api.shutdown()
    '''

    # pylint: disable=too-many-public-methods

    def __init__(self, eye_mask=publicapi.EyeMask.BINOCULAR):
        '''
        Args:
            eye_mask (EyeMask): Indicates the ocular mode of the device
        '''
        self._handler = handlers.PacketHandler(eye_mask)
        self._eye_mask = eye_mask

    @property
    def eye_mask(self):
        '''Returns the current eye mask'''
        return self._eye_mask

    @eye_mask.setter
    def eye_mask(self, eye_mask):
        '''Update the eye mask'''
        self._eye_mask = eye_mask
        self._handler.set_eye_mask(eye_mask)

    def start(self):
        '''Start communication with adhawk backend'''
        return self._handler.start()

    def shutdown(self):
        '''Stop all data streams and shutdown comms'''
        return self._handler.shutdown()

    def register_stream_handler(self, stream_type, handler=None):
        '''Register a callback for specific stream types
        Setting the handler to None unregisters the callback for the stream
        '''
        self._handler.register_stream_handler(stream_type, handler)

    def trigger_autophase(self, callback=None):
        '''Signal to reset and calculate autophase'''
        return self._handler.request(internal.PacketType.CONTROL, internal.ControlType.AUTOPHASE, callback=callback)

    def trigger_stop(self, callback=None):
        '''Signal to stop backend services'''
        return self._handler.request(internal.PacketType.CONTROL, internal.ControlType.STOP, callback=callback)

    def trigger_start(self, callback=None):
        '''Signal to start backend services'''
        return self._handler.request(internal.PacketType.CONTROL, internal.ControlType.START, callback=callback)

    def trigger_reload(self, callback=None):
        '''Signal to reload services'''
        return self._handler.request(internal.PacketType.CONTROL, internal.ControlType.RELOAD, callback=callback)

    def configure_pulse_stream(self, full_rate: bool, unfilter: bool, callback=None):
        '''Modify properties of the pulse stream'''
        return self._handler.request(
            internal.PacketType.CONTROL,
            internal.ControlType.PULSE_STREAM_CONFIG,
            full_rate, unfilter,
            callback=callback)

    def enable_embedded_info(self, rate, callback=None):
        '''Enable the embedded info stream'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_SET,
            publicapi.PropertyType.STREAM_CONTROL,
            publicapi.StreamControlBit.EMBEDDED_INFO,
            rate,
            callback=callback)

    def get_autotune_phys_model_residuals(self, callback=None):
        '''Returns the phys model residuals calculated during last autotune'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_GET, internal.PropertyType.AUTOTUNE_PHYS_MODEL_RESIDUALS,
            callback=callback)

    def set_scan_region(self, eye_idx, xmean, ymean, width, height, callback=None):
        '''Set the scan position'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_SET, internal.PropertyType.SCAN_REGION, eye_idx, xmean, ymean, width, height,
            callback=callback)

    def get_scan_region(self, eye_idx, callback=None):
        '''Get the scan position'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_GET, internal.PropertyType.SCAN_REGION, eye_idx, callback=callback)

    def set_scan_power(self, eye_idx, laser_pct, callback=None):
        '''Set the scan power'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_SET, internal.PropertyType.SCAN_POWER, eye_idx, laser_pct, callback=callback)

    def get_scan_power(self, eye_idx, callback=None):
        '''Get the scan power'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_GET, internal.PropertyType.SCAN_POWER, eye_idx, callback=callback)

    def set_detector_sensitivity(self, eye_idx, detector_type, detector_id, sensitivity, callback=None):
        '''Set the scan power'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_SET, internal.PropertyType.DETECTOR_SENSITIVITY, eye_idx, detector_type,
            detector_id, sensitivity, callback=callback)

    def get_detector_sensitivity(self, eye_idx, detector_type, detector_id, callback=None):
        '''Get the scan power'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_GET, internal.PropertyType.DETECTOR_SENSITIVITY, eye_idx, detector_type,
            detector_id, callback=callback)

    def set_pupil_offset(self, pupil_offset, callback=None):
        '''Set the pupil offset'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_SET, internal.PropertyType.PUPIL_OFFSET, pupil_offset, callback=callback)

    def get_pupil_offset(self, callback=None):
        '''Set the pupil offset'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_GET, internal.PropertyType.PUPIL_OFFSET, callback=callback)

    def set_log_mode(self, log_mode, callback=None):
        '''Set log mode'''
        return self._handler.request(
            internal.PacketType.CONTROL, internal.ControlType.LOG_MODE, log_mode, callback=callback)

    def set_scanbox(self, box_type: internal.ScanboxType, callback=None):
        '''Set scanbox'''
        return self._handler.request(
            internal.PacketType.CONTROL, internal.ControlType.SCANBOX, box_type, callback=callback)

    def set_algorithm_pipeline(self, algorithm_pipeline, callback=None):
        '''Set algorithm pipeline'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_SET, internal.PropertyType.ALGORITHM_PIPELINE, algorithm_pipeline,
            callback=callback)

    def get_algorithm_pipeline(self, callback=None):
        '''Get algorithm pipeline'''
        return self._handler.request(
            publicapi.PacketType.PROPERTY_GET, internal.PropertyType.ALGORITHM_PIPELINE,  callback=callback)
