# -*- coding: utf-8 -*-
"""
OLED64x48 Plugin
Copyright (C) 2015 Olaf Lüke <olaf@tinkerforge.com>

oled_64x48.py: OLED 64x48 Plugin Implementation

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

from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QImage, QPainter, QPen, QColor

from brickv.plugin_system.plugin_base import PluginBase
from brickv.async_call import async_call
from brickv.slider_spin_syncer import SliderSpinSyncer
from brickv.plugin_system.plugins.oled_64x48.ui_oled_64x48 import Ui_OLED64x48
from brickv.bindings.bricklet_oled_64x48 import BrickletOLED64x48

class ScribbleArea(QWidget):
    """
      this scales the image but it's not good, too many refreshes really mess it up!!!
    """
    def __init__(self, w, h, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StaticContents)
        self.scribbling = 0

        self.width = w
        self.height = h
        self.image_pen_width = 5
        self.pen_width = 1
        self.image = QImage(QSize(w, h), QImage.Format_RGB32)

        self.setMaximumSize(w*self.image_pen_width, w*self.image_pen_width)
        self.setMinimumSize(w*self.image_pen_width, h*self.image_pen_width)

        self.last_point = QPoint()
        self.clear_image()

    def clear_image(self):
        self.image.fill(Qt.black)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_point = event.pos()
            self.scribbling = 1
        elif event.button() == Qt.RightButton:
            self.last_point = event.pos()
            self.scribbling = 2

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.scribbling == 1:
            self.draw_line_to(event.pos())
        elif (event.buttons() & Qt.RightButton) and self.scribbling == 2:
            self.draw_line_to(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.scribbling == 1:
            self.draw_line_to(event.pos())
            self.scribbling = 0
        elif event.button() == Qt.RightButton and self.scribbling == 2:
            self.draw_line_to(event.pos())
            self.scribbling = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(event.rect(), self.image.scaledToWidth(self.width*self.image_pen_width))

    def draw_line_to(self, end_point):
        painter = QPainter(self.image)
        painter.setPen(QPen(Qt.white if self.scribbling == 1 else Qt.black,
                            self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(self.last_point/5, end_point/5)

        self.update()
        self.last_point = QPoint(end_point)

class OLED64x48(PluginBase, Ui_OLED64x48):
    def __init__(self, *args):
        PluginBase.__init__(self, BrickletOLED64x48, *args)

        self.setupUi(self)

        self.oled = self.device

        self.scribble_area = ScribbleArea(64, 48)
        self.image_button_layout.insertWidget(0, self.scribble_area)

        self.contrast_syncer = SliderSpinSyncer(self.contrast_slider, self.contrast_spin, lambda value: self.new_configuration())
        self.char_syncer = SliderSpinSyncer(self.char_slider, self.char_spin, self.char_slider_changed)

        self.draw_button.clicked.connect(self.draw_clicked)
        self.clear_button.clicked.connect(self.clear_clicked)
        self.send_button.clicked.connect(self.send_clicked)
        self.clear_display_button.clicked.connect(self.clear_display_clicked)
        self.invert_checkbox.stateChanged.connect(self.new_configuration)

        self.current_char_value = -1

    def char_slider_changed(self, value):
        if value != self.current_char_value:
            self.current_char_value = value
            self.write_chars(value)
            self.char_slider.setValue(value)

    def new_configuration(self):
        contrast = self.contrast_spin.value()
        invert = self.invert_checkbox.isChecked()
        self.oled.set_display_configuration(contrast, invert)

    def write_chars(self, value):
        if value > 250:
            value = 250
        for j in range(6):
            start = ""
            if value + j < 10:
                start = "  "
            elif value + j < 100:
                start = " "
            self.oled.write_line(j, 3, start + str(value+j) + ": " + chr(value+j) + '\0')

    def clear_display_clicked(self):
        self.oled.new_window(0, 63, 0, 5)
        self.oled.clear_display()

    def clear_clicked(self):
        self.scribble_area.clear_image()

    def send_clicked(self):
        line = int(self.line_combobox.currentText())
        pos = int(self.pos_combobox.currentText())
        text = self.text_edit.text()
        self.oled.write_line(line, pos, text)

    def draw_clicked(self):
        lcd = []
        for i in range(6):
            lcd.append([])
            for j in range(64):
                page = 0
                for k in range(8):
                    if QColor(self.scribble_area.image.pixel(j, i*8 + k)) == Qt.white:
                        page |= 1 << k

                lcd[i].append(page)

        self.oled.new_window(0, 63, 0, 5)
        for i in range(6):
            self.oled.write(lcd[i])

    def cb_display_configuration(self, conf):
        self.contrast_slider.setValue(conf.contrast)
        self.invert_checkbox.setChecked(conf.invert)

    def start(self):
        async_call(self.oled.get_display_configuration, None, self.cb_display_configuration, self.increase_error_count)

    def stop(self):
        pass

    def destroy(self):
        pass

    @staticmethod
    def has_device_identifier(device_identifier):
        return device_identifier == BrickletOLED64x48.DEVICE_IDENTIFIER
