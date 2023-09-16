''' This module can be used to receive and process images from the AdHawk camera streamed from the AdHawk backend
 service '''

import datetime
import logging
import os
import socket
import struct
import sys
import threading
import time

import numpy as np


if sys.platform.startswith('darwin'):
    MAX_IMAGE_DGRAM = 8900
else:
    MAX_IMAGE_DGRAM = 65000
IMAGE_HEADER = 0x65
IMAGE_DATA = 0x66
N_META_BYTES = 3


class Notification:
    '''Helper class for sending notifications to other modules
    Copied from adhawktools/notification.py to make SDK release easier'''

    def __init__(self):
        self._callbacks = {}

    def add_callback(self, func, key=None):
        '''Register a new callback'''
        key = func if key is None else key
        self._callbacks[key] = func

    def remove_callback(self, func):
        '''Remove a callback if possible'''
        if func in self._callbacks:
            del self._callbacks[func]

    def _notify_callbacks(self, *args, **kwargs):
        for func in self._callbacks.copy().values():
            func(*args, **kwargs)


class RateLogger:
    ''' Helper class to measure the frequency of an event '''

    def __init__(self, interval_s=10):
        self._interval_s = interval_s
        self._start_time = 0
        self._counter = 0
        self._frequency = 0
        self._interval_start_time = 0
        self._interval_counter = 0
        self._interval_frequency = 0

    @property
    def rate(self):
        '''Return the current rate'''
        return self._interval_frequency

    @property
    def avg_rate(self):
        '''Return the total average rate'''
        return self._frequency

    @property
    def counter(self):
        '''Number of events counted'''
        return self._counter

    def count(self, incr=1):
        '''Increment the count'''
        self._counter += incr
        self._interval_counter += incr
        if self._start_time == 0:
            self._start_time = time.perf_counter()
        if self._interval_start_time == 0:
            self._interval_start_time = self._start_time
        cur_time = time.perf_counter()
        self._frequency = self._counter / (cur_time - self._start_time)
        if (cur_time - self._interval_start_time) > self._interval_s:
            self._interval_frequency = self._interval_counter / self._interval_s
            self._interval_start_time = cur_time
            self._interval_counter = 0


class FrameReceivedEvent(Notification):
    '''Event that occurs when a frame is received'''

    def notify(self,
               tracker_timestamp: float,
               frame_image_data: bytes,
               frame_timestamp: datetime.datetime):
        '''Notify callbacks'''
        self._notify_callbacks(tracker_timestamp, frame_image_data, frame_timestamp)


class VideoReceiver:
    '''
    Class to decode the image data received from the AdHawk backend service
    Args:
        new_image_callback: Callback that gets called after receiving each image packet. The callback takes
        three parameters:
        - timestamp
        - frame index
        - image buffer in jpeg format (C-ordered byte array)
    '''

    _SOCKET_TIMEOUT = 5  # seconds
    _RECV_BUFSIZE = 1048576

    frame_received_event = FrameReceivedEvent()

    def __init__(self):
        # Create a datagram socket
        self._udp_server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._udp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self._RECV_BUFSIZE)
        if os.name == 'nt':
            addr = socket.gethostbyname(socket.gethostname())
        else:
            addr = ''
        self._udp_server_socket.bind((addr, 0))
        self._udp_server_socket.settimeout(self._SOCKET_TIMEOUT)
        # setup the rate loggers
        self._frames_received = 0
        self._rate_logger = RateLogger(interval_s=1)
        self._fps_logger = RateLogger(interval_s=1)
        # create the receive thread
        self._should_stop = False
        self._receiver_thread = threading.Thread(target=self._receive)

    def start(self):
        '''start the receiving and passing images to clients'''
        self._receiver_thread.start()

    def shutdown(self):
        '''stop the thread and close the socket'''
        self._should_stop = True
        if self._receiver_thread.is_alive():
            self._receiver_thread.join()
        self._udp_server_socket.close()

    @property
    def address(self):
        '''Return the address that this receiver is listening on'''
        return self._udp_server_socket.getsockname()

    @property
    def frames_received(self):
        '''number of frames received'''
        return self._frames_received

    @property
    def bitrate(self):
        '''returns the data transfer rate (byte per second)'''
        return self._rate_logger.rate * 8

    @property
    def fps(self):
        '''returns the fps (counting only the complete images)'''
        return self._fps_logger.rate

    @property
    def avg_bitrate(self):
        '''returns the data transfer rate (byte per second)'''
        return self._rate_logger.avg_rate * 8

    @property
    def avg_fps(self):
        '''returns the fps'''
        return self._fps_logger.avg_rate

    def _receive(self):
        image_size = 0
        image_buf = None
        expected_index = 0
        current_pos = 0
        end_pos = 0
        while not self._should_stop:
            try:
                data, _addrs = self._udp_server_socket.recvfrom(MAX_IMAGE_DGRAM)
            except socket.timeout:
                self._should_stop = True
                break
            pkt_type, = struct.unpack_from('<B', data)
            if pkt_type == IMAGE_HEADER:
                try:
                    _ptype, tracker_timestamp, size, f_time = struct.unpack_from('<B3xfId', data)
                    frame_timestamp = datetime.datetime.fromtimestamp(f_time)
                except struct.error as ex:
                    logging.warning(f'Invalid image header packet: {ex}')
                    image_buf = None
                else:
                    if end_pos != image_size:
                        logging.warning(f'Incomplete frame data (got {end_pos}, expected {image_size})')
                    image_size = size
                    image_buf = np.zeros(size, dtype=np.uint8)
                    expected_index = 0
                    current_pos = 0

            elif pkt_type == IMAGE_DATA and image_buf is not None:
                self._rate_logger.count(len(data))
                try:
                    index, = struct.unpack_from('<H', data, 1)
                except struct.error:
                    logging.warning('Invalid image data packet')
                    continue

                if index != expected_index:
                    logging.warning(f'Unexpected index in image stream (got {index}, expected {expected_index})')
                    image_buf = None
                    continue

                end_pos = min(current_pos + len(data) - N_META_BYTES, image_size)
                try:
                    image_buf[current_pos:end_pos] = memoryview(data)[N_META_BYTES:]  # pylint: disable=unsupported-assignment-operation
                except ValueError:
                    # it may happen that there is a shape mismatch here sometimes because of some weired network issues
                    image_buf = None
                    continue
                expected_index += 1
                current_pos = end_pos
                if end_pos == image_size:
                    self._frames_received += 1
                    self._fps_logger.count()
                    self.frame_received_event.notify(tracker_timestamp,
                                                     image_buf.tobytes(order='C'),
                                                     frame_timestamp)
