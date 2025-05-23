# -*- coding: utf-8 -*-
"""
brickv (Brick Viewer)
Copyright (C) 2011-2015, 2018 Olaf Lüke <olaf@tinkerforge.com>
Copyright (C) 2012 Bastian Nordmeyer <bastian@tinkerforge.com>
Copyright (C) 2012-2017 Matthias Bolte <matthias@tinkerforge.com>
Copyright (C) 2020-2021 Erik Fleckstein <erik@tinkerforge.com>

flashing.py: GUI for flashing features

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

import io
import sys
import os
import zipfile
import urllib.request
import urllib.error
import time
import struct
import json
import html
from threading import Thread

from PyQt5.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem, QBrush, QFontMetrics
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QProgressDialog, QProgressBar, QPlainTextEdit, QVBoxLayout, QPushButton

from brickv import config
from brickv.ui_flashing import Ui_Flashing
from brickv.bindings.brick_master import BrickMaster
from brickv.bindings.ip_connection import IPConnection, Error, base58encode, \
                                          base58decode, BASE58, uid64_to_uid32
from brickv.imu_calibration import parse_imu_calibration, IMU_CALIBRATION_URL
from brickv.samba import SAMBA, SAMBAException, SAMBARebootError, get_serial_ports
from brickv.infos import get_version_string
from brickv.utils import get_home_path, get_open_file_name, \
                         get_modeless_dialog_flags, parse_version
from brickv.esp_flash import ESPFlash, FatalError
from brickv.infos import BrickREDInfo, DeviceInfo, inventory
from brickv.firmware_fetch import ERROR_DOWNLOAD
from brickv.utils import get_main_window, get_save_file_name
from brickv.devicesproxymodel import DevicesProxyModel
from brickv.urlopen import urlopen
from brickv.esptool import main as esptool_main, \
                           print_callback_ref as esptool_print_callback_ref, \
                           firmware_ref as esptool_firmware_ref

FIRMWARE_URL = 'https://download.tinkerforge.com/firmwares/'
SELECT = 'Select...'
CUSTOM = 'Custom...'
NO_BRICK = 'No Brick found'
NO_EXTENSION = 'No Extension found'
NO_BOOTLOADER = 'No Brick in Bootloader found'

def error_to_name(e):
    if e.value == Error.TIMEOUT:
        return 'Timeout'

    if e.value == Error.NOT_CONNECTED:
        return 'No TCP/IP connection'

    if e.value == Error.INVALID_PARAMETER:
        return 'Invalid parameter'

    if e.value == Error.NOT_SUPPORTED:
        return 'Not supported'

    return e.message

class PaddedProgressDialog(QProgressDialog):
    def __init__(self, parent, text_for_width_calculation=None):
        super().__init__(parent)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setWindowTitle("Updates / Flashing")
        self.setWindowModality(Qt.WindowModal)
        if text_for_width_calculation is None:
            self.text_for_width_calculation = 'Verifying written plugin: bricklet_industrial_dual_analog_in_v2_firmware_2_0_0.zbin'
            self.uses_default_text_for_width_calculation = True
        else:
            self.text_for_width_calculation = text_for_width_calculation
            self.uses_default_text_for_width_calculation = False
        self.canceled.connect(self.hide)

    # overrides QProgressDialog.sizeHint
    def sizeHint(self):
        size = QProgressDialog.sizeHint(self)
        size.setWidth(QFontMetrics(QApplication.font()).width(self.text_for_width_calculation) + 100)
        return size

    def reset(self, title, length):
        if title != None:
            self.setLabelText(title)

        self.setMaximum(length)
        self.setValue(0)
        self.show()
        QApplication.processEvents()

    def update(self, value=None):
        if value != None:
            self.setValue(value)

        QApplication.processEvents()

    def hideCancelButton(self):
        self.setCancelButton(None)
        self.adjustSize()

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self.daemon = True
        self._return = None
        self._exception = None
    def run(self):
        if self._target is not None:
            try:
                self._return = self._target(*self._args, **self._kwargs)
            except Exception as e:
                self._exception = e
    def join(self, *args, **kwargs):
        Thread.join(self, *args, **kwargs)
        return self._return, self._exception

class BrickletKindMismatchError(Exception):
    pass

class ESPToolDialog(QDialog):
    add_text = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Updates / Flashing")
        self.setWindowModality(Qt.WindowModal)

        self.layout = QVBoxLayout(self)
        self.edit = QPlainTextEdit(self)
        self.button = QPushButton('Close', self)

        self.layout.addWidget(self.edit)
        self.layout.addWidget(self.button)

        self.edit.setReadOnly(True)
        self.edit.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.button.setEnabled(False)

        self.text = ''

        self.add_text.connect(self.cb_add_text)
        self.button.clicked.connect(self.close)

    def reject(self):
        pass # avoid closing using ESC key

    def closeEvent(self, event):
        if not self.button.isEnabled():
            event.ignore()

        # dont touch event to avoid closing using ESC key

    def cb_add_text(self, text):
        self.show()

        self.text += text

        self.edit.setPlainText(self.text)

        scrollbar = self.edit.verticalScrollBar()

        scrollbar.setValue(scrollbar.maximum())

class FlashingWindow(QDialog, Ui_Flashing):
    def __init__(self, parent):
        QDialog.__init__(self, parent, get_modeless_dialog_flags())

        self.setupUi(self)

        self.ipcon_available = False
        self.ignore_tab_changed_event = False

        self.tool_infos = {}
        self.firmware_infos = {}
        self.plugin_infos = {}
        self.extension_firmware_infos = {}
        self.extension_infos = []
        self.refresh_updates_pending = False

        self.fw_fetch_progress_bar = None

        self.last_firmware_url_part = ""
        self.last_plugin_url_part = ""
        self.last_extension_firmware_url_part = ""

        self.parent = parent
        self.tab_widget.currentChanged.connect(self.tab_changed)
        self.button_serial_port_refresh.clicked.connect(self.refresh_serial_ports)
        self.combo_firmware.currentIndexChanged.connect(self.firmware_changed)
        self.button_update_firmware_list.clicked.connect(lambda: self.refresh_updates_clicked(force=True))
        self.button_firmware_save.clicked.connect(self.firmware_save_clicked)
        self.button_firmware_browse.clicked.connect(self.firmware_browse_clicked)
        self.button_uid_load.clicked.connect(self.uid_load_clicked)
        self.button_uid_save.clicked.connect(self.uid_save_clicked)
        self.combo_parent.currentIndexChanged.connect(self.brick_changed)
        self.combo_port.currentIndexChanged.connect(self.port_changed)
        self.combo_plugin.currentIndexChanged.connect(self.plugin_changed)
        self.button_update_plugin_list.clicked.connect(lambda: self.refresh_updates_clicked(force=True))
        self.button_plugin_save.clicked.connect(self.plugin_save_clicked)
        self.button_plugin_browse.clicked.connect(self.plugin_browse_clicked)
        self.combo_extension.currentIndexChanged.connect(self.extension_changed)
        self.combo_extension_firmware.currentIndexChanged.connect(self.extension_firmware_changed)
        self.button_update_ext_firmware_list.clicked.connect(lambda: self.refresh_updates_clicked(force=True))
        self.button_extension_firmware_save.clicked.connect(self.extension_firmware_save_clicked)
        self.button_extension_firmware_browse.clicked.connect(self.extension_firmware_browse_clicked)

        inventory.info_changed.connect(self.update_bricks)
        inventory.info_changed.connect(self.update_extensions)

        self.label_update_tool.hide()
        self.label_no_update_connection.hide()
        self.label_no_firmware_connection.hide()
        self.label_no_plugin_connection.hide()
        self.label_no_extension_firmware_connection.hide()
        self.label_extension_firmware_usb_hint.hide()

        self.refresh_serial_ports()

        self.combo_firmware.addItem(CUSTOM)
        self.combo_firmware.setEnabled(False)
        self.firmware_changed(0)

        self.combo_plugin.addItem(CUSTOM)
        self.combo_plugin.setEnabled(False)
        self.plugin_changed(0)

        self.combo_extension_firmware.addItem(CUSTOM)
        self.combo_extension_firmware.setEnabled(False)
        self.extension_firmware_changed(0)

        self.brick_changed(0)
        self.extension_changed(0)

        self.update_tree_view_model_labels = ['Name', 'UID', 'Position', 'Installed', 'Latest']

        self.update_tree_view_model = QStandardItemModel(self)

        self.update_tree_view_proxy_model = DevicesProxyModel(self)
        self.update_tree_view_proxy_model.setSourceModel(self.update_tree_view_model)
        self.update_tree_view.setModel(self.update_tree_view_proxy_model)
        self.update_tree_view.setSortingEnabled(True)
        self.update_tree_view.header().setSortIndicator(2, Qt.AscendingOrder)
        self.update_tree_view.activated.connect(self.update_tree_view_clicked)
        self.update_tree_view.setExpandsOnDoubleClick(False)

        self.update_button_refresh.clicked.connect(lambda: self.refresh_updates_clicked(force=False))
        self.update_button_bricklets.clicked.connect(self.auto_update_bricklets_clicked)

        self.combo_serial_port.currentIndexChanged.connect(self.update_ui_state)
        self.edit_custom_firmware.textChanged.connect(self.update_ui_state)
        self.edit_custom_plugin.textChanged.connect(self.update_ui_state)
        self.edit_custom_extension_firmware.textChanged.connect(self.update_ui_state)

        self.button_close.clicked.connect(self.hide)

        get_main_window().fw_version_fetcher.fw_versions_avail.connect(self.fw_versions_fetched)

        self.refresh_update_tree_view()

        self.update_bricks()
        self.update_extensions()

    def reject(self):
        pass # avoid closing using ESC key

    def closeEvent(self, event):
        pass # dont touch event to avoid closing using ESC key

    def download_file(self, url, name, filename=None, progress_dialog=None):
        downloading_text = 'Downloading {}'.format(name)
        done_text = downloading_text + ' - Done'
        connecting_text = 'Connecting to ' + url.replace('https://', '').split('/')[0]
        text_for_width_calculation = done_text if len(done_text) > len(connecting_text) else connecting_text

        if progress_dialog is None:
            progress = PaddedProgressDialog(self, text_for_width_calculation)
        else:
            progress = progress_dialog
            if progress.uses_default_text_for_width_calculation:
                progress.text_for_width_calculation = text_for_width_calculation
                progress.adjustSize()

        progress.setMaximum(0)
        progress.setLabelText(connecting_text)
        progress.setValue(0)
        progress.forceShow()

        # Use a small block size to increase responsiveness of the progress dialog.
        # Unfortunately there is no non blocking read available.
        block_size = 1024

        def urlopen_wrapper(url, **kwargs):
            try:
                return urlopen(url, **kwargs)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    if url.endswith('.bin'):
                        try:
                            with urlopen(url[:-4] + '.zbin', **kwargs) as r:
                                pass
                        except:
                            raise e

                        raise BrickletKindMismatchError('Cannot flash Co-Processor firmware onto Classic Bricklet')
                    elif url.endswith('.zbin'):
                        try:
                            with urlopen(url[:-5] + '.bin', **kwargs) as r:
                                pass
                        except:
                            raise e

                        raise BrickletKindMismatchError('Cannot flash Classic plugin onto Co-Processor Bricklet')

        try:
            connection_thread = ThreadWithReturnValue(target=urlopen_wrapper, args=[url], kwargs={'timeout': 10})
            connection_thread.start()
            while True:
                response, exception = connection_thread.join(timeout=1.0/60)
                if not connection_thread.is_alive():
                    break
                QApplication.processEvents()
            if exception is not None:
                raise exception
            with response:
                progress.setValue(0)
                progress.setLabelText(downloading_text)
                QApplication.processEvents()

                file_size = int(response.info().get('Content-Length', 0))
                progress.setMaximum(file_size)
                progress.setValue(0)
                progress.setLabelText(downloading_text)
                QApplication.processEvents()

                blocks_transfered = 0

                if filename is not None:
                    file = open(filename + '.part', 'wb')
                else:
                    file = io.BytesIO()

                with file:
                    while True:
                        if progress.wasCanceled():
                            progress.hide()
                            return None

                        block = response.read(block_size)
                        if len(block) == 0:
                            break

                        file.write(block)

                        blocks_transfered += 1
                        progress.setValue(min(progress.maximum(), blocks_transfered * block_size))
                        QApplication.processEvents()

                    # Only show finished state if progress is our own dialog
                    if progress_dialog is None:
                        progress.setLabelText(done_text)
                        progress.setCancelButtonText('OK')
                        progress.setMaximum(1)
                        progress.setValue(1)

                    if filename is None:
                        file.seek(0)
                        return file.read()

                # Do this outside the file context manager:
                # The file should be closed before renaming it.
                os.replace(filename + '.part', filename)


        except BrickletKindMismatchError as e:
            progress.cancel()
            self.popup_fail('Updates / Flashing', html.escape(str(e)))
        except Exception as e:
            progress.cancel()
            self.popup_fail('Updates / Flashing',
                            "Failed to download {0}.<br/><br/>".format(name) +
                            "Please report this error to <a href='mailto:info@tinkerforge.com'>info@tinkerforge.com</a>:<br/><br/>" +
                            html.escape(str(e)))
            return None

    def get_brickv_download_url(self, version):
        url = 'https://download.tinkerforge.com/tools/brickv/{platform}/brickv{suffix}'
        suffix = ''

        package_type = config.PACKAGE_TYPE
        platform = {'exe': 'windows', 'dmg': 'macos'}.get(package_type, 'linux')
        default_filename = 'brickv-{}.{}'.format(version, package_type)

        if package_type == 'deb':
            suffix = '-{version_dots}_all.deb'.format(version_dots=version)
        elif package_type == 'aur':
            metadata_url = 'https://aur.archlinux.org/rpc/?v=5&type=info&arg[]=brickv'
            try:
                with urlopen(metadata_url, timeout=10) as response:
                    parsed = json.loads(response.read().decode('utf-8'))
                    for result in parsed['results']:
                        if result['Name'] == 'brickv':
                            aur_version = result['Version'].split('-')[0]
                            break
                    else:
                        raise Exception("Could not query AUR package version.")
            except:
                if QMessageBox.warning(self, "Updates / Flashing", "Could not query AUR package version. Download anyway?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                    return
                # User wants to download whatever is in the AUR, fake that it is the correct version
                aur_version = version
            if parse_version(aur_version) != parse_version(version):
                if QMessageBox.warning(self, "Updates / Flashing", "AUR package version was {}, but expected was {}. Download anyway?".format(aur_version, version), QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                    return
                # User wants to download whatever is in the AUR, override version, so that the progress dialog title shown when downloading is correct.
                version = aur_version
            url = 'https://aur.archlinux.org/cgit/aur.git/snapshot/brickv.tar.gz'
            default_filename = 'brickv-{}.tar.gz'.format(version)
        elif package_type == 'dmg' or package_type == 'exe':
            suffix = '_{platform}_{version_under}.{ext}'.format(platform=platform, version_under='_'.join(version.split('.')), ext=package_type)
        else:
            url = 'https://github.com/Tinkerforge/brickv/archive/v{version_dots}.zip'.format(version_dots=version)

        url = url.format(platform=platform, suffix=suffix)
        return url, version

    def update_tree_view_clicked(self, idx):
        name, uid, _position, _current_version, latest_version = [idx.sibling(idx.row(), i).data() for i in range(0, 5)]

        is_local_brickv = "brick viewer" in name.lower() and idx.parent().data() is None

        is_red_brick_brickv = "brick viewer" in name.lower() and idx.parent().data() is not None
        is_red_brick_bindings = "bindings" in name.lower()

        if is_red_brick_brickv or is_red_brick_bindings:
            parent = idx.parent()

            while parent.parent().data() is not None:
                parent = parent.parent()

            uid = parent.sibling(parent.row(), 1).data()

            if inventory.get_info(uid).plugin is not None:
                inventory.get_info(uid).plugin.perform_action(3)

            return

        if is_local_brickv:
            url, version = self.get_brickv_download_url(latest_version)
            default_filename = url.split('/')[-1]

            filename = get_save_file_name(self, "Save Brick Viewer Update", os.path.join(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation), default_filename))
            if len(filename) == 0:
                return

            self.download_file(url, 'Brick Viewer {}'.format(version), filename)
            return

        if "wifi" in name.lower() and "2.0" in name.lower():
            uid = idx.parent().sibling(idx.parent().row(), 1).data()
            self.show_extension_update(uid)
            return

        if len(uid) == 0:
            return # Tools and firmware-less extensions

        device_info = inventory.get_info(uid)

        if isinstance(device_info, BrickREDInfo):
            self.show_red_brick_update()
        elif not device_info.flashable_like_bricklet:
            self.show_brick_update(device_info.url_part)
        elif device_info.flashable_like_bricklet:
            self.show_bricklet_update(device_info.connected_uid, device_info.position)

    def fw_versions_fetched(self, firmware_info):
        if isinstance(firmware_info, int):
            if self.fw_fetch_progress_bar is not None:
                self.fw_fetch_progress_bar.cancel()
                self.fw_fetch_progress_bar = None

                self.combo_firmware.setEnabled(False)
                self.combo_firmware_version.setEnabled(False)
                self.combo_plugin.setEnabled(False)
                self.combo_plugin_version.setEnabled(False)
                self.combo_extension_firmware.setEnabled(False)
                self.combo_extension_firmware_version.setEnabled(False)

                if firmware_info == ERROR_DOWNLOAD:
                    self.popup_fail('Updates / Flashing',
                                    "Update information could not be downloaded from tinkerforge.com.<br/><br/>" +
                                    "Is your computer connected to the Internet?<br/><br/>" +
                                    "Firmwares and plugins can be flashed from local files only.")
                else:
                    self.popup_fail('Updates / Flashing',
                                    ("Update information on tinkerforge.com is malformed (error code {0}).<br/><br/>" +
                                     "Please report this error to <a href='mailto:info@tinkerforge.com'>info@tinkerforge.com</a>.<br/><br/>" +
                                     "Firmwares and plugins can be flashed from local files only.").format(firmware_info))
        else:
            self.refresh_update_tree_view()

        self.update_button_refresh.setDisabled(False)
        self.button_update_firmware_list.setDisabled(False)
        self.button_update_plugin_list.setDisabled(False)
        self.button_update_ext_firmware_list.setDisabled(False)

    def load_version_info(self, version_info):
        # Save combobox state by url_part
        selected_firmware = self.combo_firmware.currentData()
        selected_plugin = self.combo_plugin.currentData()
        selected_extension_firmware = self.combo_extension_firmware.currentData()

        self.reset_version_info()

        if version_info is not None:
            self.tool_infos.update(version_info.tool_infos)
            self.firmware_infos.update(version_info.firmware_infos)
            self.plugin_infos.update(version_info.plugin_infos)
            self.extension_firmware_infos.update(version_info.extension_firmware_infos)

            # update combo_firmware
            if len(self.firmware_infos) > 0:
                self.combo_firmware.addItem(SELECT)
                self.combo_firmware.insertSeparator(self.combo_firmware.count())

            for firmware_info in sorted(self.firmware_infos.values(), key=lambda x: x.name):
                name = '{0}'.format(firmware_info.name)
                self.combo_firmware.addItem(name, firmware_info.url_part)

            if self.combo_firmware.count() > 0:
                self.combo_firmware.insertSeparator(self.combo_firmware.count())

            # update combo_plugin
            if len(self.plugin_infos) > 0:
                self.combo_plugin.addItem(SELECT)
                self.combo_plugin.insertSeparator(self.combo_plugin.count())

            for plugin_info in sorted(self.plugin_infos.values(), key=lambda x: x.name):
                name = '{0}'.format(plugin_info.name)
                self.combo_plugin.addItem(name, plugin_info.url_part)

            if self.combo_plugin.count() > 0:
                self.combo_plugin.insertSeparator(self.combo_plugin.count())

            # update combo_extension_firmware
            if len(self.extension_firmware_infos) > 0:
                self.combo_extension_firmware.addItem(SELECT)
                self.combo_extension_firmware.insertSeparator(self.combo_extension_firmware.count())

            for extension_firmware_info in sorted(self.extension_firmware_infos.values(), key=lambda x: x.name):
                name = '{0}'.format(extension_firmware_info.name)
                self.combo_extension_firmware.addItem(name, extension_firmware_info.url_part)

            if self.combo_extension_firmware.count() > 0:
                self.combo_extension_firmware.insertSeparator(self.combo_extension_firmware.count())

        # Restore combobox state. If the former selected firmware is not found, set combobox to SELECT.
        self.combo_firmware.addItem(CUSTOM)

        if len(self.edit_custom_firmware.text()) > 0:
            firmware_idx = self.combo_firmware.count() - 1
        else:
            firmware_idx = self.combo_firmware.findData(selected_firmware)
            if firmware_idx < 0:
                firmware_idx = 0

        self.combo_firmware.setCurrentIndex(firmware_idx)
        self.firmware_changed(firmware_idx)

        self.combo_plugin.addItem(CUSTOM)
        plugin_idx = self.combo_plugin.findData(selected_plugin)

        if plugin_idx < 0:
            plugin_idx = 0

        self.combo_plugin.setCurrentIndex(plugin_idx)
        self.plugin_changed(plugin_idx)

        self.combo_extension_firmware.addItem(CUSTOM)

        if len(self.edit_custom_extension_firmware.text()) > 0:
            extension_firmware_idx = self.combo_extension_firmware.count() - 1
        else:
            extension_firmware_idx = self.combo_extension_firmware.findData(selected_extension_firmware)

            if extension_firmware_idx < 0:
                extension_firmware_idx = 0

        self.combo_extension_firmware.setCurrentIndex(extension_firmware_idx)
        self.extension_firmware_changed(extension_firmware_idx)

        self.update_ui_state()

    def reset_version_info(self):
        self.tool_infos = {}
        self.firmware_infos = {}
        self.plugin_infos = {}
        self.extension_firmware_infos = {}

        self.combo_firmware.clear()
        self.combo_plugin.clear()
        self.combo_extension_firmware.clear()
        self.combo_firmware.setEnabled(True)
        self.combo_plugin.setEnabled(True)
        self.combo_extension_firmware.setEnabled(True)

    def refresh_latest_version_info(self):
        self.fw_fetch_progress_bar.setLabelText('Discovering latest versions on tinkerforge.com')
        self.fw_fetch_progress_bar.setMaximum(0)
        self.fw_fetch_progress_bar.setValue(0)
        self.fw_fetch_progress_bar.show()

        get_main_window().fw_version_fetcher.fetch_now()

    def update_bricks(self):
        self.combo_parent.clear()

        has_no_parent_devices = False

        for info in inventory.get_device_infos():
            if info.reverse_connection == None and info.flashable_like_bricklet:
                has_no_parent_devices = True

        if has_no_parent_devices:
            no_parent_info = DeviceInfo()
            no_parent_info.name = 'None'
            no_parent_info.uid = '0'

            for info in inventory.get_device_infos():
                if info.reverse_connection == None and info.flashable_like_bricklet:
                    no_parent_info.connections_add_item((info.position, info))

            self.combo_parent.addItem('None', no_parent_info)

        for info in inventory.get_device_infos():
            if isinstance(info, DeviceInfo) and len(info.bricklet_ports) > 0:
                self.combo_parent.addItem(info.get_combo_item(), info)

        if self.combo_parent.count() == 0:
            self.combo_parent.addItem(NO_BRICK, None)

        if self.combo_parent.itemText(0) == 'None' and self.combo_parent.count() > 1:
            self.combo_parent.insertSeparator(1)

        self.update_ui_state()

    def popup_ok(self, title, message):
        QMessageBox.information(self, title, message, QMessageBox.Ok)

    def popup_fail(self, title, message):
        QMessageBox.critical(self, title, message, QMessageBox.Ok)

    def refresh_serial_ports(self):
        progress = PaddedProgressDialog(self)
        progress.setLabelText('Discovering')
        current_text = self.combo_serial_port.currentText()
        self.combo_serial_port.clear()

        try:
            progress.setLabelText('Discovering serial ports')
            progress.setMaximum(0)
            progress.setValue(0)
            progress.show()

            ports = get_serial_ports(vid=0x03eb, pid=0x6124, opaque='atmel') # ATMEL AT91 USB bootloader
            ports += get_serial_ports(vid=0x10c4, pid=0xea60, opaque='esp32') # CP2102N USB to UART chip used on ESP32 (Ethernet) Bricks
        except:
            import traceback
            traceback.print_exc()
            progress.cancel()
            self.combo_serial_port.addItem(NO_BOOTLOADER)
            self.update_ui_state()
            self.popup_fail('Brick', 'Could not discover serial ports')
        else:
            for port in ports:
                self.combo_serial_port.addItem(port.description, port)

            if self.combo_serial_port.count() == 0:
                self.combo_serial_port.addItem(NO_BOOTLOADER)
            else:
                self.combo_serial_port.insertItem(0, SELECT)
                self.combo_serial_port.insertSeparator(1)
                self.combo_serial_port.setCurrentIndex(0)
                if current_text != '':
                    index = self.combo_serial_port.findText(current_text)
                    if index >= 0:
                        self.combo_serial_port.setCurrentIndex(index)

            self.update_ui_state()

        progress.cancel()

        # For some reason the progress dialog is not hidden if the parent is not removed.
        # Other approaches such as hide, close, cancel, reset, QApplication.processEvents,
        # a single shot timer and setting progress to None don't work everytime.
        progress.setParent(None)

    def update_ui_state(self):
        # bricks
        is_no_bootloader = self.combo_serial_port.currentText() == NO_BOOTLOADER
        is_serial_port_select = self.combo_serial_port.currentText() == SELECT
        is_firmware_select = self.combo_firmware.currentText() == SELECT
        is_firmware_custom = self.combo_firmware.currentText() == CUSTOM
        custom_firmware_path = self.edit_custom_firmware.text()

        self.combo_serial_port.setEnabled(not is_no_bootloader)

        if len(custom_firmware_path) == 0:
            custom_firmware_is_valid = False

            self.label_custom_firmware_invalid.hide()
        else:
            custom_firmware_is_valid = os.path.isfile(custom_firmware_path)

            self.label_custom_firmware_invalid.setVisible(is_firmware_custom and not custom_firmware_is_valid)

        self.button_firmware_save.setEnabled(not is_no_bootloader and not is_serial_port_select and \
                                             ((not is_firmware_select and not is_firmware_custom) or \
                                              (is_firmware_custom and custom_firmware_is_valid)))

        self.combo_firmware_version.setEnabled(not is_firmware_custom and not is_firmware_select)
        self.edit_custom_firmware.setEnabled(is_firmware_custom)
        self.button_firmware_browse.setEnabled(is_firmware_custom)

        # bricklets
        is_no_brick = self.combo_parent.currentText() == NO_BRICK
        has_bricklet_ports = self.combo_port.count() > 0
        is_plugin_select = self.combo_plugin.currentText() == SELECT
        is_plugin_custom = self.combo_plugin.currentText() == CUSTOM
        custom_plugin_path = self.edit_custom_plugin.text()

        self.combo_parent.setEnabled(not is_no_brick)
        self.combo_port.setEnabled(has_bricklet_ports)
        self.combo_plugin.setEnabled(has_bricklet_ports)
        self.edit_uid.setEnabled(has_bricklet_ports)
        self.button_uid_load.setEnabled(has_bricklet_ports)
        self.button_uid_save.setEnabled(has_bricklet_ports)

        if len(custom_plugin_path) == 0:
            custom_plugin_is_valid = False

            self.label_custom_plugin_invalid.hide()
        else:
            custom_plugin_is_valid = os.path.isfile(custom_plugin_path)

            self.label_custom_plugin_invalid.setVisible(is_plugin_custom and not custom_plugin_is_valid)

        self.button_plugin_save.setEnabled(not is_no_brick and has_bricklet_ports and \
                                           ((not is_plugin_select and not is_plugin_custom) or \
                                            (is_plugin_custom and custom_plugin_is_valid)))

        self.combo_plugin_version.setEnabled(not is_plugin_custom and not is_plugin_select)
        self.edit_custom_plugin.setEnabled(is_plugin_custom)
        self.button_plugin_browse.setEnabled(is_plugin_custom)

        # extensions
        is_extension_firmware_select = self.combo_extension_firmware.currentText() == SELECT
        is_extension_firmware_custom = self.combo_extension_firmware.currentText() == CUSTOM
        is_no_extension = self.combo_extension.currentText() == NO_EXTENSION
        custom_extension_firmware_path = self.edit_custom_extension_firmware.text()

        self.combo_extension.setEnabled(not is_no_extension)

        try:
            extension_connection_type = self.extension_infos[self.combo_extension.currentIndex()].master_info.connection_type
        except IndexError:
            extension_connection_type = None

        if extension_connection_type == None:
            is_extension_connection_type_usb = False
        else:
            is_extension_connection_type_usb = extension_connection_type == BrickMaster.CONNECTION_TYPE_USB

        self.label_extension_firmware_usb_hint.setVisible(not is_extension_connection_type_usb)

        if len(custom_extension_firmware_path) == 0:
            custom_extension_firmware_is_valid = False

            self.label_custom_extension_firmware_invalid.hide()
        else:
            custom_extension_firmware_is_valid = os.path.isfile(custom_extension_firmware_path)

            self.label_custom_extension_firmware_invalid.setVisible(is_extension_firmware_custom and not custom_extension_firmware_is_valid)

        self.button_extension_firmware_save.setEnabled(not is_no_extension and is_extension_connection_type_usb and \
                                                       ((not is_extension_firmware_select and not is_extension_firmware_custom) or \
                                                        (is_extension_firmware_custom and custom_extension_firmware_is_valid)))

        self.combo_extension_firmware_version.setEnabled(not is_extension_firmware_custom and not is_extension_firmware_select)
        self.edit_custom_extension_firmware.setEnabled(is_extension_firmware_custom)
        self.button_extension_firmware_browse.setEnabled(is_extension_firmware_custom)

        # setTabEnabled sets the current index to the modified tab if enabled is true.
        # Restore the old selected tab after enabling.
        # Also ignore the tab_changed_event here, as it calls update_ui_state (this function)
        # resulting in endless recursion.
        self.ignore_tab_changed_event = True
        idx = self.tab_widget.currentIndex()
        self.tab_widget.setTabEnabled(2, self.ipcon_available and self.combo_parent.count() > 0 and self.combo_parent.itemText(0) != NO_BRICK)
        self.tab_widget.setTabEnabled(3, self.ipcon_available and len(self.extension_infos) > 0)

        if self.tab_widget.isTabEnabled(idx):
            self.tab_widget.setCurrentIndex(idx)

        self.ignore_tab_changed_event = False

    def firmware_changed(self, _index):
        self.update_ui_state()
        url_part = self.combo_firmware.currentData()

        last_selected_firmware = self.combo_firmware_version.currentData()
        last_latest_firmware = self.combo_firmware_version.itemData(0)

        self.combo_firmware_version.clear()

        if url_part is None:
            self.last_firmware_url_part = url_part
            return

        for version in self.firmware_infos[url_part].firmware_versions:
            self.combo_firmware_version.addItem('{}.{}.{}'.format(*version), version)

        if self.last_firmware_url_part == url_part and last_selected_firmware != last_latest_firmware:
            idx = self.combo_firmware_version.findData(last_selected_firmware)
            self.combo_firmware_version.setCurrentIndex(idx)

        self.last_firmware_url_part = url_part

    def firmware_browse_clicked(self):
        if len(self.edit_custom_firmware.text()) > 0:
            last_dir = os.path.dirname(os.path.realpath(self.edit_custom_firmware.text()))
        else:
            last_dir = get_home_path()

        filename = get_open_file_name(self, 'Open Firmware', last_dir, 'Firmwares(*.bin);;All Files(*)')

        if len(filename) > 0:
            self.edit_custom_firmware.setText(filename)

    def firmware_save_clicked(self):
        port = self.combo_serial_port.itemData(self.combo_serial_port.currentIndex())

        if port.opaque == 'atmel':
            self.firmware_save_atmel(port)
        elif port.opaque == 'esp32':
            self.firmware_save_esp32(port)

    def firmware_save_atmel(self, port):
        try:
            samba = SAMBA(port.path)
        except SAMBAException as e:
            self.refresh_serial_ports()
            self.popup_fail('Brick', 'Could not connect to Brick: {0}'.format(str(e)))
            return
        except:
            exc_info = sys.exc_info()
            self.refresh_serial_ports()
            # Report the exception without unwinding the call stack
            sys.excepthook(*exc_info)
            return

        progress = PaddedProgressDialog(self, text_for_width_calculation='Downloading factory calibration for IMU Brick')
        samba.progress = progress
        current_text = self.combo_firmware.currentText()

        # Get firmware
        name = None
        version = None

        if current_text == SELECT:
            return
        elif current_text == CUSTOM:
            firmware_file_name = self.edit_custom_firmware.text()
            try:
                with open(firmware_file_name, 'rb') as f:
                    firmware = f.read()
            except IOError:
                progress.cancel()
                self.popup_fail('Brick', 'Could not read firmware file')
                return
        else:
            url_part = self.combo_firmware.itemData(self.combo_firmware.currentIndex())
            name = self.firmware_infos[url_part].name
            version = self.combo_firmware_version.currentData()

            url = FIRMWARE_URL + 'bricks/{0}/brick_{0}_firmware_{1}_{2}_{3}.bin'.format(url_part, *version)

            firmware = self.download_file(url, '{0} Brick firmware {1}.{2}.{3}'.format(name, *version), progress_dialog=progress)
            if firmware is None:
                return

        # Get IMU UID
        imu_uid = None
        imu_calibration = None
        lock_imu_calibration_pages = False

        if name == 'IMU':
            # IMU 1.0.9 and earlier have a bug in their flash locking that makes
            # them unlook the wrong pages. Therefore, the calibration pages
            # must not be locked for this versions
            if version[1] > 0 or (version[1] == 0 and version[2] > 9):
                lock_imu_calibration_pages = True

            try:
                imu_uid = base58encode(uid64_to_uid32(samba.read_uid64()))
            except SAMBAException as e:
                progress.cancel()
                self.popup_fail('Brick', 'Could read UID of IMU Brick: {0}'.format(str(e)))
                return
            except:
                exc_info = sys.exc_info()
                progress.cancel()
                # Report the exception without unwinding the call stack
                sys.excepthook(*exc_info)
                return

            result = QMessageBox.question(self, 'IMU Brick',
                                          'Restore factory calibration for IMU Brick [{0}] from tinkerforge.com?'.format(imu_uid),
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            # Download IMU calibration
            if result == QMessageBox.Yes:
                progress.reset('Downloading factory calibration for IMU Brick', 0)

                try:
                    imu_calibration_text = b''
                    response = urlopen(IMU_CALIBRATION_URL + '{0}.txt'.format(imu_uid), timeout=10)
                    chunk = response.read(1024)

                    while len(chunk) > 0:
                        imu_calibration_text += chunk
                        chunk = response.read(1024)

                    response.close()
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        imu_calibration_text = None
                        self.popup_ok('IMU Brick', 'No factory calibration for IMU Brick [{0}] available'.format(imu_uid))
                    else:
                        progress.cancel()
                        self.popup_fail('IMU Brick', 'Could not download factory calibration for IMU Brick [{0}]: {1}'.format(imu_uid, e))
                        return
                except urllib.error.URLError as e:
                    progress.cancel()
                    self.popup_fail('IMU Brick', 'Could not download factory calibration for IMU Brick [{0}]: {1}'.format(imu_uid, e))
                    return

                if imu_calibration_text is not None:
                    try:
                        imu_calibration_text = imu_calibration_text.decode('utf-8')
                    except UnicodeError as e:
                        progress.cancel()
                        self.popup_fail('IMU Brick', 'Could not decode factory calibration for IMU Brick [{0}]: {1}'.format(imu_uid, e))
                        return

                    if len(imu_calibration_text) == 0:
                        progress.cancel()
                        self.popup_fail('IMU Brick', 'Could not download factory calibration for IMU Brick [{0}]'.format(imu_uid))
                        return

                    try:
                        imu_calibration_matrix = parse_imu_calibration(imu_calibration_text)

                        # Ensure proper temperature relation
                        if imu_calibration_matrix[5][1][7] <= imu_calibration_matrix[5][1][3]:
                            imu_calibration_matrix[5][1][7] = imu_calibration_matrix[5][1][3] + 1

                        imu_calibration_array = imu_calibration_matrix[0][1][:6] + \
                                                imu_calibration_matrix[1][1][:3] + \
                                                imu_calibration_matrix[2][1][:6] + \
                                                imu_calibration_matrix[3][1][:3] + \
                                                imu_calibration_matrix[4][1][:6] + \
                                                imu_calibration_matrix[5][1][:8]

                        imu_calibration = struct.pack('<32h', *imu_calibration_array)
                    except Exception as e:
                        progress.cancel()
                        self.popup_fail('IMU Brick', 'Could not parse factory calibration for IMU Brick [{0}]: {1}'.format(imu_uid, e))
                        return

        progress.hideCancelButton()

        # Flash firmware
        def report_result(reboot_okay):
            if current_text == CUSTOM:
                if reboot_okay:
                    message = 'Successfully restarted Brick!'
                else:
                    message = 'Manual restart of Brick required!'
            else:
                if reboot_okay:
                    message = 'Successfully restarted {0} Brick!'.format(name)
                else:
                    message = 'Manual restart of {0} Brick required!'.format(name)

            if current_text == CUSTOM:
                self.popup_ok('Brick', 'Successfully flashed firmware.\n' + message)
            elif imu_calibration is not None:
                self.popup_ok('Brick',
                              'Successfully flashed {0} Brick firmware {1}.{2}.{3}.\n'.format(name, *version) +
                              'Successfully restored factory calibration.\n' + message)
            else:
                self.popup_ok('Brick',
                              'Successfully flashed {0} Brick firmware {1}.{2}.{3}.\n'.format(name, *version) +
                              message)

        try:
            samba.flash(firmware, imu_calibration, lock_imu_calibration_pages)
            # close serial device before showing dialog, otherwise exchanging
            # the brick while the dialog is open will force it to show up as ttyACM1
            samba = None
            progress.cancel()
            self.refresh_serial_ports()
            report_result(True)
        except SAMBARebootError as e:
            samba = None
            progress.cancel()
            self.refresh_serial_ports()
            report_result(False)
        except SAMBAException as e:
            samba = None
            progress.cancel()
            self.refresh_serial_ports()
            self.popup_fail('Brick', 'Could not flash Brick: {0}'.format(str(e)))
        except:
            exc_info = sys.exc_info()
            samba = None
            progress.cancel()
            self.refresh_serial_ports()
            # Report the exception without unwinding the call stack
            sys.excepthook(*exc_info)

        self.refresh_serial_ports()

    def firmware_save_esp32(self, port):
        progress = PaddedProgressDialog(self, text_for_width_calculation='Downloading factory calibration for IMU Brick')
        current_text = self.combo_firmware.currentText()

        # Get firmware
        name = None
        version = None

        if current_text == SELECT:
            return
        elif current_text == CUSTOM:
            firmware_file_name = self.edit_custom_firmware.text()

            try:
                with open(firmware_file_name, 'rb') as f:
                    firmware = f.read()
            except IOError:
                progress.cancel()
                self.popup_fail('Brick', 'Could not read firmware file')
                return
        else:
            url_part = self.combo_firmware.itemData(self.combo_firmware.currentIndex())
            name = self.firmware_infos[url_part].name
            version = self.combo_firmware_version.currentData()
            url = FIRMWARE_URL + 'bricks/{0}/brick_{0}_firmware_{1}_{2}_{3}.bin'.format(url_part, *version)
            firmware = self.download_file(url, '{0} Brick firmware {1}.{2}.{3}'.format(name, *version), progress_dialog=progress)

            if firmware == None:
                return

        progress.cancel()

        dialog = ESPToolDialog(self)
        dialog.resize(900, 600)
        dialog.show()

        esptool_print_callback_ref[0] = lambda *args, end='\n': dialog.add_text.emit(' '.join([str(arg) for arg in args]) + end)

        def esptool_handler():
            # Check efuses
            dialog.add_text.emit('===== Checking eFuses =====\n\n')

            try:
                esptool_main(['--port', port.path,
                              '--chip', 'esp32',
                              'check_efuses'])
            except BaseException as e:
                dialog.add_text.emit('\nERROR: [{0}] {1}\n\n===== Failure ====='.format(e.__class__.__name__, e))
                return

            if 'eFuses are configured correctly' not in dialog.text:
                dialog.add_text.emit('\nERROR: Could not check eFuses\n\n===== Failure =====')
                return

            # Erase flash
            dialog.add_text.emit('\n===== Erasing flash =====\n\n')

            try:
                esptool_main(['--port', port.path,
                              '--chip', 'esp32',
                              'erase_flash'])
            except BaseException as e:
                dialog.add_text.emit('\nERROR: [{0}] {1}\n\n===== Failure ====='.format(e.__class__.__name__, e))
                return

            if 'Chip erase completed successfully' not in dialog.text:
                dialog.add_text.emit('\nERROR: Could not erase flash\n\n===== Failure =====')
                return

            dialog.add_text.emit('\nSuccessfully erased flash\n')

            # Flash firmware
            esptool_firmware_ref[0] = firmware

            dialog.add_text.emit('\n===== Flashing firmware =====\n\n')

            try:
                esptool_main(['--port', port.path,
                              '--chip', 'esp32',
                              '--baud', '921600',
                              '--before', 'default_reset',
                              '--after', 'hard_reset',
                              'write_flash',
                              '--flash_mode', 'dio',
                              '--flash_freq', '40m',
                              '--flash_size', '16MB',
                              '0x1000',
                              '[firmware]'])
            except BaseException as e:
                dialog.add_text.emit('\nERROR: [{0}] {1}\n\n===== Failure ====='.format(e.__class__.__name__, e))
                return

            if 'Hash of data verified.' not in dialog.text:
                if current_text == CUSTOM:
                    text = '\nERROR: Could not flash firmware\n'
                else:
                    text = '\nERROR: Could not flash {0} Brick firmware {1}.{2}.{3}\n'.format(name, *version)

                text += '\n===== Failure =====\n'

                dialog.add_text.emit(text)
                return

            if current_text == CUSTOM:
                text = '\nSuccessfully flashed firmware\n'
            else:
                text = '\nSuccessfully flashed {0} Brick firmware {1}.{2}.{3}\n'.format(name, *version)

            text += '\n===== Success =====\n'
            text += '\nIMPORTANT: Please wait up to 60 seconds until the blue Status LED is blinking before disconnecting the USB cable'

            dialog.add_text.emit(text)

        esptool_thread = ThreadWithReturnValue(target=esptool_handler)
        esptool_thread.start()

        while True:
            response, exception = esptool_thread.join(timeout=1.0/60)

            if not esptool_thread.is_alive():
                break

            QApplication.processEvents()

        esptool_print_callback_ref[0] = None

        dialog.button.setEnabled(True)

    def read_current_uid(self):
        if self.current_bricklet_has_comcu() or self.current_bricklet_is_tng():
            return base58encode(self.current_bricklet_device().read_uid())

        brick = self.current_parent_device()
        port = self.current_bricklet_port()
        return self.parent.ipcon.read_bricklet_uid(brick, port)

    def uid_save_clicked(self):
        brick = self.current_parent_device()
        port = self.current_bricklet_port()
        uid = self.edit_uid.text()

        if len(uid) == 0:
            self.popup_fail('Bricklet', 'UID cannot be empty')
            return

        for c in uid:
            if c not in BASE58:
                self.popup_fail('Bricklet', "UID cannot contain '{0}'".format(c))
                return

        try:
            if base58decode(uid) > 0xFFFFFFFF:
                self.popup_fail('Bricklet', 'UID is too long')
                return
        except:
            self.popup_fail('Bricklet', 'UID is invalid')
            return

        try:
            if self.current_bricklet_has_comcu() or self.current_bricklet_is_tng():
                self.current_bricklet_device().write_uid(base58decode(uid))
            else:
                self.parent.ipcon.write_bricklet_uid(brick, port, uid)
        except Error as e:
            self.popup_fail('Bricklet', 'Could not write UID: ' + error_to_name(e))
            return

        try:
            uid_read = self.read_current_uid()
        except Error as e:
            self.popup_fail('Bricklet', 'Could not read written UID: ' + error_to_name(e))
            return

        if uid == uid_read:
            self.popup_ok('Bricklet', 'Successfully wrote UID.\nNew UID will be used after reset of the connected Brick.')
        else:
            self.popup_fail('Bricklet', 'Could not write UID: Verification failed')

    def uid_load_clicked(self):
        try:
            uid = self.read_current_uid()
        except Error as e:
            self.edit_uid.setText('')
            self.popup_fail('Bricklet', 'Could not read UID: ' + error_to_name(e))
            return

        self.edit_uid.setText(uid)

    def brick_changed(self, index):
        self.combo_port.clear()

        brick_info = self.combo_parent.itemData(index)

        if brick_info == None:
            return

        first_index = None

        # First display all of the standard ports of the Brick and add
        # Bricklet information if a Bricklet is connected
        for port in brick_info.bricklet_ports:
            if port in brick_info.connections_keys():
                bricklet_info = brick_info.connections_get(port)[0]

                if bricklet_info.flashable_like_bricklet:
                    if first_index == None:
                        first_index = self.combo_port.count()

                    name = '{0}: {1}'.format(port.upper(), bricklet_info.get_combo_item())
                    self.combo_port.addItem(name, (port, bricklet_info))
                    continue

            self.combo_port.addItem(port.upper(), (port, None))

        # Then we fill the non-standard ports (e.g. RPi or Isolator Bricklet)
        for port, bricklet_info in sorted(brick_info.connections_items()):
            if port in brick_info.bricklet_ports:
                continue

            if bricklet_info.flashable_like_bricklet:
                if first_index == None:
                    first_index = self.combo_port.count()

                name = '{0}: {1}'.format(port.upper(), bricklet_info.get_combo_item())
                self.combo_port.addItem(name, (port, bricklet_info))

        if first_index != None:
            self.combo_port.setCurrentIndex(first_index)

        self.update_ui_state()

    def port_changed(self, index, ignore_custom=False):
        self.update_ui_state()
        self.edit_uid.setText('')

        if not ignore_custom and len(self.edit_custom_plugin.text()) > 0:
            self.combo_plugin.setCurrentIndex(self.combo_plugin.count() - 1)
            return

        if index < 0:
            self.combo_plugin.setCurrentIndex(0)
            return

        port_info = self.combo_port.itemData(index)[1]

        if port_info == None or port_info.url_part == None or len(port_info.url_part) == 0:
            self.combo_plugin.setCurrentIndex(0)
            return

        i = self.combo_plugin.findData(port_info.url_part)
        if i < 0:
            self.combo_plugin.setCurrentIndex(0)
        else:
            self.combo_plugin.setCurrentIndex(i)


        self.edit_uid.setText(port_info.uid)

    def plugin_changed(self, _index):
        self.update_ui_state()
        url_part = self.combo_plugin.currentData()

        last_selected_plugin = self.combo_plugin_version.currentData()
        last_latest_plugin = self.combo_plugin_version.itemData(0)

        self.combo_plugin_version.clear()

        if url_part is None:
            self.last_plugin_url_part = url_part
            return

        for version in self.plugin_infos[url_part].firmware_versions:
            self.combo_plugin_version.addItem('{}.{}.{}'.format(*version), version)

        if self.last_plugin_url_part == url_part and last_selected_plugin != last_latest_plugin:
            idx = self.combo_plugin_version.findData(last_selected_plugin)
            self.combo_plugin_version.setCurrentIndex(idx)

        self.last_plugin_url_part = url_part

    def download_bricklet_plugin(self, progress, url_part, has_comcu, name, version):
        if has_comcu:
            file_ext = 'zbin'
        else:
            file_ext = 'bin'

        url = FIRMWARE_URL + 'bricklets/{0}/bricklet_{0}_firmware_{2}_{3}_{4}.{1}'.format(url_part, file_ext, *version)
        name = '{0} Bricklet plugin {1}.{2}.{3}'.format(name, *version)

        return self.download_file(url, name, progress_dialog=progress)

    def write_bricklet_plugin(self, plugin, brick, port, bricklet, name, progress, has_comcu):
        if has_comcu:
            return self.write_bricklet_plugin_comcu(plugin, bricklet, name, progress)

        if self.current_bricklet_is_tng():
            return self.write_bricklet_plugin_tng(plugin, bricklet, name, progress)

        return self.write_bricklet_plugin_classic(plugin, brick, port, bricklet, name, progress)

    def write_bricklet_plugin_tng(self, plugin, bricklet, name, progress):
        try:
            progress.setLabelText('Starting bootloader mode')
            progress.setMaximum(0)
            progress.setValue(0)
            progress.show()

            # Convert plugin back from list of bytes to something we can put in ZipFile
            zip_file = plugin

            try:
                zf = zipfile.ZipFile(io.BytesIO(zip_file), 'r')
            except Exception as e:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not read *.zbin file: {0}'.format(e))
                return False

            plugin_data = None
            is_tng = False

            for name in zf.namelist():
                if name.endswith('firmware.bin'):
                    plugin_data = zf.read(name)
                    break

            if plugin_data == None:
                progress.cancel()
                self.popup_fail('TNG Module', 'Could not find firmware in *.zbin file')
                return False

            # Now convert plugin to list of bytes
            plugin = plugin_data

            # For TNG fill with zeroes to make sure that plugin size is divisible by 64.
            plugin_len_rest = len(plugin) % 64
            if plugin_len_rest != 0:
                plugin += b'\0'*(64-plugin_len_rest)

            num_packets = len(plugin) // 64
            index_list = list(range(num_packets))

            progress.setLabelText('Writing plugin: ' + name)
            progress.setMaximum(len(index_list))
            progress.setValue(0)
            progress.show()

            for position in index_list:
                start = position * 64
                end = (position + 1) * 64

                try:
                    bricklet.set_write_firmware_pointer(start)
                    bricklet.write_firmware(plugin[start:end])
                except:
                    # retry block a second time
                    try:
                        bricklet.set_write_firmware_pointer(start)
                        bricklet.write_firmware(plugin[start:end])
                    except Exception as e:
                        progress.cancel()
                        self.popup_fail('TNG Module', 'Could not write firmware: {0}'.format(e))
                        return False

                progress.setValue(position)

            copy_status = bricklet.copy_firmware()
            if copy_status == 0:
                bricklet.reset()
                return True
            else:
                if copy_status == 1:
                    error_str = 'Device identifier incorrect (Error 1)'
                elif copy_status == 2:
                    error_str = 'Magic number incorrect (Error 2)'
                elif copy_status == 3:
                    error_str = 'Length malformed (Error 3)'
                elif copy_status == 4:
                    error_str = 'CRC mismatch (Error 4)'
                else: # unknown error case
                    error_str = 'Error ' + str(copy_status)

                progress.cancel()
                self.popup_fail('Bricklet', 'Could not flash firmware: ' + error_str)
                return False
        except:
            progress.cancel()
            sys.excepthook(*sys.exc_info())
            return False

    def set_comcu_bootloader_mode(self, bricklet, mode):
        counter = 0

        while True:
            try:
                return bricklet.set_bootloader_mode(mode)
            except:
                pass

            if counter == 10:
                break

            time.sleep(0.25)
            counter += 1

        return None

    def wait_for_comcu_bootloader_mode(self, bricklet, mode):
        counter = 0

        while True:
            try:
                if bricklet.get_bootloader_mode() == mode:
                    return True
            except:
                pass

            if counter == 10:
                break

            time.sleep(0.25)
            counter += 1

        return False

    def write_bricklet_plugin_comcu(self, plugin, bricklet, name, progress):
        try:
            progress.setLabelText('Starting bootloader mode')
            progress.setMaximum(0)
            progress.setValue(0)
            progress.show()

            # Convert plugin back from list of bytes to something we can put in ZipFile
            zip_file = plugin

            try:
                zf = zipfile.ZipFile(io.BytesIO(zip_file), 'r')
            except Exception as e:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not read *.zbin file: {0}'.format(e))
                return False

            plugin_data = None

            for name in zf.namelist():
                if name.endswith('firmware.bin'):
                    plugin_data = zf.read(name)
                    break

            if plugin_data == None:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not find firmware in *.zbin file')
                return False

            # Now convert plugin to list of bytes
            plugin = plugin_data
            regular_plugin_upto = -1

            for i in reversed(range(4, len(plugin)-12)):
                if plugin[i] == 0x12 and plugin[i-1] == 0x34 and plugin[i-2] == 0x56 and plugin[i-3] == 0x78:
                    regular_plugin_upto = i
                    break

            if regular_plugin_upto == -1:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not find magic number in firmware')
                return False

            XMC1_PAGE_SIZE = 256
            MAX_SKIPPED_ZERO_BYTES = 20 * 1024 # Theoretical worst-case maximum possible is ~23KiB.
            MAX_SKIPPED_PAGES = MAX_SKIPPED_ZERO_BYTES / XMC1_PAGE_SIZE

            plugin_len = len(plugin)

            if plugin_len % XMC1_PAGE_SIZE != 0:
                progress.cancel()
                self.popup_fail('Bricklet', 'Firmware size is not a multiple of the page size')
                return False

            flash_success = False

            for attempt in range(2):
                if attempt == 0:
                    attempt_str = ''
                    allow_skipping = True
                else:
                    attempt_str = ' (attempt ' + str(attempt + 1) + ')'
                    allow_skipping = False

                if self.set_comcu_bootloader_mode(bricklet, bricklet.BOOTLOADER_MODE_BOOTLOADER) == None or \
                not self.wait_for_comcu_bootloader_mode(bricklet, bricklet.BOOTLOADER_MODE_BOOTLOADER):
                    progress.cancel()
                    self.popup_fail('Bricklet', 'Device did not enter bootloader mode in 2.5 seconds' + attempt_str)
                    return False


                progress.setLabelText('Writing plugin' + attempt_str + ': ' + name)
                progress.setMaximum(plugin_len)
                progress.setValue(0)
                progress.show()

                skipped_pages = MAX_SKIPPED_PAGES + 1 # Force writing the first page.

                position = 0
                while position < plugin_len:
                    # Don't allow skipping the last page.
                    if allow_skipping and skipped_pages < MAX_SKIPPED_PAGES and plugin_len - position > XMC1_PAGE_SIZE and all(b == 0 for b in plugin[position:position+XMC1_PAGE_SIZE]):
                        skipped_pages += 1
                        position += XMC1_PAGE_SIZE
                        continue

                    skipped_pages = 0

                    for block_offset in range(0, XMC1_PAGE_SIZE, 64):
                        block_start = position + block_offset
                        block_end = block_start + 64

                        # retry block a three times to recover from Co-MCU bootloader
                        # bug that results in lost request, especially when used in
                        # combination with an Isolator Bricklet
                        last_exception = None
                        for subpage_attempt in range(3):
                            try:
                                bricklet.set_write_firmware_pointer(block_start)
                                bricklet.write_firmware(plugin[block_start:block_end])
                                last_exception = None
                                break
                            except Exception as e:
                                last_exception = e

                        if last_exception is not None:
                            progress.cancel()
                            self.popup_fail('Bricklet', 'Could not write plugin: {0}'.format(last_exception))
                            return False

                    position += XMC1_PAGE_SIZE
                    progress.setValue(position)

                progress.setLabelText('Changing from bootloader mode to firmware mode' + attempt_str)
                progress.setMaximum(0)
                progress.setValue(0)
                progress.show()

                mode_ret = self.set_comcu_bootloader_mode(bricklet, bricklet.BOOTLOADER_MODE_FIRMWARE)

                if mode_ret == None:
                    progress.cancel()
                    self.popup_fail('Bricklet', 'Device did not enter firmware mode in 2.5 seconds')
                    return False

                if mode_ret == 0 or mode_ret == 2: # 0 = ok, 2 = no change
                    flash_success = True
                    break

                if mode_ret == 1:
                    error_str = 'Invalid mode (Error 1)'
                elif mode_ret == 3:
                    error_str = 'Entry function not present (Error 3)'
                elif mode_ret == 4:
                    error_str = 'Device identifier incorrect (Error 4)'
                elif mode_ret == 5:
                    error_str = 'CRC Mismatch (Error 5)'
                else: # unknown error case
                    error_str = 'Error ' + str(mode_ret)

                # In case of CRC error we try again with whole firmware.
                # If there happens to be garbage data between the actual firmware and the
                # firmware data at the end of the flash, the CRC does not match and we have
                # to overwrite it with zeros.
                # This sometimes seems to be the case with fresh XMCs. This should not
                # happen according to the specification in the datasheet...
                if mode_ret == 5:
                    continue

                progress.cancel()
                self.popup_fail('Bricklet', 'Could not change from bootloader mode to firmware mode: ' + error_str)
                return False

            if not flash_success: # CRC failed after all attempts
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not change from bootloader mode to firmware mode: ' + error_str)
                return False

            if not self.wait_for_comcu_bootloader_mode(bricklet, bricklet.BOOTLOADER_MODE_FIRMWARE):
                progress.cancel()
                self.popup_fail('Bricklet', 'Device did not enter firmware mode in 2.5 seconds')
                return False

            return True
        except:
            progress.cancel()
            sys.excepthook(*sys.exc_info())
            return False

    def write_bricklet_plugin_classic(self, plugin, brick, port, _bricklet, name, progress):
        if len(plugin) > 4084:
            progress.cancel()
            self.popup_fail('Bricklet', 'Could not write Bricklet plugin: Plugin is larger than 4084 bytes (the maximum plugin size for classic Bricklets).')
            return

        # Write
        progress.setLabelText('Writing plugin: ' + name)
        progress.setMaximum(0)
        progress.setValue(0)
        progress.show()

        plugin_chunk_size = 32
        plugin_chunks = []
        offset = 0

        # it's okay to use the Master Brick constant here, because this function
        # is on the same function ID (246) for all Bricks.
        brick.set_response_expected(BrickMaster.FUNCTION_WRITE_BRICKLET_PLUGIN, True)

        while offset < len(plugin):
            chunk = plugin[offset:offset + plugin_chunk_size]

            if len(chunk) < plugin_chunk_size:
                chunk += bytes([0]) * (plugin_chunk_size - len(chunk))

            plugin_chunks.append(chunk)
            offset += plugin_chunk_size

        progress.setMaximum(len(plugin_chunks))

        position = 0

        for chunk in plugin_chunks:
            try:
                brick.write_bricklet_plugin(port, position, chunk)
            except Error as e:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not write Bricklet plugin: ' + error_to_name(e))
                return False

            position += 1
            progress.setValue(position)

            time.sleep(0.015)
            QApplication.processEvents()

        time.sleep(0.1)

        # Verify
        progress.setLabelText('Verifying written plugin: ' + name)
        progress.setMaximum(len(plugin_chunks))
        progress.setValue(0)
        progress.show()

        time.sleep(0.1)
        position = 0

        for chunk in plugin_chunks:
            try:
                read_chunk = bytes(brick.read_bricklet_plugin(port, position))
            except Error as e:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not read Bricklet plugin back for verification: ' + error_to_name(e))
                return False

            if read_chunk != chunk:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not flash Bricklet plugin: Verification error')
                return False

            position += 1
            progress.setValue(position)

            time.sleep(0.015)
            QApplication.processEvents()

        return True

    def plugin_save_clicked(self):
        progress = PaddedProgressDialog(self)
        current_text = self.combo_plugin.currentText()

        # Get plugin
        if current_text == SELECT:
            return
        elif current_text == CUSTOM:
            plugin_file_name = self.edit_custom_plugin.text()

            try:
                with open(plugin_file_name, 'rb') as f:
                    plugin = f.read()
            except IOError:
                progress.cancel()
                self.popup_fail('Bricklet', 'Could not read plugin file')
                return
        else:
            url_part = self.combo_plugin.itemData(self.combo_plugin.currentIndex())
            plugin_info = self.plugin_infos[url_part]
            name = plugin_info.name
            version = self.combo_plugin_version.currentData()
            plugin = self.download_bricklet_plugin(progress, url_part, self.current_bricklet_has_comcu(), name, version)

            if plugin == None:
                return

        progress.hideCancelButton()

        # Flash plugin
        port = self.current_bricklet_port()
        brick = self.current_parent_device()
        bricklet = self.current_bricklet_device()
        has_comcu = self.current_bricklet_has_comcu()

        if current_text == CUSTOM:
            if not self.write_bricklet_plugin(plugin, brick, port, bricklet, os.path.split(plugin_file_name)[-1], progress, has_comcu):
                return
        else:
            if not self.write_bricklet_plugin(plugin, brick, port, bricklet, name, progress, has_comcu):
                return

        progress.cancel()

        if has_comcu:
            message_tail = ''
        else:
            message_tail = '\nNew plugin will be used after reset of the connected Brick.'

        if current_text == CUSTOM:
            self.popup_ok('Bricklet', 'Successfully flashed plugin.{0}'.format(message_tail))
        else:
            self.popup_ok('Bricklet', 'Successfully flashed {0} Bricklet plugin {2}.{3}.{4}.{1}'.format(name, message_tail, *version))

    def current_bricklet_info(self):
        try:
            return self.combo_port.itemData(self.combo_port.currentIndex())[1]
        except:
            return None

    def current_bricklet_port(self):
        try:
            return self.combo_port.itemData(self.combo_port.currentIndex())[0]
        except:
            return None

    def current_parent_info(self):
        try:
            return self.combo_parent.itemData(self.combo_parent.currentIndex())
        except:
            return None

    def current_parent_plugin(self):
        try:
            return self.current_parent_info().plugin
        except:
            return None

    def current_parent_device(self):
        try:
            return self.current_parent_plugin().device
        except:
            return None

    def current_bricklet_plugin(self):
        try:
            return self.current_bricklet_info().plugin
        except:
            return None

    def current_bricklet_device(self):
        try:
            return self.current_bricklet_plugin().device
        except:
            return None

    def current_bricklet_has_comcu(self):
        try:
            return self.current_bricklet_plugin().has_comcu
        except:
            return False

    def current_bricklet_is_tng(self):
        try:
            return self.current_bricklet_plugin().is_tng
        except:
            return False

    def plugin_browse_clicked(self):
        if self.current_bricklet_has_comcu() or self.current_bricklet_is_tng():
            file_ending = '*.zbin'
        else:
            file_ending = '*.bin'

        last_dir = get_home_path()

        if len(self.edit_custom_plugin.text()) > 0:
            last_dir = os.path.dirname(os.path.realpath(self.edit_custom_plugin.text()))

        filename = get_open_file_name(self, 'Open Plugin', last_dir, 'Firmwares({});;All Files(*)'.format(file_ending))

        if len(filename) > 0:
            self.edit_custom_plugin.setText(filename)

    def auto_update_bricklets_clicked(self):
        def brick_for_bricklet(bricklet):
            return bricklet.reverse_connection

        progress = PaddedProgressDialog(self)
        progress.setLabelText('Auto-Updating Bricklets')
        progress.hideCancelButton()

        bricks_to_reset = set()

        for device_info in inventory.get_bricklet_infos():
            if device_info.firmware_version_installed < device_info.firmware_version_latest:
                plugin = self.download_bricklet_plugin(progress, device_info.url_part, device_info.plugin.has_comcu, device_info.name, device_info.firmware_version_latest)

                if plugin == None:
                    progress.cancel()
                    self.refresh_updates_clicked()
                    return

                brick = brick_for_bricklet(device_info)

                if brick != None and brick.plugin != None:
                    brick_plugin_device = brick.plugin.device
                else:
                    brick_plugin_device = None

                if self.write_bricklet_plugin(plugin, brick_plugin_device, device_info.position, device_info.plugin.device, device_info.name, progress, device_info.plugin.has_comcu):
                    bricks_to_reset.add(brick)
                else:
                    self.refresh_updates_clicked()
                    return

        for brick in bricks_to_reset:
            try:
                brick.plugin.device.reset()
            except:
                pass

        progress.cancel()

        if any(brick.firmware_version_installed < brick.firmware_version_latest for brick in inventory.get_brick_infos()):
            self.popup_ok("Brick firmware updates available.", "There are Brick firmware updates available.")

    def tab_changed(self, i):
        if self.ignore_tab_changed_event:
            return

        if i == 0 and self.refresh_updates_pending:
            self.refresh_updates_clicked()
        elif i == 2:
            self.brick_changed(self.combo_parent.currentIndex())
            self.port_changed(self.combo_port.currentIndex())
        elif i == 3:
            self.extension_changed(self.combo_extension.currentIndex())

    def refresh_updates_clicked(self, force=False):
        if not force and self.tab_widget.currentIndex() != 0:
            self.refresh_updates_pending = True
            return

        self.update_button_refresh.setDisabled(True)
        self.button_update_firmware_list.setDisabled(True)
        self.button_update_plugin_list.setDisabled(True)
        self.button_update_ext_firmware_list.setDisabled(True)

        self.refresh_updates_pending = False
        self.fw_fetch_progress_bar = PaddedProgressDialog(self, 'Discovering latest versions on tinkerforge.com')

        self.refresh_latest_version_info()

    def refresh_update_tree_view(self):
        def get_color_for_device(device):
            if device.firmware_version_installed >= device.firmware_version_latest:
                return None, False

            if device.firmware_version_installed == (0, 0, 0):
                return None, False

            return QBrush(QColor(255, 160, 55)), True

        self.load_version_info(inventory.get_latest_fws())

        if self.fw_fetch_progress_bar is not None:
            self.fw_fetch_progress_bar.cancel()
            self.fw_fetch_progress_bar = None

        sis = self.update_tree_view.header().sortIndicatorSection()
        sio = self.update_tree_view.header().sortIndicatorOrder()

        self.update_tree_view_model.clear()
        self.update_tree_view_model.setHorizontalHeaderLabels(self.update_tree_view_model_labels)

        is_update = False

        def get_row(info, ignore_update=False):
            nonlocal is_update
            inst_replacement = '0.0.0'
            unknown_replacement = 'Unknown'

            if info.url_part == 'wifi_v2' or info.kind == 'tool' or info.kind == 'bindings':
                inst_replacement = "Querying..."
            elif info.kind == "extension":
                inst_replacement = ""
                unknown_replacement = ''

            row = [QStandardItem(info.name),
                   QStandardItem(info.uid if hasattr(info, 'uid') else ''),
                   QStandardItem(info.position.title() if hasattr(info, 'position') else ''),
                   QStandardItem(get_version_string(info.firmware_version_installed, replace_unknown=inst_replacement)),
                   QStandardItem(get_version_string(info.firmware_version_latest, replace_unknown=unknown_replacement))]

            color, update = get_color_for_device(info)
            if ignore_update:
                color, update = None, False

            if update and info.kind != "extension":
                is_update = True

            for item in row:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(color, Qt.BackgroundRole)

            return row

        def recurse_on_device(info, insertion_point):
            row = get_row(info)
            insertion_point.appendRow(row)

            for child in info.connections_values():
                recurse_on_device(child, row[0])

            if info.can_have_extension:
                for extension in info.extensions.values():
                    if extension is None:
                        continue
                    ext_row = get_row(extension)
                    if extension.url_part != 'wifi_v2':
                        for item in ext_row:
                            item.setData(QBrush(QColor(0x80, 0x80, 0x80)), Qt.ForegroundRole)
                    row[0].appendRow(ext_row)

        def recurse_on_chilren(info, row):
            for child in info.connections_values():
                recurse_on_device(child, row[0])

            if info.can_have_extension:
                for extension in info.extensions.values():
                    if extension is None:
                        continue
                    ext_row = get_row(extension)
                    if extension.url_part != 'wifi_v2':
                        for item in ext_row:
                            item.setData(QBrush(QColor(0x80, 0x80, 0x80)), Qt.ForegroundRole)
                    row[0].appendRow(ext_row)

        to_collapse = []

        for info in inventory.get_infos():
            if isinstance(info, DeviceInfo):
                # If a device has a reverse connection, it will be handled as a child below.
                if info.reverse_connection != None:
                    continue

                is_red_brick = isinstance(info, BrickREDInfo)

                if is_red_brick:
                    replace_unknown = 'Querying...'
                else:
                    replace_unknown = None

                parent = [QStandardItem(info.name),
                          QStandardItem(info.uid),
                          QStandardItem(info.position.title()),
                          QStandardItem(get_version_string(info.firmware_version_installed, replace_unknown=replace_unknown, is_red_brick=is_red_brick)),
                          QStandardItem(get_version_string(info.firmware_version_latest, replace_unknown="Unknown", is_red_brick=is_red_brick))]

                color, update = get_color_for_device(info)

                if update and (info.kind == 'bricklet' or info.kind == 'tng'):
                    is_update = True

                for item in parent:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    item.setData(color, Qt.BackgroundRole)

                parent[0].setData(info.uid, Qt.UserRole)
                self.update_tree_view_model.appendRow(parent)

                recurse_on_chilren(info, parent)

                if is_red_brick:
                    # Cache is_update state and restore after handling bindings. They should not enable the update all bindings button.
                    old_is_update = is_update

                    brickv_row = get_row(info.brickv_info, ignore_update=info.firmware_version_installed < (1, 14, 0))

                    is_update = False

                    # Use cached latest fw, as the one in info.brickv_info is not updated when still querying
                    row_color = brickv_row[4].data(Qt.BackgroundRole)
                    brickv_version = self.tool_infos['brickv'].firmware_version_latest if 'brickv' in self.tool_infos else (0, 0, 0)
                    brickv_row[4] = QStandardItem(get_version_string(brickv_version, replace_unknown="Unknown"))
                    brickv_row[4].setData(row_color, Qt.BackgroundRole)
                    parent[0].appendRow(brickv_row)

                    installed_bindings_string = 'Querying...' if len(info.bindings_infos) == 0 else ''
                    binding_row = [QStandardItem('Bindings'), QStandardItem(''), QStandardItem(''), QStandardItem(installed_bindings_string), QStandardItem('')]

                    for binding in info.bindings_infos:
                        child = get_row(binding)
                        binding_row[0].appendRow(child)

                    for item in binding_row:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        if is_update:
                            item.setData(QBrush(QColor(255, 160, 55)), Qt.BackgroundRole)

                    parent[0].appendRow(binding_row)

                    index = self.update_tree_view_proxy_model.mapFromSource(binding_row[0].index())

                    to_collapse.append(index)

                    # Restore cached is_update state, see above.
                    is_update = old_is_update

            elif info.kind == 'tool' and 'Brick Viewer' in info.name:
                parent = [QStandardItem(info.name),
                          QStandardItem(''),
                          QStandardItem(''),
                          QStandardItem(get_version_string(info.firmware_version_installed)),
                          QStandardItem(get_version_string(info.firmware_version_latest, replace_unknown="Unknown"))]

                color, update = get_color_for_device(info)

                if update:
                    self.label_update_tool.show()
                else:
                    self.label_update_tool.hide()

                for item in parent:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    item.setData(color, Qt.BackgroundRole)

                self.update_tree_view_model.appendRow(parent)

        # Disable collapse animation temporarily, as it would be visible when the user opens the flashing window.
        self.update_tree_view.setAnimated(False)
        self.update_tree_view.expandAll()

        for model_idx in to_collapse:
            self.update_tree_view.collapse(model_idx)

        self.update_tree_view.setAnimated(True)

        self.update_tree_view.setColumnWidth(0, 280)
        self.update_tree_view.setColumnWidth(1, 70)
        self.update_tree_view.setColumnWidth(2, 90)
        self.update_tree_view.setColumnWidth(3, 105)
        self.update_tree_view.setColumnWidth(4, 105)
        self.update_tree_view.setSortingEnabled(True)
        self.update_tree_view.header().setSortIndicator(sis, sio)

        if is_update and self.ipcon_available:
            self.update_button_bricklets.setEnabled(True)
        else:
            self.update_button_bricklets.setEnabled(False)

        self.brick_changed(self.combo_parent.currentIndex())

    def extension_changed(self, index, ignore_custom=False):
        if index < 0:
            self.combo_extension.setCurrentIndex(0)
            return

        if not ignore_custom and len(self.edit_custom_extension_firmware.text()) > 0:
            self.combo_extension_firmware.setCurrentIndex(self.combo_extension_firmware.count() - 1)
            return

        itemData = self.combo_extension.itemData(index)

        if itemData == None:
            url_part = None
        else:
            url_part = itemData[0]

        if url_part == None or len(url_part) == 0:
            self.combo_extension_firmware.setCurrentIndex(0)
            return

        i = self.combo_extension_firmware.findData(url_part)

        if i < 0:
            self.combo_extension_firmware.setCurrentIndex(0)
        else:
            self.combo_extension_firmware.setCurrentIndex(i)

        self.update_ui_state()

        url_part = self.combo_extension_firmware.currentData()

        last_selected_extension_firmware = self.combo_extension_firmware_version.currentData()
        last_latest_extension_firmware = self.combo_extension_firmware_version.itemData(0)

        self.combo_extension_firmware_version.clear()

        if url_part is None:
            self.last_extension_firmware_url_part = url_part
            return

        for version in self.extension_firmware_infos[url_part].firmware_versions:
            self.combo_extension_firmware_version.addItem('{}.{}.{}'.format(*version), version)

        if self.last_extension_firmware_url_part == url_part and last_selected_extension_firmware != last_latest_extension_firmware:
            idx = self.combo_extension_firmware_version.findData(last_selected_extension_firmware)
            self.combo_extension_firmware_version.setCurrentIndex(idx)

        self.last_extension_firmware_url_part = url_part

    def extension_firmware_changed(self, _index):
        self.update_ui_state()

    def extension_firmware_save_clicked(self):
        # FIXME: check Master.get_connection_type()

        current_text = self.combo_extension_firmware.currentText()
        progress = PaddedProgressDialog(self)

        if current_text == SELECT:
            return
        elif current_text == CUSTOM:
            firmware_file_name = self.edit_custom_extension_firmware.text()

            if not zipfile.is_zipfile(firmware_file_name):
                progress.cancel()
                self.popup_fail('Extension Firmware', 'Firmware file does not have correct format')
                return

            try:
                with open(firmware_file_name, 'rb') as f:
                    firmware = f.read()
            except IOError:
                progress.cancel()
                self.popup_fail('Extension Firmware', 'Could not read firmware file')
                return

            name = None
            version = None
        else:
            url_part = self.combo_extension_firmware.itemData(self.combo_extension_firmware.currentIndex())
            name = self.extension_firmware_infos[url_part].name
            version = self.combo_extension_firmware_version.currentData()

            url = FIRMWARE_URL + 'extensions/{0}/extension_{0}_firmware_{1}_{2}_{3}.zbin'.format(url_part, *version)
            firmware = self.download_file(url, '{0} Extension firmware {1}.{2}.{3}'.format(name, *version), progress_dialog=progress)

            if not firmware:
                return

        progress.hideCancelButton()
        progress.reset('Connecting to bootloader', 0)
        progress.update(0)

        extension_info = self.extension_infos[self.combo_extension.currentIndex()]
        master = None

        # Find master from infos again, our info object may be outdated at this point
        for info in inventory.get_brick_infos():
            if info.uid == extension_info.master_info.uid:
                master = info.plugin.device

        if master == None:
            progress.cancel()
            self.popup_fail('Extension Firmware', 'Error during Extension flashing: Could not find choosen Master Brick')
            return

        try:
            ESPFlash(master, progress).flash(firmware)
        except FatalError as e:
            progress.cancel()
            self.popup_fail('Extension Firmware', 'Error during Extension flashing: {0}'.format(e))
            return
        except:
            progress.cancel()
            sys.excepthook(*sys.exc_info())
            return

        progress.cancel()
        master.reset()

        if name != None and version != None:
            self.popup_ok('Extension Firmware', 'Successfully flashed {0} Extension firmware {1}.{2}.{3}.\nMaster Brick will now restart automatically.'.format(name, *version))
        else:
            self.popup_ok('Extension Firmware', 'Successfully flashed Extension firmware.\nMaster Brick will now restart automatically.')

    def extension_firmware_browse_clicked(self):
        if len(self.edit_custom_extension_firmware.text()) > 0:
            last_dir = os.path.dirname(os.path.realpath(self.edit_custom_extension_firmware.text()))
        else:
            last_dir = get_home_path()

        filename = get_open_file_name(self, 'Open Extension Firmware', last_dir, 'Firmwares(*.zbin);;All Files(*)')

        if len(filename) > 0:
            self.edit_custom_extension_firmware.setText(filename)

    def update_extensions(self):
        self.extension_infos = []
        self.combo_extension.clear()
        items = {}

        for info in inventory.get_extension_infos():
            if info.extension_type == BrickMaster.EXTENSION_TYPE_WIFI2:
                items[info.get_combo_item()] = info

        for item in sorted(items.keys()):
            self.extension_infos.append(items[item])
            self.combo_extension.addItem(item, (items[item].url_part, items[item].master_info.uid))

        if self.combo_extension.count() == 0:
            self.combo_extension.addItem(NO_EXTENSION, ('', '0'))

        self.update_ui_state()

    def show_brick_update(self, url_part):
        self.tab_widget.setCurrentWidget(self.tab_brick)
        self.refresh_serial_ports()

        try:
            idx = [self.combo_firmware.itemData(i) for i in range(self.combo_firmware.count())].index(url_part)
        except ValueError:
            idx = -1

        if idx >= 0:
            # Remove user selected version to ensure, that the latest version is preselected
            self.last_firmware_url_part = ""
            self.combo_firmware.setCurrentIndex(idx)

    def show_bricklet_update(self, parent_uid, port):
        self.tab_widget.setCurrentWidget(self.tab_bricklet)

        idx = -1
        for i in range(self.combo_parent.count()):
            data = self.combo_parent.itemData(i)
            if data is not None and data.uid == parent_uid:
                idx = i
                break

        if idx >= 0:
            self.combo_parent.setCurrentIndex(idx)
            self.brick_changed(idx)

        try:
            idx = [self.combo_port.itemData(i)[0] for i in range(self.combo_port.count())].index(port)
        except ValueError:
            idx = -1

        if idx >= 0:
            # Remove user selected version to ensure, that the latest version is preselected
            self.last_plugin_url_part = ""
            self.combo_port.setCurrentIndex(idx)
            self.port_changed(idx, ignore_custom=True)

    def show_extension_update(self, master_uid):
        self.tab_widget.setCurrentWidget(self.tab_extension)

        try:
            idx = [self.combo_extension.itemData(i)[1] for i in range(self.combo_extension.count())].index(master_uid)
        except ValueError:
            idx = -1

        if idx >= 0:
            # Remove user selected version to ensure, that the latest version is preselected
            self.last_extension_firmware_url_part = ""
            self.combo_extension.setCurrentIndex(idx)
            self.extension_changed(idx, ignore_custom=True)

    def show_red_brick_update(self):
        get_main_window().show_red_brick_update()

    def set_ipcon_available(self, ipcon_available):
        last_ipcon_available = self.ipcon_available

        self.ipcon_available = ipcon_available

        if last_ipcon_available != ipcon_available:
            # ensure auto-update button has correct state
            self.refresh_update_tree_view()

        self.update_ui_state()

    def set_auto_search_for_updates(self, enable):
        self.label_firmware_a.setVisible(not enable)
        self.label_firmware_b.setVisible(enable)
        self.button_update_firmware_list.setVisible(not enable)

        self.label_plugin_a.setVisible(not enable)
        self.label_plugin_b.setVisible(enable)
        self.button_update_plugin_list.setVisible(not enable)

        self.label_ext_firmware_a.setVisible(not enable)
        self.label_ext_firmware_b.setVisible(enable)
        self.button_update_ext_firmware_list.setVisible(not enable)
