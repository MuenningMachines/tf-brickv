# -*- coding: utf-8 -*-
"""
Servo Plugin
Copyright (C) 2010-2012 Olaf Lüke <olaf@tinkerforge.com>
Copyright (C) 2014 Matthias Bolte <matthias@tinkerforge.com>

servo.py: Servo Brick Plugin implementation

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

import time
import random
from threading import Event

from PyQt5.QtCore import Qt, QRect, QTimer, pyqtSignal, QThread
from PyQt5.QtWidgets import QLabel, QWidget, QInputDialog, QErrorMessage, QAction
from PyQt5.QtGui import QColor, QPainter

from brickv.plugin_system.plugin_base import PluginBase
from brickv.plugin_system.plugins.servo.ui_servo import Ui_Servo
from brickv.bindings import ip_connection
from brickv.bindings.brick_servo import BrickServo
from brickv.async_call import async_call
from brickv.knob_widget import KnobWidget
from brickv.slider_spin_syncer import SliderSpinSyncer

class ColorBar(QWidget):
    def __init__(self, orientation, *args):
        QWidget.__init__(self, *args)
        self.orientation = orientation
        self.light = QColor(Qt.gray)
        self.dark = QColor(Qt.black)
        self.height = 100

    def paintEvent(self, _):
        painter = QPainter(self)
        self.draw_color_bar(painter, self.rect())

    def grey(self):
        self.light = QColor(Qt.gray)
        self.dark = QColor(Qt.black)
        self.update()

    def color(self):
        self.light = QColor(Qt.red)
        self.dark = QColor(Qt.green)
        self.update()

    def set_height(self, height):
        self.height = height
        self.update()

    def draw_color_bar(self, painter, rect):
        h1, s1, v1, _ = self.light.getHsv()
        h2, s2, v2, _ = self.dark.getHsv()

        painter.save()
        painter.setClipRect(rect)
        painter.setClipping(True)

        if self.orientation == Qt.Horizontal:
            num_intervalls = rect.width()
        else:
            num_intervalls = rect.height()

        section = QRect()

        num_intervalls_shown = (num_intervalls*self.height)//100
        l = list(range(num_intervalls-num_intervalls_shown, num_intervalls))
        l.reverse()
        for i in l:
            if self.orientation == Qt.Horizontal:
                section.setRect(rect.x() + i, rect.y(),
                                1, rect.heigh())
            else:
                section.setRect(rect.x(), rect.y() + i,
                                rect.width(), 1)

            ratio = float(i)/float(num_intervalls)
            color = QColor()
            color.setHsv(h1 + int(ratio*(h2-h1) + 0.5),
                         s1 + int(ratio*(s2-s1) + 0.5),
                         v1 + int(ratio*(v2-v1) + 0.5))

            painter.fillRect(section, color)

        painter.restore()

class PositionKnob(KnobWidget):
    def __init__(self):
        KnobWidget.__init__(self)

        self.set_total_angle(180)
        self.set_range(-90, 90)
        self.set_knob_radius(15)
        self.set_scale_visible(False)

class Servo(PluginBase, Ui_Servo):
    qtcb_under_voltage = pyqtSignal(int)

    def __init__(self, *args):
        PluginBase.__init__(self, BrickServo, *args)

        self.setupUi(self)

        self.servo = self.device

        self.position_list = []
        self.velocity_list = []
        self.acceleration_list = []
        self.enable_list = []

        self.up_cur = 0
        self.up_siv = 0
        self.up_eiv = 0
        self.up_opv = 0
        self.up_mv = 0

        self.up_ena = [0]*7
        self.up_pos = [0]*7
        self.up_vel = [0]*7
        self.up_acc = [0]*7

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_apply)
        self.update_timer.setInterval(50)

        self.alive = True

        for i in range(1, 8):
            label = QLabel()
            label.setText('Off')
            self.enable_list.append(label)
            self.status_grid.addWidget(label, i, 1)

        for i in range(1, 8):
            pk = PositionKnob()
            self.position_list.append(pk)
            self.status_grid.addWidget(pk, i, 2)

        for i in range(1, 8):
            cb = ColorBar(Qt.Vertical)
            self.velocity_list.append(cb)
            self.status_grid.addWidget(cb, i, 3)

        for i in range(1, 8):
            cb = ColorBar(Qt.Vertical)
            self.acceleration_list.append(cb)
            self.status_grid.addWidget(cb, i, 4)

        self.qem = QErrorMessage(self)
        self.qem.setWindowTitle("Under Voltage")

        self.test_button.clicked.connect(self.test_button_clicked)
        self.output_voltage_button.clicked.connect(self.output_voltage_button_clicked)

        self.servo_dropbox.currentIndexChanged.connect(lambda x: self.update_servo_specific())
        self.enable_checkbox.stateChanged.connect(self.enable_state_changed)

        self.position_syncer = SliderSpinSyncer(self.position_slider,
                                                self.position_spin,
                                                self.position_changed)

        self.velocity_syncer = SliderSpinSyncer(self.velocity_slider,
                                                self.velocity_spin,
                                                self.velocity_changed)

        self.acceleration_syncer = SliderSpinSyncer(self.acceleration_slider,
                                                    self.acceleration_spin,
                                                    self.acceleration_changed)

        self.period_syncer = SliderSpinSyncer(self.period_slider,
                                              self.period_spin,
                                              self.period_changed)

        self.pulse_width_min_spin.editingFinished.connect(self.pulse_width_spin_finished)
        self.pulse_width_max_spin.editingFinished.connect(self.pulse_width_spin_finished)
        self.degree_min_spin.editingFinished.connect(self.degree_spin_finished)
        self.degree_max_spin.editingFinished.connect(self.degree_spin_finished)

        self.minimum_voltage_button.clicked.connect(self.minimum_voltage_button_clicked)

        self.qtcb_under_voltage.connect(self.cb_under_voltage)
        self.servo.register_callback(self.servo.CALLBACK_UNDER_VOLTAGE,
                                     self.qtcb_under_voltage.emit)

        class WorkerThread(QThread):
            def __init__(self, parent=None, func=None):
                QThread.__init__(self, parent)
                self.func = func

            def run(self):
                self.func()

        self.test_event = Event()
        self.test_thread_object = WorkerThread(self, self.test_thread)
        self.update_event = Event()
        self.update_thread_object = WorkerThread(self, self.update_thread)

        self.update_thread_first_time = False

        self.update_done_event = Event()
        self.update_done_event.set()

        if self.firmware_version >= (2, 3, 1):
            self.status_led_action = QAction('Status LED', self)
            self.status_led_action.setCheckable(True)
            self.status_led_action.toggled.connect(lambda checked: self.servo.enable_status_led() if checked else self.servo.disable_status_led())
            self.set_configs([(0, None, [self.status_led_action])])
        else:
            self.status_led_action = None

        if self.firmware_version >= (1, 1, 3):
            reset = QAction('Reset', self)
            reset.triggered.connect(lambda: self.servo.reset())
            self.set_actions([(0, None, [reset])])

    def start(self):
        if self.firmware_version >= (2, 3, 1):
            async_call(self.servo.is_status_led_enabled, None, self.status_led_action.setChecked, self.increase_error_count)

        self.alive = True
        self.test_event.clear()
        self.update_done_event.set()
        self.update_event.set()

        if not self.test_thread_object.isRunning():
            self.test_thread_object.start()

        if not self.update_thread_object.isRunning():
            self.update_thread_object.start()

        self.update_servo_specific()

        self.update_timer.start()

    def stop(self):
        if self.test_button.text().replace('&','') == "Stop Test":
            self.test_button_clicked()

        self.update_timer.stop()

        self.update_event.clear()
        self.alive = False
        self.update_done_event.wait()

    def destroy(self):
        self.test_event.set()
        self.update_event.set()

    @staticmethod
    def has_device_identifier(device_identifier):
        return device_identifier == BrickServo.DEVICE_IDENTIFIER

    def get_period_async(self, per):
        self.period_spin.setValue(per)
        self.period_slider.setValue(per)

    def is_enabled_async(self, ena):
        self.enable_checkbox.setChecked(ena)

    def get_position_async(self, pos):
        self.position_spin.setValue(pos)
        self.position_slider.setValue(pos)

    def get_velocity_async(self, vel):
        self.velocity_spin.setValue(vel)
        self.velocity_slider.setValue(vel)

    def get_acceleration_async(self, acc):
        self.acceleration_spin.setValue(acc)
        self.acceleration_slider.setValue(acc)

    def get_degree_async(self, deg, i):
        deg_min, deg_max = deg

        self.degree_min_spin.setValue(deg_min)
        self.degree_max_spin.setValue(deg_max)

        self.position_slider.setMinimum(deg_min)
        self.position_slider.setMaximum(deg_max)
        self.position_spin.setMinimum(deg_min)
        self.position_spin.setMaximum(deg_max)

        self.position_list[i].set_total_angle((deg_max - deg_min)/100)
        self.position_list[i].set_range(deg_min/100, deg_max/100)

    def get_pulse_width_async(self, pulse):
        pulse_min, pulse_max = pulse
        self.pulse_width_min_spin.setValue(pulse_min)
        self.pulse_width_max_spin.setValue(pulse_max)


    def update_servo_specific(self):
        i = self.selected_servo()
        if i == 255:
            self.enable_checkbox.setChecked(False)
            return

        async_call(self.servo.get_position, i, self.get_position_async, self.increase_error_count)
        async_call(self.servo.get_velocity, i, self.get_velocity_async, self.increase_error_count)
        async_call(self.servo.get_acceleration, i, self.get_acceleration_async, self.increase_error_count)
        async_call(self.servo.get_period, i, self.get_period_async, self.increase_error_count)
        async_call(self.servo.is_enabled, i, self.is_enabled_async, self.increase_error_count)
        def get_lambda_deg(i):
            return lambda x: self.get_degree_async(x, i)
        async_call(self.servo.get_degree, i, get_lambda_deg(i), self.increase_error_count)
        async_call(self.servo.get_pulse_width, i, self.get_pulse_width_async, self.increase_error_count)

    def error_handler(self, error):
        pass

    def servo_current_update(self, value):
        self.current_label.setText(str(value) + "mA")

    def stack_input_voltage_update(self, sv):
        sv_str = "%gV"  % round(sv/1000.0, 1)
        self.stack_voltage_label.setText(sv_str)

    def external_input_voltage_update(self, ev):
        ev_str = "%gV"  % round(ev/1000.0, 1)
        self.external_voltage_label.setText(ev_str)

    def output_voltage_update(self, ov):
        ov_str = "%gV"  % round(ov/1000.0, 1)
        self.output_voltage_label.setText(ov_str)

    def minimum_voltage_update(self, mv):
        mv_str = "%gV"  % round(mv/1000.0, 1)
        self.minimum_voltage_label.setText(mv_str)

    def position_update(self, i, pos):
        self.position_list[i].set_value(pos/100)

    def velocity_update(self, i, vel):
        self.velocity_list[i].set_height(vel*100//0xFFFF)

    def acceleration_update(self, i, acc):
        self.acceleration_list[i].set_height(acc*100//0xFFFF)

    def deactivate_servo(self, i):
        if self.enable_list[i].text().replace('&','') != 'Off':
            self.velocity_list[i].grey()
            self.acceleration_list[i].grey()

    def activate_servo(self, i):
        if self.enable_list[i].text().replace('&','') != 'On':
            self.velocity_list[i].color()
            self.acceleration_list[i].color()

    def selected_servo(self):
        try:
            return int(self.servo_dropbox.currentText()[-1:])
        except:
            return 255

    def enable_state_changed(self, state):
        s = self.selected_servo()
        try:
            if state == Qt.Checked:
                self.servo.enable(s)
            elif state == Qt.Unchecked:
                self.servo.disable(s)
        except ip_connection.Error:
            return

    def update_apply(self):
        if not self.update_thread_first_time:
            return

        self.servo_current_update(self.up_cur)
        self.stack_input_voltage_update(self.up_siv)
        self.external_input_voltage_update(self.up_eiv)
        self.output_voltage_update(self.up_opv)
        self.minimum_voltage_update(self.up_mv)
        for i in range(7):
            if self.up_ena[i]:
                self.activate_servo(i)

                self.position_update(i, self.up_pos[i])
                self.velocity_update(i, self.up_vel[i])
                self.acceleration_update(i, self.up_acc[i])

                self.enable_list[i].setText('On')
            else:
                self.deactivate_servo(i)
                self.enable_list[i].setText('Off')

    def update_thread(self):
        while self.alive:
            time.sleep(0.1)

            try:
                servo = self.selected_servo()
                if servo == 255:
                    self.up_cur = self.servo.get_overall_current()
                else:
                    self.up_cur = self.servo.get_servo_current(servo)

                self.up_siv = self.servo.get_stack_input_voltage()
                self.up_eiv = self.servo.get_external_input_voltage()
                self.up_opv = self.servo.get_output_voltage()
                self.up_mv = self.servo.get_minimum_voltage()

                for i in range(7):
                    self.up_ena[i] = self.servo.is_enabled(i)
                    if self.up_ena[i]:
                        self.activate_servo(i)
                        self.up_pos[i] = self.servo.get_current_position(i)
                        self.up_vel[i] = self.servo.get_current_velocity(i)
                        self.up_acc[i] = self.servo.get_acceleration(i)

                self.update_done_event.set()
                self.update_event.wait()
                self.update_done_event.clear()
            except ip_connection.Error:
                pass

            self.update_thread_first_time = True

        self.update_done_event.set()

    def test_thread(self):
        def test(num, ena, acc, vel, pos):
            if not self.alive:
                return

            try:
                if ena:
                    self.servo.enable(num)
                else:
                    self.servo.disable(num)
                self.servo.set_acceleration(num, acc)
                self.servo.set_velocity(num, vel)
                self.servo.set_position(num, pos)
            except ip_connection.Error:
                return

        def random_test():
            for i in range(7):
                test(i,
                     random.randrange(0, 2),
                     random.randrange(0, 65536),
                     random.randrange(0, 65536),
                     random.randrange(-9000, 9001))

        while self.alive:
            self.test_event.wait()
            if not self.alive:
                return

            # Full Speed left for 2 seconds
            for i in range(7):
                test(i, True, 65535, 65535, 9000)
            time.sleep(2)
            self.test_event.wait()
            if not self.alive:
                return

            # Full Speed right for 2 seconds
            for i in range(7):
                test(i, True, 65535, 65535, -9000)
            time.sleep(2)
            self.test_event.wait()
            if not self.alive:
                return

            # Test different speeds
            for i in range(19):
                for j in range(7):
                    test(j, True, 65535, 65535*i/18, -9000+i*1000)
                time.sleep(0.1)
                self.test_event.wait()
                if not self.alive:
                    return
            time.sleep(1)
            self.test_event.wait()
            if not self.alive:
                return

            # Test acceleration
            for i in range(7):
                test(i, True, 100, 65535, -9000)

            time.sleep(3)
            self.test_event.wait()
            if not self.alive:
                return

            # Random for 3 seconds
            random_test()
            time.sleep(3)

    def test_button_clicked(self):
        if self.test_button.text().replace('&','') == "Start Test":
            self.test_button.setText("Stop Test")
            self.test_event.set()
        else:
            self.test_button.setText("Start Test")
            self.test_event.clear()

    def output_voltage_button_clicked(self):
        qid = QInputDialog(self)
        qid.setInputMode(QInputDialog.IntInput)
        qid.setIntMinimum(2000)
        qid.setIntMaximum(9000)
        qid.setIntStep(100)
        async_call(self.servo.get_output_voltage, None, qid.setIntValue, self.increase_error_count)
        qid.intValueSelected.connect(self.output_voltage_selected)
        qid.setLabelText("Choose Output Voltage in mV.")
        qid.open()

    def output_voltage_selected(self, value):
        try:
            self.servo.set_output_voltage(value)
        except ip_connection.Error:
            return

    def position_changed(self, value):
        try:
            self.servo.set_position(self.selected_servo(), value)
        except ip_connection.Error:
            return

    def velocity_changed(self, value):
        try:
            self.servo.set_velocity(self.selected_servo(), value)
        except ip_connection.Error:
            return

    def acceleration_changed(self, value):
        try:
            self.servo.set_acceleration(self.selected_servo(), value)
        except ip_connection.Error:
            return

    def period_changed(self, value):
        try:
            self.servo.set_period(self.selected_servo(), value)
        except ip_connection.Error:
            return

    def pulse_width_spin_finished(self):
        try:
            self.servo.set_pulse_width(self.selected_servo(),
                                       self.pulse_width_min_spin.value(),
                                       self.pulse_width_max_spin.value())
        except ip_connection.Error:
            return

    def degree_spin_finished(self):
        min = self.degree_min_spin.value()
        max = self.degree_max_spin.value()
        servo = self.selected_servo()

        self.position_slider.setMinimum(min)
        self.position_slider.setMaximum(max)
        self.position_spin.setMinimum(min)
        self.position_spin.setMaximum(max)
        if servo == 255:
            for i in range(7):
                self.position_list[i].set_total_angle((max - min)/100)
                self.position_list[i].set_range(min/100, max/100)
        else:
            self.position_list[servo].set_total_angle((max - min)/100)
            self.position_list[servo].set_range(min/100, max/100)

        try:
            self.servo.set_degree(servo, min, max)
        except ip_connection.Error:
            return

    def cb_under_voltage(self, ov):
        mv_str = self.minimum_voltage_label.text()
        ov_str = "%gV"  % round(ov/1000.0, 1)
        if not self.qem.isVisible():
            self.qem.showMessage("Under Voltage: Output Voltage of " + ov_str +
                                 " is below minimum voltage of " + mv_str,
                                 "Servo_UnterVoltage")

    def minimum_voltage_selected(self, value):
        try:
            self.servo.set_minimum_voltage(value)
        except ip_connection.Error:
            return

    def minimum_voltage_button_clicked(self):
        qid = QInputDialog(self)
        qid.setInputMode(QInputDialog.IntInput)
        qid.setIntMinimum(5000)
        qid.setIntMaximum(0xFFFF)
        qid.setIntStep(100)
        async_call(self.servo.get_minimum_voltage, None, qid.setIntValue, self.increase_error_count)
        qid.intValueSelected.connect(self.minimum_voltage_selected)
        qid.setLabelText("Choose minimum servo voltage in mV.")
        qid.open()
