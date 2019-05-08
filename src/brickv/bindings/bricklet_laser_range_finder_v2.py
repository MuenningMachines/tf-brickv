# -*- coding: utf-8 -*-
#############################################################
# This file was automatically generated on 2019-05-07.      #
#                                                           #
# Python Bindings Version 2.1.21                            #
#                                                           #
# If you have a bugfix for this file and want to commit it, #
# please fix the bug in the generator. You can find a link  #
# to the generators git repository on tinkerforge.com       #
#############################################################

#### __DEVICE_IS_NOT_RELEASED__ ####

from collections import namedtuple

try:
    from .ip_connection import Device, IPConnection, Error, create_char, create_char_list, create_string, create_chunk_data
except ValueError:
    from ip_connection import Device, IPConnection, Error, create_char, create_char_list, create_string, create_chunk_data

GetDistanceCallbackConfiguration = namedtuple('DistanceCallbackConfiguration', ['period', 'value_has_to_change', 'option', 'min', 'max'])
GetVelocityCallbackConfiguration = namedtuple('VelocityCallbackConfiguration', ['period', 'value_has_to_change', 'option', 'min', 'max'])
GetConfiguration = namedtuple('Configuration', ['acquisition_count', 'enable_quick_termination', 'threshold_value', 'measurement_frequency'])
GetMovingAverage = namedtuple('MovingAverage', ['distance_average_length', 'velocity_average_length'])
GetSPITFPErrorCount = namedtuple('SPITFPErrorCount', ['error_count_ack_checksum', 'error_count_message_checksum', 'error_count_frame', 'error_count_overflow'])
GetIdentity = namedtuple('Identity', ['uid', 'connected_uid', 'position', 'hardware_version', 'firmware_version', 'device_identifier'])

