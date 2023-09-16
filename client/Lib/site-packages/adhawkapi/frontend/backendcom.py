'''Module to handle communications with the backend'''

import socket
import struct
import threading
import time

from ..publicapi import PacketType, AckCodes, REQUEST_TIMEOUT


PING_INTERVAL = 2  # seconds
# if we haven't seen any data for 2 cycles, then we didn't recieve
# any ack to our ping request, and we're considered disconnected
DISCONNECT_THRESHOLD = 5.0  # seconds


class BackendStream:
    ''' Get data stream from AdHawk backend '''
    _SERVER_CONTROL_PORT = 11032
    _BUFFER_SIZE = 1024

    def __init__(self, handler):
        self._handler = handler

        self._ctrlsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._ctrlsock.bind(("127.0.0.1", 0))
        self._ctrlsock.settimeout(REQUEST_TIMEOUT)  # match backend ack timeout
        self._datasock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._datasock.bind(("127.0.0.1", 0))
        self._datasock.settimeout(0.5)

        self._last_received_time = 0
        self._connected = False

        self._shouldstop = threading.Event()
        self._ctrl_thread = threading.Thread(target=self._handle_recv_ctrl, name='frontend_ctrl')
        self._data_thread = threading.Thread(target=self._handle_recv_data, name='frontend_data')
        self._keep_alive_thread = threading.Thread(target=self._keep_alive, name='frontend_keep_alive')

    def start(self):
        '''start socket data handler and connection attempts'''
        self._ctrl_thread.start()
        self._data_thread.start()
        self._keep_alive_thread.start()

    def _disconnect(self):
        '''try to unregister as a data endpoint'''
        self.send(struct.pack('<B', PacketType.END_UDP_CONN))

    def shutdown(self):
        '''stop and join the read thread'''
        self._shouldstop.set()
        # Locally disconnect immediately instead of waiting for an ACK (which may be missed)
        # from the _disconnect() call
        self._handle_disconnect()
        self._disconnect()

    def _handle_disconnect(self):
        '''We're considered disconnected, craft an 0xc2
        response to indicate to the clients that we've disconnected.'''
        self._handle_tracker_disconnect()
        if self._connected:
            data = struct.pack('<BB', PacketType.END_UDP_CONN, 0)
            self._handler(data[0], data[1:])
            self._connected = False

    def _handle_tracker_disconnect(self):
        if self._connected:
            data = struct.pack('<BB', PacketType.TRACKER_STATUS, AckCodes.TRACKER_DISCONNECTED)
            self._handler(data[0], data[1:])

    def send(self, data):
        '''send raw data to the control port'''
        self._ctrlsock.sendto(data, ("127.0.0.1", self._SERVER_CONTROL_PORT))

    def _keep_alive(self):
        while not self._shouldstop.wait(PING_INTERVAL):
            if self._connected:
                self.send(struct.pack('<B', PacketType.PING))

    def _handle_recv_ctrl(self):
        while not self._shouldstop.is_set():
            if not self._connected:
                # send connect request if not connected
                self.send(struct.pack('<BI', PacketType.UDP_CONN, self._datasock.getsockname()[1]))

            try:
                data, _addr = self._ctrlsock.recvfrom(2048)
            except socket.timeout:
                # if we haven't seen any data for 2 cycles, then we didn't recieve
                # any ack to our ping request, and we're considered disconnected
                if time.time() - self._last_received_time > DISCONNECT_THRESHOLD:
                    self._handle_disconnect()
            except (ConnectionResetError, OSError):
                self._handle_disconnect()
            else:
                if data[0] == PacketType.END_UDP_CONN:
                    self._handle_disconnect()
                elif data[0] == PacketType.TRACKER_STATUS and data[1] == AckCodes.TRACKER_DISCONNECTED:
                    self._handle_tracker_disconnect()
                else:
                    self._connected = True
                    self._last_received_time = time.time()
                    if data[0] != PacketType.PING:
                        # Don't forward ping to the clients
                        self._handler(data[0], data[1:])

    def _handle_recv_data(self):
        while not self._shouldstop.is_set():
            try:
                data = self._datasock.recv(1024)
            except (socket.timeout, OSError):
                pass
            else:
                self._handler(data[0], data[1:])
