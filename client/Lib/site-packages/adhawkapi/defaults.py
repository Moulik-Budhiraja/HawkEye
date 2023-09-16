'''This module provides global defaults
Ideally these should exist only in the relevant module, but there are lots of
code duplication, which leads to these constants being used by multiple modules.
Once we do some refactoring, the file should be eliminated.
'''

MAX_EYES = 2
# Max scanner corresponds to the number of AdHawk's MEMS scanner module
MAX_SCANNERS = 2
# Max tracker refers to the number of pulse detection modules
LIMIT_MAX_TRACKERS = 4
# Max devices refers to the number of addressable devices in the system
LIMIT_MAX_DEVICES = 5
CONTROL_DEV_ID = 0x0F
HOST_DEV_ID = 0x0E

N_PHOTODIODES = 6
MAX_PUPIL_DETECTORS = 2
MAX_SHARED_DETECTORS = 3

BLOB_CHUNK_LEN = 25

LIMIT_X_MIN = 0
LIMIT_X_MAX = 1023

LIMIT_Y_MIN = 0
LIMIT_Y_MAX = 1023

LIMIT_MAX_LASER_CURRENT_SCALE = 45.5
LIMIT_MAX_LASER_CURRENT = 45.5

# Units of Modulation Freq are in MHz
LIMIT_MIN_MODULATION_FREQ = 1
LIMIT_MAX_MODULATION_FREQ = 10

# Units of Duty Cycle are in %
LIMIT_MAX_DUTYCYCLE = 100

LIMIT_MAX_THRESHOLD = 3.3

LIMIT_MIN_FREQ = 1000
LIMIT_MAX_FREQ = 10000

LIMIT_MAX_DAC_PHASE = 4095

DEFAULT_X_MIN = 0
DEFAULT_X_MAX = 1023
DEFAULT_X_STEP = 20
DEFAULT_FREQUENCY = 3800
DEFAULT_Y_MIN = 0
DEFAULT_Y_MAX = 1023
DEFAULT_Y_STEP = 10
DEFAULT_DWELL = 5

DEFAULT_PD_GAIN_MIN = 0
DEFAULT_PD_GAIN_MAX = 25

SIM_SERIAL_NUM = ""

DEFAULT_RATE = 125
DEFAULT_PULSE_RATE = 250

# number of terms for the autotune-invariant modulecal polynomial
MODULE_CAL_NUM_TERMS = 12
