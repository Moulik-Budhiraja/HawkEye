'''Contains handlers for frontend requests and responses'''

import collections
import logging
import threading
import numpy as np

from . import backendcom, blecom
from .decoders import decode
from .encoders import encode


try:
    from .. import internal
except ImportError:
    internal = None
from .. import publicapi


class PacketHandler:
    '''Class that wraps the comm layer and handles encoding and decoding requests and responses
    '''

    _ET_TYPE_MAPPINGS = {
        publicapi.EyeTrackingStreamTypes.GAZE: publicapi.PacketType.GAZE,
        publicapi.EyeTrackingStreamTypes.PER_EYE_GAZE: publicapi.PacketType.PER_EYE_GAZE,
        publicapi.EyeTrackingStreamTypes.PUPIL_POSITION: publicapi.PacketType.PUPIL_POSITION,
        publicapi.EyeTrackingStreamTypes.PUPIL_DIAMETER: publicapi.PacketType.PUPIL_DIAMETER,
        publicapi.EyeTrackingStreamTypes.GAZE_IN_IMAGE: publicapi.PacketType.GAZE_IN_IMAGE,
        publicapi.EyeTrackingStreamTypes.GAZE_IN_SCREEN: publicapi.PacketType.GAZE_IN_SCREEN,
    }

    _OLD_ET_MAPPINGS = {v: k for k, v in _ET_TYPE_MAPPINGS.items()}

    _FEATURE_TYPE_MAPPINGS = {
        publicapi.FeatureStreamTypes.GLINT: publicapi.PacketType.GLINT,
        publicapi.FeatureStreamTypes.FUSED: publicapi.PacketType.FUSE,
        publicapi.FeatureStreamTypes.PUPIL_ELLIPSE: publicapi.PacketType.PUPIL_ELLIPSE,
    }

    _OLD_FEATURE_MAPPINGS = {v: k for k, v in _FEATURE_TYPE_MAPPINGS.items()}

    def __init__(self, eye_mask, ble_device_name=None):
        self._logger = logging.getLogger(__name__)
        self._pending_requests = collections.defaultdict(collections.deque)
        self._registered_handlers = collections.defaultdict(list)
        self._rx_cv = threading.Condition()
        self._responses = collections.deque()
        self._com = None
        self._eye_mask = eye_mask
        self._ble_device_name = ble_device_name

    def set_eye_mask(self, eye_mask):
        '''Set the current eye mask'''
        self._eye_mask = eye_mask

    def start(self):
        '''Start communication with AdHawk service'''
        if self._ble_device_name:
            self._com = blecom.BLECom(self._ble_device_name, self._handle_packet)
        else:
            self._com = backendcom.BackendStream(self._handle_packet)
        self._com.start()

    def shutdown(self):
        '''Stop all data streams and shutdown comms'''
        if self._com is not None:
            self._com.shutdown()
            self._com = None

    def request(self, packet_type, *args, callback=None, **kwargs):
        '''Send a request to backend given a packet type and the arguments'''

        self._logger.debug(f'[tx] {repr(packet_type)}: {args}')
        # setup sync or async callbacks
        if callback is None:
            self._pending_requests[packet_type].append(self._blocking_handler)
        else:
            self._pending_requests[packet_type].append(callback)

        # encode and send the message
        message = encode(packet_type, *args, *kwargs)
        self._com.send(message)

        # wait on response if required
        if callback:
            return None
        with self._rx_cv:
            self._logger.debug('Waiting for response...')
            self._rx_cv.wait(publicapi.REQUEST_TIMEOUT + 1)
            try:
                response = self._responses.pop()
                if response[0] != publicapi.AckCodes.SUCCESS:
                    raise publicapi.APIRequestError(response[0])
                return response
            except IndexError:
                raise publicapi.APIRequestError(publicapi.AckCodes.REQUEST_TIMEOUT)

    def register_stream_handler(self, packet_type, handler=None):
        '''Add a listener for a particular packet type'''
        if not packet_type.is_stream():
            # Ensure we only register or unregister stream packets
            # All other packets are automatically registered through
            # the api callback parameter
            return
        self.register_handler(packet_type, handler)

    def register_handler(self, packet_type, handler=None):
        '''Add a listener for a particular packet type'''
        if packet_type in self._OLD_ET_MAPPINGS:
            self._logger.warning(f'Deprecated stream type {packet_type}, use et stream handler')
        if packet_type in self._OLD_FEATURE_MAPPINGS:
            self._logger.warning(f'Deprecated stream type {packet_type}, use feature stream handler')

        if handler:
            self._registered_handlers[packet_type].append(handler)
        else:
            if packet_type in self._registered_handlers:
                self._registered_handlers.pop(packet_type)

    def _blocking_handler(self, *args):
        '''Provides a handler that wakes up all threads waiting for a specific response'''
        with self._rx_cv:
            self._responses.append(args)
            self._rx_cv.notify()

    def _handle_et_data(self, et_data: publicapi.EyeTrackingStreamData):  # pylint: disable=too-many-branches
        ''' backwards compatibility for old streams '''
        # gaze
        if et_data.gaze is not None:
            if np.all(np.isfinite(et_data.gaze)):
                handlers = self._registered_handlers[publicapi.PacketType.GAZE]
                if handlers:
                    for handler in handlers:
                        handler(et_data.timestamp, *et_data.gaze)
        if et_data.per_eye_gaze is not None:
            if np.any(np.isfinite(et_data.per_eye_gaze)):
                handlers = self._registered_handlers[publicapi.PacketType.PER_EYE_GAZE]
                if handlers:
                    for handler in handlers:
                        handler(et_data.timestamp, *et_data.per_eye_gaze)
        if et_data.pupil_pos is not None:
            if np.any(np.isfinite(et_data.pupil_pos)):
                handlers = self._registered_handlers[publicapi.PacketType.PUPIL_POSITION]
                if handlers:
                    for handler in handlers:
                        handler(et_data.timestamp, *et_data.pupil_pos)
        if et_data.pupil_diameter is not None:
            if np.any(np.isfinite(et_data.pupil_diameter)):
                handlers = self._registered_handlers[publicapi.PacketType.PUPIL_DIAMETER]
                if handlers:
                    for handler in handlers:
                        handler(et_data.timestamp, *et_data.pupil_diameter)
        if et_data.gaze_in_image is not None:
            if np.all(np.isfinite(et_data.gaze_in_image)):
                handlers = self._registered_handlers[publicapi.PacketType.GAZE_IN_IMAGE]
                if handlers:
                    for handler in handlers:
                        handler(et_data.timestamp, *et_data.gaze_in_image)
        if et_data.gaze_in_screen is not None:
            if np.all(np.isfinite(et_data.gaze_in_screen)):
                handlers = self._registered_handlers[publicapi.PacketType.GAZE_IN_SCREEN]
                if handlers:
                    for handler in handlers:
                        handler(et_data.timestamp, *et_data.gaze_in_screen)

    def _handle_feature_data(self, feature_data: publicapi.FeatureStreamData):  # pylint: disable=too-many-branches
        ''' backwards compatibility for old streams '''
        if feature_data.glints is not None:
            for glint in feature_data.glints:
                if np.all(np.isfinite(glint)):
                    handlers = self._registered_handlers[publicapi.PacketType.GLINT]
                    if handlers:
                        for handler in handlers:
                            pd_index, xvec, yvec = glint
                            handler(feature_data.tracker_id, feature_data.timestamp, xvec, yvec, pd_index)
        if feature_data.fused is not None:
            if np.all(np.isfinite(feature_data.fused)):
                handlers = self._registered_handlers[publicapi.PacketType.FUSE]
                if handlers:
                    for handler in handlers:
                        handler(feature_data.tracker_id, feature_data.timestamp, *feature_data.fused)
        if feature_data.ellipse is not None:
            if np.all(np.isfinite(feature_data.ellipse)):
                handlers = self._registered_handlers[publicapi.PacketType.PUPIL_ELLIPSE]
                if handlers:
                    for handler in handlers:
                        handler(feature_data.tracker_id, feature_data.timestamp, *feature_data.ellipse)

    def _handle_packet(self, packet_type_int, data):  # pylint: disable=too-many-branches
        '''Determines the packet type and decodes it'''
        try:
            try:
                packet_type = publicapi.PacketType(packet_type_int)
            except ValueError:
                if internal is None:
                    raise
                packet_type = internal.PacketType(packet_type_int)
        except ValueError:
            self._logger.warning(f'Unrecognized packet: {hex(packet_type_int)}')
            return

        decoded = decode(packet_type, data, self._eye_mask)
        if decoded is None:
            return

        if packet_type == publicapi.PacketType.EYETRACKING_STREAM:
            self._handle_et_data(decoded)
            decoded = [decoded]
        if packet_type == publicapi.PacketType.FEATURE_STREAM:  # pylint: disable=too-many-nested-blocks
            self._handle_feature_data(decoded)
            decoded = [decoded]

        # handle udp comm packets and any registered stream handlers first
        handlers = self._registered_handlers[packet_type]
        if handlers:
            for handler in handlers:
                handler(*decoded)
            return

        # if no handler for udp comm packets, return without warning
        if packet_type in (publicapi.PacketType.UDP_CONN, publicapi.PacketType.END_UDP_CONN):
            return

        if not packet_type.is_stream():
            # Checking pending requests
            self._logger.debug(f'[rx] {repr(packet_type)} {decoded}')
            try:
                # responses from backend are for the most part strictly ordered
                # there are a few packets types that are handled prior to streaming
                # therefore we key on the packet type and then pop the requests
                # off the queue
                handler = self._pending_requests[packet_type].popleft()
            except IndexError:
                self._logger.warning(f'Received unexpected packet: {repr(packet_type)}')
            else:
                handler(*decoded)
