import adhawkapi
import adhawkapi.frontend
import math
import time

class FrontendData:
    ''' BLE Frontend '''

    def __init__(self, to_speak, is_mic_on):
        # Instantiate an API object
        # TODO: Update the device name to match your device
        self._api = adhawkapi.frontend.FrontendApi(ble_device_name='ADHAWK MINDLINK-275')

        self.to_speak = to_speak
        self.is_mic_on = is_mic_on

        # Tell the api that we wish to receive eye tracking data stream
        # with self._handle_et_data as the handler
        self._api.register_stream_handler(adhawkapi.PacketType.EYETRACKING_STREAM, self._handle_et_data)

        self._api.register_stream_handler(adhawkapi.PacketType.EVENTS, self._handle_events)

        # Start the api and set its connection callback to self._handle_tracker_connect/disconnect.
        # When the api detects a connection to a MindLink, this function will be run.
        self._api.start(tracker_connect_cb=self._handle_tracker_connect,
                        tracker_disconnect_cb=self._handle_tracker_disconnect)
        
        self.current_gaze = (0, 0, 0, 0)

        self.last_blink = 0

    def shutdown(self):
        '''Shutdown the api and terminate the bluetooth connection'''
        self._api.shutdown()

    def _handle_et_data(self, et_data: adhawkapi.EyeTrackingStreamData):
        ''' Handles the latest et data '''
        if et_data.gaze is not None:
            xvec, yvec, zvec, vergence = et_data.gaze
            self.current_gaze = [i if not math.isnan(i) else 0 for i in (xvec, yvec, zvec, vergence)]
            # print(f'Gaze={xvec:.2f},y={yvec:.2f},z={zvec:.2f},vergence={vergence:.2f}')



    def _handle_events(self, event_type, timestamp, *args):
        if event_type == adhawkapi.Events.BLINK:
            duration = args[0]
            
            if time.time() - self.last_blink < 0.5:
                print("Double blink")
                self.is_mic_on.value = not self.is_mic_on.value
                self.to_speak.value = "Mic on" if self.is_mic_on.value else "Mic off"
            else: 
                self.last_blink = time.time()





    def _handle_tracker_connect(self):
        print("Tracker connected")
        self._api.set_et_stream_rate(60, callback=lambda *args: None)

        self._api.set_et_stream_control([
            adhawkapi.EyeTrackingStreamTypes.GAZE,
            adhawkapi.EyeTrackingStreamTypes.EYE_CENTER,
            adhawkapi.EyeTrackingStreamTypes.PUPIL_DIAMETER,
            adhawkapi.EyeTrackingStreamTypes.IMU_QUATERNION,
        ], True, callback=lambda *args: None)

        self._api.set_event_control(adhawkapi.EventControlBit.BLINK, 1, callback=lambda *args: None)
        self._api.set_event_control(adhawkapi.EventControlBit.EYE_CLOSE_OPEN, 1, callback=lambda *args: None)

    def _handle_tracker_disconnect(self):
        print("Tracker disconnected")