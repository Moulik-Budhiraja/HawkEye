'''This module contains board related enums and definitions'''

import enum

from . import registers


class MCUType(enum.IntEnum):
    '''Specifies the MCU type to select the corresponding image sector'''
    STM32F446 = 1
    STM32L552 = 3


class ScanMode(enum.IntEnum):
    '''Specifies Scanner drive type'''
    UNKNOWN = 0
    PWM_STM32 = 1
    PWM_STM32_SHARED_XX = 2
    PWM_STM32_SHARED_XY = 3
    SIM = 4
    PWM_FUNDAMENTAL = 5


class BoardCategory(enum.Enum):
    '''Specifies the board's family, which is displayed to users'''
    EYETRACKER = 'Eye Tracker'
    COM = 'Communication Board'
    HUB = 'Sensor Hub'
    BOOTLOADER = 'Bootloader'


MCU_SECTOR_MAPPING = {
    MCUType.STM32F446: [(0x8000000, 0x8000FFF), (0x8020000, 0x803FFFF), (0x8040000, 0x805FFFF)],
    MCUType.STM32L552: [(0x8000000, 0x8000FFF), (0x8020000, 0x803FFFF), (0x8040000, 0x805FFFF)],
}


BOARD_PROGRAMMER_CONFIGS = {
    registers.IspBoardType.AHSM3ET: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_ahsm3_et_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_ahsm3_et_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.AHSM3_3PD: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_ahsm3_3pd_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_ahsm3_3pd_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.L5_EVK_V1: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_l5evk_v1_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_l5evk_v1_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.L5_EVK_V1_3PD: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_l5evk_v1_3pd_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_l5evk_v1_3pd_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.DEVBOARDV5: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_devboard_v5_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_devboard_v5_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.ZAPATA_V1: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_zapata_v1_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_zapata_v1_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.EVK4: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_evk4_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_evk4_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.DEVBOARDV5_ALC: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_devboard_v5_alc_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_devboard_v5_alc_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.L5_EVK_SR21: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_l5evk_sr21_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_l5evk_sr21_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.AMBON_SHIELD: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_ambon_shield_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_ambon_shield_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.L5_EVK_SR21_IRIS: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_l5evk_sr21_iris_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_l5evk_sr21_iris_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.DEVBOARDV6: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_devboard_v6_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_devboard_v6_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.INT_V1: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_int_v1_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_int_v1_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.INT_V1_IRIS: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_int_v1_iris_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_int_v1_iris_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.MERLIN22: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_merlin22_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_merlin22_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.LP_INT_V2: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_lp_int_v2_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_lp_int_v2_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.EVK4_V2: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_evk4_v2_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_evk4_v2_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.MERLIN2: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_merlin2_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_merlin2_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.HONEYCOMB_V1: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_honeycomb_v1_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_honeycomb_v1_release.hex', MCUType.STM32L552)],
    registers.IspBoardType.EVK4_WIRELESS: [
        (BoardCategory.EYETRACKER, 'ah_stm32l552_evk4_wireless_release.hex', MCUType.STM32L552),
        (BoardCategory.BOOTLOADER, 'ah_stm32l552_evk4_wireless_release.hex', MCUType.STM32L552)],
}


BOARD_SCANNER_DRIVE_CONFIG = {
    registers.IspBoardType.AHSM3ET: [ScanMode.PWM_STM32_SHARED_XX, 110000000],
    registers.IspBoardType.AHSM3_3PD: [ScanMode.PWM_STM32_SHARED_XX, 110000000],
    registers.IspBoardType.L5_EVK_V1: [ScanMode.PWM_STM32_SHARED_XX, 110000000],
    registers.IspBoardType.L5_EVK_V1_3PD: [ScanMode.PWM_STM32_SHARED_XX, 110000000],
    registers.IspBoardType.DEVBOARDV5: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.ZAPATA_V1: [ScanMode.PWM_STM32_SHARED_XX, 110000000],
    registers.IspBoardType.EVK4: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.DEVBOARDV5_ALC: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.L5_EVK_SR21: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.AMBON_SHIELD: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.L5_EVK_SR21_IRIS: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.DEVBOARDV6: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.INT_V1: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.INT_V1_IRIS: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.MERLIN22: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.LP_INT_V2: [ScanMode.PWM_FUNDAMENTAL, 110000000],
    registers.IspBoardType.EVK4_V2: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.MERLIN2: [ScanMode.PWM_STM32_SHARED_XY, 110000000],
    registers.IspBoardType.HONEYCOMB_V1: [ScanMode.PWM_FUNDAMENTAL, 110000000],
    registers.IspBoardType.EVK4_WIRELESS: [ScanMode.PWM_STM32_SHARED_XY, 110000000],

}