class BrickletLaserRangeFinderV2(Device):
    """
    Measures distance up to 40m with laser light
    """

    DEVICE_IDENTIFIER = 2144
    DEVICE_DISPLAY_NAME = 'Laser Range Finder Bricklet 2.0'
    DEVICE_URL_PART = 'laser_range_finder_v2' # internal

    CALLBACK_DISTANCE = 4
    CALLBACK_VELOCITY = 8


    FUNCTION_GET_DISTANCE = 1
    FUNCTION_SET_DISTANCE_CALLBACK_CONFIGURATION = 2
    FUNCTION_GET_DISTANCE_CALLBACK_CONFIGURATION = 3
    FUNCTION_GET_VELOCITY = 5
    FUNCTION_SET_VELOCITY_CALLBACK_CONFIGURATION = 6
    FUNCTION_GET_VELOCITY_CALLBACK_CONFIGURATION = 7
    FUNCTION_SET_ENABLE = 9
    FUNCTION_GET_ENABLE = 10
    FUNCTION_SET_CONFIGURATION = 11
    FUNCTION_GET_CONFIGURATION = 12
    FUNCTION_SET_MOVING_AVERAGE = 13
    FUNCTION_GET_MOVING_AVERAGE = 14
    FUNCTION_SET_OFFSET_CALIBRATION = 15
    FUNCTION_GET_OFFSET_CALIBRATION = 16
    FUNCTION_GET_SPITFP_ERROR_COUNT = 234
    FUNCTION_SET_BOOTLOADER_MODE = 235
    FUNCTION_GET_BOOTLOADER_MODE = 236
    FUNCTION_SET_WRITE_FIRMWARE_POINTER = 237
    FUNCTION_WRITE_FIRMWARE = 238
    FUNCTION_SET_STATUS_LED_CONFIG = 239
    FUNCTION_GET_STATUS_LED_CONFIG = 240
    FUNCTION_GET_CHIP_TEMPERATURE = 242
    FUNCTION_RESET = 243
    FUNCTION_WRITE_UID = 248
    FUNCTION_READ_UID = 249
    FUNCTION_GET_IDENTITY = 255

    THRESHOLD_OPTION_OFF = 'x'
    THRESHOLD_OPTION_OUTSIDE = 'o'
    THRESHOLD_OPTION_INSIDE = 'i'
    THRESHOLD_OPTION_SMALLER = '<'
    THRESHOLD_OPTION_GREATER = '>'
    BOOTLOADER_MODE_BOOTLOADER = 0
    BOOTLOADER_MODE_FIRMWARE = 1
    BOOTLOADER_MODE_BOOTLOADER_WAIT_FOR_REBOOT = 2
    BOOTLOADER_MODE_FIRMWARE_WAIT_FOR_REBOOT = 3
    BOOTLOADER_MODE_FIRMWARE_WAIT_FOR_ERASE_AND_REBOOT = 4
    BOOTLOADER_STATUS_OK = 0
    BOOTLOADER_STATUS_INVALID_MODE = 1
    BOOTLOADER_STATUS_NO_CHANGE = 2
    BOOTLOADER_STATUS_ENTRY_FUNCTION_NOT_PRESENT = 3
    BOOTLOADER_STATUS_DEVICE_IDENTIFIER_INCORRECT = 4
    BOOTLOADER_STATUS_CRC_MISMATCH = 5
    STATUS_LED_CONFIG_OFF = 0
    STATUS_LED_CONFIG_ON = 1
    STATUS_LED_CONFIG_SHOW_HEARTBEAT = 2
    STATUS_LED_CONFIG_SHOW_STATUS = 3

    def __init__(self, uid, ipcon):
        """
        Creates an object with the unique device ID *uid* and adds it to
        the IP Connection *ipcon*.
        """
        Device.__init__(self, uid, ipcon)

        self.api_version = (2, 0, 0)

        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_DISTANCE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_DISTANCE_CALLBACK_CONFIGURATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_DISTANCE_CALLBACK_CONFIGURATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_VELOCITY] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_VELOCITY_CALLBACK_CONFIGURATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_VELOCITY_CALLBACK_CONFIGURATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_ENABLE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_ENABLE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_CONFIGURATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_CONFIGURATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_MOVING_AVERAGE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_MOVING_AVERAGE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_OFFSET_CALIBRATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_OFFSET_CALIBRATION] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_SPITFP_ERROR_COUNT] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_BOOTLOADER_MODE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_BOOTLOADER_MODE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_WRITE_FIRMWARE_POINTER] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_WRITE_FIRMWARE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_SET_STATUS_LED_CONFIG] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_STATUS_LED_CONFIG] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_CHIP_TEMPERATURE] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_RESET] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_WRITE_UID] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_FALSE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_READ_UID] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE
        self.response_expected[BrickletLaserRangeFinderV2.FUNCTION_GET_IDENTITY] = BrickletLaserRangeFinderV2.RESPONSE_EXPECTED_ALWAYS_TRUE

        self.callback_formats[BrickletLaserRangeFinderV2.CALLBACK_DISTANCE] = 'H'
        self.callback_formats[BrickletLaserRangeFinderV2.CALLBACK_VELOCITY] = 'h'


    def get_distance(self):
        """
        Returns the measured distance. The value has a range of 0 to 4000
        and is given in cm.

        The laser has to be enabled, see :func:`Enable Laser`.


        If you want to get the value periodically, it is recommended to use the
        :cb:`Distance` callback. You can set the callback configuration
        with :func:`Set Distance Callback Configuration`.


        If you want to get the value periodically, it is recommended to use the
        :cb:`Velocity` callback. You can set the callback configuration
        with :func:`Set Velocity Callback Configuration`.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_DISTANCE, (), '', 'H')

    def set_distance_callback_configuration(self, period, value_has_to_change, option, min, max):
        """
        The period in ms is the period with which the :cb:`Distance` callback is triggered
        periodically. A value of 0 turns the callback off.

        If the `value has to change`-parameter is set to true, the callback is only
        triggered after the value has changed. If the value didn't change
        within the period, the callback is triggered immediately on change.

        If it is set to false, the callback is continuously triggered with the period,
        independent of the value.

        It is furthermore possible to constrain the callback with thresholds.

        The `option`-parameter together with min/max sets a threshold for the :cb:`Distance` callback.

        The following options are possible:

        .. csv-table::
         :header: "Option", "Description"
         :widths: 10, 100

         "'x'",    "Threshold is turned off"
         "'o'",    "Threshold is triggered when the value is *outside* the min and max values"
         "'i'",    "Threshold is triggered when the value is *inside* or equal to the min and max values"
         "'<'",    "Threshold is triggered when the value is smaller than the min value (max is ignored)"
         "'>'",    "Threshold is triggered when the value is greater than the min value (max is ignored)"

        If the option is set to 'x' (threshold turned off) the callback is triggered with the fixed period.

        The default value is (0, false, 'x', 0, 0).
        """
        period = int(period)
        value_has_to_change = bool(value_has_to_change)
        option = create_char(option)
        min = int(min)
        max = int(max)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_DISTANCE_CALLBACK_CONFIGURATION, (period, value_has_to_change, option, min, max), 'I ! c H H', '')

    def get_distance_callback_configuration(self):
        """
        Returns the callback configuration as set by :func:`Set Distance Callback Configuration`.
        """
        return GetDistanceCallbackConfiguration(*self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_DISTANCE_CALLBACK_CONFIGURATION, (), '', 'I ! c H H'))

    def get_velocity(self):
        """
        Returns the measured distance. The value has a range of 0 to 4000
        and is given in cm.

        The laser has to be enabled, see :func:`Enable Laser`.


        If you want to get the value periodically, it is recommended to use the
        :cb:`Distance` callback. You can set the callback configuration
        with :func:`Set Distance Callback Configuration`.


        If you want to get the value periodically, it is recommended to use the
        :cb:`Velocity` callback. You can set the callback configuration
        with :func:`Set Velocity Callback Configuration`.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_VELOCITY, (), '', 'h')

    def set_velocity_callback_configuration(self, period, value_has_to_change, option, min, max):
        """
        The period in ms is the period with which the :cb:`Velocity` callback is triggered
        periodically. A value of 0 turns the callback off.

        If the `value has to change`-parameter is set to true, the callback is only
        triggered after the value has changed. If the value didn't change
        within the period, the callback is triggered immediately on change.

        If it is set to false, the callback is continuously triggered with the period,
        independent of the value.

        It is furthermore possible to constrain the callback with thresholds.

        The `option`-parameter together with min/max sets a threshold for the :cb:`Velocity` callback.

        The following options are possible:

        .. csv-table::
         :header: "Option", "Description"
         :widths: 10, 100

         "'x'",    "Threshold is turned off"
         "'o'",    "Threshold is triggered when the value is *outside* the min and max values"
         "'i'",    "Threshold is triggered when the value is *inside* or equal to the min and max values"
         "'<'",    "Threshold is triggered when the value is smaller than the min value (max is ignored)"
         "'>'",    "Threshold is triggered when the value is greater than the min value (max is ignored)"

        If the option is set to 'x' (threshold turned off) the callback is triggered with the fixed period.

        The default value is (0, false, 'x', 0, 0).
        """
        period = int(period)
        value_has_to_change = bool(value_has_to_change)
        option = create_char(option)
        min = int(min)
        max = int(max)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_VELOCITY_CALLBACK_CONFIGURATION, (period, value_has_to_change, option, min, max), 'I ! c h h', '')

    def get_velocity_callback_configuration(self):
        """
        Returns the callback configuration as set by :func:`Set Velocity Callback Configuration`.
        """
        return GetVelocityCallbackConfiguration(*self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_VELOCITY_CALLBACK_CONFIGURATION, (), '', 'I ! c h h'))

    def set_enable(self, enable):
        """
        Activates the laser of the LIDAR if set to *true*.

        We recommend that you wait 250ms after enabling the laser before
        the first call of :func:`Get Distance` to ensure stable measurements.
        """
        enable = bool(enable)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_ENABLE, (enable,), '!', '')

    def get_enable(self):
        """
        Returns the value as set by :func:`Set Enbale`.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_ENABLE, (), '', '!')

    def set_configuration(self, acquisition_count, enable_quick_termination, threshold_value, measurement_frequency):
        """
        The **Aquisition Count** defines the number of times the Laser Range Finder Bricklet
        will integrate acquisitions to find a correlation record peak. With a higher count,
        the Bricklet can measure longer distances. With a lower count, the rate increases. The
        allowed values are 1-255.

        If you set **Enable Quick Termination** to true, the distance measurement will be terminated
        early if a high peak was already detected. This means that a higher measurement rate can be achieved
        and long distances can be measured at the same time. However, the chance of false-positive
        distance measurements increases.

        Normally the distance is calculated with a detection algorithm that uses peak value,
        signal strength and noise. You can however also define a fixed **Threshold Value**.
        Set this to a low value if you want to measure the distance to something that has
        very little reflection (e.g. glass) and set it to a high value if you want to measure
        the distance to something with a very high reflection (e.g. mirror). Set this to 0 to
        use the default algorithm. The other allowed values are 1-255.

        Set the **Measurement Frequency** in Hz to force a fixed measurement rate. If set to 0,
        the Laser Range Finder Bricklet will use the optimal frequency according to the other
        configurations and the actual measured distance. Since the rate is not fixed in this case,
        the velocity measurement is not stable. For a stable velocity measurement you should
        set a fixed measurement frequency. The lower the frequency, the higher is the resolution
        of the calculated velocity. The allowed values are 10Hz-500Hz (and 0 to turn the fixed
        frequency off).

        The default values for Acquisition Count, Enable Quick Termination, Threshold Value and
        Measurement Frequency are 128, false, 0 and 0.
        """
        acquisition_count = int(acquisition_count)
        enable_quick_termination = bool(enable_quick_termination)
        threshold_value = int(threshold_value)
        measurement_frequency = int(measurement_frequency)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_CONFIGURATION, (acquisition_count, enable_quick_termination, threshold_value, measurement_frequency), 'B ! B H', '')

    def get_configuration(self):
        """
        Returns the configuration as set by :func:`Set Configuration`.
        """
        return GetConfiguration(*self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_CONFIGURATION, (), '', 'B ! B H'))

    def set_moving_average(self, distance_average_length, velocity_average_length):
        """
        Sets the length of a `moving averaging <https://en.wikipedia.org/wiki/Moving_average>`__
        for the distance and velocity.

        Setting the length to 0 will turn the averaging completely off. With less
        averaging, there is more noise on the data.

        The range for the averaging is 0-255.

        The default value is 10.
        """
        distance_average_length = int(distance_average_length)
        velocity_average_length = int(velocity_average_length)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_MOVING_AVERAGE, (distance_average_length, velocity_average_length), 'B B', '')

    def get_moving_average(self):
        """
        Returns the length moving average as set by :func:`Set Moving Average`.
        """
        return GetMovingAverage(*self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_MOVING_AVERAGE, (), '', 'B B'))

    def set_offset_calibration(self, offset):
        """
        The offset is given in cm and added to the measured distance.
        It is saved in non-volatile memory, you only have to set it once.

        The Bricklet comes with a per-sensor factory-calibrated offset value,
        you should not have to call this function.

        If you want to re-calibrate the offset you first have to set it to 0.
        Calculate the offset by measuring the distance to a known distance
        and set it again.
        """
        offset = int(offset)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_OFFSET_CALIBRATION, (offset,), 'h', '')

    def get_offset_calibration(self):
        """
        Returns the offset value as set by :func:`Set Offset Calibration`.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_OFFSET_CALIBRATION, (), '', 'h')

    def get_spitfp_error_count(self):
        """
        Returns the error count for the communication between Brick and Bricklet.

        The errors are divided into

        * ACK checksum errors,
        * message checksum errors,
        * framing errors and
        * overflow errors.

        The errors counts are for errors that occur on the Bricklet side. All
        Bricks have a similar function that returns the errors on the Brick side.
        """
        return GetSPITFPErrorCount(*self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_SPITFP_ERROR_COUNT, (), '', 'I I I I'))

    def set_bootloader_mode(self, mode):
        """
        Sets the bootloader mode and returns the status after the requested
        mode change was instigated.

        You can change from bootloader mode to firmware mode and vice versa. A change
        from bootloader mode to firmware mode will only take place if the entry function,
        device identifier and CRC are present and correct.

        This function is used by Brick Viewer during flashing. It should not be
        necessary to call it in a normal user program.
        """
        mode = int(mode)

        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_BOOTLOADER_MODE, (mode,), 'B', 'B')

    def get_bootloader_mode(self):
        """
        Returns the current bootloader mode, see :func:`Set Bootloader Mode`.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_BOOTLOADER_MODE, (), '', 'B')

    def set_write_firmware_pointer(self, pointer):
        """
        Sets the firmware pointer for :func:`Write Firmware`. The pointer has
        to be increased by chunks of size 64. The data is written to flash
        every 4 chunks (which equals to one page of size 256).

        This function is used by Brick Viewer during flashing. It should not be
        necessary to call it in a normal user program.
        """
        pointer = int(pointer)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_WRITE_FIRMWARE_POINTER, (pointer,), 'I', '')

    def write_firmware(self, data):
        """
        Writes 64 Bytes of firmware at the position as written by
        :func:`Set Write Firmware Pointer` before. The firmware is written
        to flash every 4 chunks.

        You can only write firmware in bootloader mode.

        This function is used by Brick Viewer during flashing. It should not be
        necessary to call it in a normal user program.
        """
        data = list(map(int, data))

        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_WRITE_FIRMWARE, (data,), '64B', 'B')

    def set_status_led_config(self, config):
        """
        Sets the status LED configuration. By default the LED shows
        communication traffic between Brick and Bricklet, it flickers once
        for every 10 received data packets.

        You can also turn the LED permanently on/off or show a heartbeat.

        If the Bricklet is in bootloader mode, the LED is will show heartbeat by default.
        """
        config = int(config)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_SET_STATUS_LED_CONFIG, (config,), 'B', '')

    def get_status_led_config(self):
        """
        Returns the configuration as set by :func:`Set Status LED Config`
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_STATUS_LED_CONFIG, (), '', 'B')

    def get_chip_temperature(self):
        """
        Returns the temperature in °C as measured inside the microcontroller. The
        value returned is not the ambient temperature!

        The temperature is only proportional to the real temperature and it has bad
        accuracy. Practically it is only useful as an indicator for
        temperature changes.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_CHIP_TEMPERATURE, (), '', 'h')

    def reset(self):
        """
        Calling this function will reset the Bricklet. All configurations
        will be lost.

        After a reset you have to create new device objects,
        calling functions on the existing ones will result in
        undefined behavior!
        """
        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_RESET, (), '', '')

    def write_uid(self, uid):
        """
        Writes a new UID into flash. If you want to set a new UID
        you have to decode the Base58 encoded UID string into an
        integer first.

        We recommend that you use Brick Viewer to change the UID.
        """
        uid = int(uid)

        self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_WRITE_UID, (uid,), 'I', '')

    def read_uid(self):
        """
        Returns the current UID as an integer. Encode as
        Base58 to get the usual string version.
        """
        return self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_READ_UID, (), '', 'I')

    def get_identity(self):
        """
        Returns the UID, the UID where the Bricklet is connected to,
        the position, the hardware and firmware version as well as the
        device identifier.

        The position can be 'a', 'b', 'c' or 'd'.

        The device identifier numbers can be found :ref:`here <device_identifier>`.
        |device_identifier_constant|
        """
        return GetIdentity(*self.ipcon.send_request(self, BrickletLaserRangeFinderV2.FUNCTION_GET_IDENTITY, (), '', '8s 8s c 3B 3B H'))

    def register_callback(self, callback_id, function):
        """
        Registers the given *function* with the given *callback_id*.
        """
        if function is None:
            self.registered_callbacks.pop(callback_id, None)
        else:
            self.registered_callbacks[callback_id] = function

LaserRangeFinderV2 = BrickletLaserRangeFinderV2 # for backward compatibility