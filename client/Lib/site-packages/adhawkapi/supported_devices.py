'''This module lists the supported AdHawk devices'''

# List of supported devices (USB vendor id, USB device id)
BASE_DEVICES = [(0x03eb, 0x2404, ''),
                (0x03ec, 0x2404, ''),
                (0x03ed, 0x2404, ''),
                (0x32bc, 0x0110, ''),  # single-mcu-v1
                (0x32bc, 0x0111, ''),  # single-mcu-3pd
                (0x32bc, 0x0202, ''),  # L5-dev-shield-v1
                (0x32bc, 0x0204, ''),  # dev-board-v4
                (0x32bc, 0x0301, ''),  # AHSM3-ET
                (0x32bc, 0x0302, ''),  # AHSM3-spi-adapter
                (0x32bc, 0x0112, ''),  # L5-evk-v1
                (0x32bc, 0x0205, ''),  # dev-board-v5
                (0x32bc, 0x0303, ''),  # zapata_v1
                (0x32bc, 0x0113, ''),  # EVK4
                (0x32bc, 0x0114, ''),  # evk4 wireless
                (0x32bc, 0x0304, ''),  # ambon_shield
                (0x32bc, 0x0207, ''),  # dev-board-v6
                (0x32bc, 0x0305, ''),  # integration_board_v1
                (0x32bc, 0x0306, ''),  # merlin22 and merlin2
                (0x32bc, 0x0307, ''),  # low_power_integration_board_v1
                (0x32bc, 0x0701, ''),  # esp32s3
                (0x32bc, 0x0208, '')]  # honeycomb_v1

SUPPORTED_DEVICES = BASE_DEVICES + [(vend_id, prod_id | 0x8000, '') for vend_id, prod_id, _ in BASE_DEVICES]

# List of supported embedded host devices (USB vendor id, USB device id)
EMBEDDED_HUB_DEVICE = (0x0424, 0x03803, '')
