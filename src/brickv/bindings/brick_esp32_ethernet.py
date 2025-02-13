# -*- coding: utf-8 -*-
#############################################################
# This file was automatically generated on 2023-05-09.      #
#                                                           #
# Python Bindings Version 2.1.30                            #
#                                                           #
# If you have a bugfix for this file and want to commit it, #
# please fix the bug in the generator. You can find a link  #
# to the generators git repository on tinkerforge.com       #
#############################################################

from collections import namedtuple

try:
    from .ip_connection import Device, IPConnection, Error, create_char, create_char_list, create_string, create_chunk_data
except (ValueError, ImportError):
    try:
        from ip_connection import Device, IPConnection, Error, create_char, create_char_list, create_string, create_chunk_data
    except (ValueError, ImportError):
        from tinkerforge.ip_connection import Device, IPConnection, Error, create_char, create_char_list, create_string, create_chunk_data

GetIdentity = namedtuple('Identity', ['uid', 'connected_uid', 'position', 'hardware_version', 'firmware_version', 'device_identifier'])

class BrickESP32Ethernet(Device):
    r"""
    ESP32 microcontroller based Brick with Ethernet and 6 Bricklet ports
    """

    DEVICE_IDENTIFIER = 115
    DEVICE_DISPLAY_NAME = 'ESP32 Ethernet Brick'
    DEVICE_URL_PART = 'esp32_ethernet' # internal



    FUNCTION_GET_IDENTITY = 255


    def __init__(self, uid, ipcon):
        r"""
        Creates an object with the unique device ID *uid* and adds it to
        the IP Connection *ipcon*.
        """
        Device.__init__(self, uid, ipcon, BrickESP32Ethernet.DEVICE_IDENTIFIER, BrickESP32Ethernet.DEVICE_DISPLAY_NAME)

        self.api_version = (2, 0, 0)

        self.response_expected[BrickESP32Ethernet.FUNCTION_GET_IDENTITY] = BrickESP32Ethernet.RESPONSE_EXPECTED_ALWAYS_TRUE


        ipcon.add_device(self)

    def get_identity(self):
        r"""
        Returns the UID, the UID where the Brick is connected to,
        the position, the hardware and firmware version as well as the
        device identifier.

        The position is the position in the stack from '0' (bottom) to '8' (top).

        The device identifier numbers can be found :ref:`here <device_identifier>`.
        |device_identifier_constant|
        """
        return GetIdentity(*self.ipcon.send_request(self, BrickESP32Ethernet.FUNCTION_GET_IDENTITY, (), '', 33, '8s 8s c 3B 3B H'))

ESP32Ethernet = BrickESP32Ethernet # for backward compatibility
