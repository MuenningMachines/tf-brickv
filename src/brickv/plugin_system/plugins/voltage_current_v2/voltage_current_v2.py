# -*- coding: utf-8 -*-
"""
Voltage/Current 2.0 Plugin
Copyright (C) 2018 Olaf Lüke <olaf@tinkerforge.com>
Copyright (C) 2018 Ishraq Ibne Ashraf <ishraq@tinkerforge.com>

voltage_current_v2.py: Voltage/Current 2.0 Plugin Implementation

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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QDialog

from brickv.bindings.bricklet_voltage_current_v2 import BrickletVoltageCurrentV2
from brickv.plugin_system.plugins.voltage_current_v2.ui_voltage_current_v2 import Ui_VoltageCurrentV2
from brickv.plugin_system.plugins.voltage_current_v2.ui_calibration import Ui_Calibration
from brickv.plugin_system.comcu_plugin_base import COMCUPluginBase
from brickv.plot_widget import PlotWidget, CurveValueWrapper
from brickv.async_call import async_call
from brickv.callback_emulator import CallbackEmulator
from brickv.utils import format_voltage, format_current
from brickv.utils import get_modeless_dialog_flags

def format_power(value): # float, W
    if abs(value) < 1:
        return str(int(round(value * 1000.0))) + ' mW'
    else:
        return format(value, '.3f') + ' W'

class Calibration(QDialog, Ui_Calibration):
    def __init__(self, parent):
        QDialog.__init__(self, parent, get_modeless_dialog_flags())
        self.parent = parent

        self.setupUi(self)

        # Synced voltage, current and power. Updated with callbacks.
        self.voltage = 0
        self.current = 0
        self.power = 0

        # Synced calibration parameters. Updated with get_calibration() calls.
        self.cal_v_mul = 1
        self.cal_v_div = 1
        self.cal_c_mul = 1
        self.cal_c_div = 1

        self.btn_cal_v.clicked.connect(self.cal_v_clicked)
        self.btn_cal_c.clicked.connect(self.cal_c_clicked)
        self.btn_cal_rst.clicked.connect(self.cal_rst_clicked)
        self.btn_close.clicked.connect(self.close)

        self.cbe_voltage = CallbackEmulator(self.parent.vc.get_voltage,
                                            None,
                                            self.cb_voltage,
                                            self.parent.increase_error_count)

        self.cbe_current = CallbackEmulator(self.parent.vc.get_current,
                                            None,
                                            self.cb_current,
                                            self.parent.increase_error_count)

        self.cbe_power = CallbackEmulator(self.parent.vc.get_power,
                                          None,
                                          self.cb_power,
                                          self.parent.increase_error_count)

    def show(self):
        QDialog.show(self)

        self.cbe_voltage.set_period(100)
        self.cbe_current.set_period(100)
        self.cbe_power.set_period(100)

        async_call(self.parent.vc.get_calibration,
                   None,
                   self.get_calibration_async,
                   self.parent.increase_error_count)

    def cal_rst_clicked(self):
        self.parent.vc.set_calibration(1, 1, 1, 1)

        async_call(self.parent.vc.get_calibration,
                   None,
                   self.get_calibration_async,
                   self.parent.increase_error_count)

    def cal_v_clicked(self):
        self.parent.vc.set_calibration(self.sbox_cal_v_mul.value(), self.voltage, 1, 1)

        async_call(self.parent.vc.get_calibration,
                   None,
                   self.get_calibration_async,
                   self.parent.increase_error_count)

    def cal_c_clicked(self):
        self.parent.vc.set_calibration(self.cal_v_mul,
                                       self.cal_v_div,
                                       self.sbox_cal_c_mul.value(),
                                       self.current)

        async_call(self.parent.vc.get_calibration,
                   None,
                   self.get_calibration_async,
                   self.parent.increase_error_count)

    def get_calibration_async(self, cal):
        self.cal_v_mul = cal.voltage_multiplier
        self.cal_v_div = cal.voltage_divisor
        self.cal_c_mul = cal.current_multiplier
        self.cal_c_div = cal.current_divisor

        self.sbox_cal_v_mul.setValue(self.cal_v_mul)
        self.sbox_cal_c_mul.setValue(self.cal_c_mul)

    def cb_voltage(self, voltage):
        self.voltage = voltage

        if (self.voltage / 1000.0) < 1.0:
            self.lbl_voltage.setText(str(self.voltage) + ' mV')
        else:
            self.lbl_voltage.setText(str(self.voltage / 1000.0) + ' V')

    def cb_current(self, current):
        self.current = current

        if (self.current / 1000.0) < 1.0:
            self.lbl_current.setText(str(self.current) + ' mA')
        else:
            self.lbl_current.setText(str(self.current / 1000.0) + ' A')

    def cb_power(self, power):
        self.power = power

        if (self.power / 1000.0) < 1.0:
            self.lbl_power.setText(str(self.power) + ' mW')
        else:
            self.lbl_power.setText(str(self.power / 1000.0) + ' W')

    def closeEvent(self, event):
        self.cbe_voltage.set_period(0)
        self.cbe_current.set_period(0)
        self.cbe_power.set_period(0)
        self.parent.button_calibration.setEnabled(True)

class VoltageCurrentV2(COMCUPluginBase, Ui_VoltageCurrentV2):
    def __init__(self, *args):
        COMCUPluginBase.__init__(self, BrickletVoltageCurrentV2, *args)

        self.setupUi(self)

        self.vc = self.device

        self.cbe_voltage = CallbackEmulator(self.vc.get_voltage,
                                            None,
                                            self.cb_voltage,
                                            self.increase_error_count)
        self.cbe_current = CallbackEmulator(self.vc.get_current,
                                            None,
                                            self.cb_current,
                                            self.increase_error_count)
        self.cbe_power = CallbackEmulator(self.vc.get_power,
                                          None,
                                          self.cb_power,
                                          self.increase_error_count)

        self.current_voltage = CurveValueWrapper() # float, V
        self.current_current = CurveValueWrapper() # float, A
        self.current_power = CurveValueWrapper() # float, W

        plots_voltage = [('Voltage', Qt.red, self.current_voltage, format_voltage)]
        plots_current = [('Current', Qt.blue, self.current_current, format_current)]
        plots_power = [('Power', Qt.darkGreen, self.current_power, format_power)]
        self.plot_widget_voltage = PlotWidget('Voltage [V]', plots_voltage, clear_button=self.button_clear_graphs, y_resolution=0.001)
        self.plot_widget_current = PlotWidget('Current [A]', plots_current, clear_button=self.button_clear_graphs, y_resolution=0.001)
        self.plot_widget_power = PlotWidget('Power [W]', plots_power, clear_button=self.button_clear_graphs, y_resolution=0.001)

        self.save_conf_button.clicked.connect(self.save_conf_clicked)

        self.calibration = None
        self.button_calibration.clicked.connect(self.calibration_clicked)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.plot_widget_voltage)
        hlayout.addWidget(self.plot_widget_current)
        hlayout.addWidget(self.plot_widget_power)

        self.main_layout.insertLayout(0, hlayout)

    def get_configuration_async(self, conf):
        avg, vol, cur = conf
        self.averaging_box.setCurrentIndex(avg)
        self.voltage_box.setCurrentIndex(vol)
        self.current_box.setCurrentIndex(cur)

    def start(self):
        async_call(self.vc.get_configuration, None, self.get_configuration_async, self.increase_error_count)

        self.cbe_current.set_period(100)
        self.cbe_voltage.set_period(100)
        self.cbe_power.set_period(100)

        self.plot_widget_current.stop = False
        self.plot_widget_voltage.stop = False
        self.plot_widget_power.stop = False

    def stop(self):
        self.cbe_current.set_period(0)
        self.cbe_voltage.set_period(0)
        self.cbe_power.set_period(0)

        self.plot_widget_current.stop = True
        self.plot_widget_voltage.stop = True
        self.plot_widget_power.stop = True

    def destroy(self):
        if self.calibration != None:
            self.calibration.close()

    @staticmethod
    def has_device_identifier(device_identifier):
        return device_identifier == BrickletVoltageCurrentV2.DEVICE_IDENTIFIER

    def get_url_part(self):
        return 'voltage_current_v2'

    def cb_current(self, current):
        self.current_current.value = current / 1000.0

    def cb_voltage(self, voltage):
        self.current_voltage.value = voltage / 1000.0

    def cb_power(self, power):
        self.current_power.value = power / 1000.0

    def save_cal_clicked(self):
        gainmul = self.gainmul_spinbox.value()
        gaindiv = self.gaindiv_spinbox.value()
        self.vc.set_calibration(gainmul, gaindiv)

    def save_conf_clicked(self):
        avg = self.averaging_box.currentIndex()
        vol = self.voltage_box.currentIndex()
        cur = self.current_box.currentIndex()
        self.vc.set_configuration(avg, vol, cur)

    def calibration_clicked(self):
        if self.calibration == None:
            self.calibration = Calibration(self)

        self.button_calibration.setEnabled(False)
        self.calibration.show()
