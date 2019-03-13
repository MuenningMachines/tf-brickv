# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014 Ishraq Ibne Ashraf <ishraq@tinkerforge.com>

widget_span_slider.py: Custom span slider with spinbox implementation

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

from PyQt5 import Qt, QtCore
from PyQt5.QtWidgets import QWidget, QSpinBox, QHBoxLayout

from brickv.plugin_system.plugins.red.qxt_span_slider import QxtSpanSlider

class widgetSpinBoxSpanSlider(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.span_slider = QxtSpanSlider()
        self.sbox_lower = QSpinBox()
        self.sbox_upper = QSpinBox()
        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.setContentsMargins(5, 5, 5, 5)
        self.horizontal_layout.addWidget(self.sbox_lower)
        self.horizontal_layout.addWidget(self.span_slider)
        self.horizontal_layout.addWidget(self.sbox_upper)

        # Signal and slots
        self.sbox_lower.valueChanged.connect(self.slot_sbox_lower_value_changed)
        self.sbox_upper.valueChanged.connect(self.slot_sbox_upper_value_changed)
        self.span_slider.lowerPositionChanged.connect(self.slot_span_slider_lower_position_changed)
        self.span_slider.upperPositionChanged.connect(self.slot_span_slider_upper_position_changed)

        self.setLayout(self.horizontal_layout)

    def slot_sbox_lower_value_changed(self, value):
        value_sbox_upper = self.sbox_upper.value()
        value_sbox_lower = value

        if value_sbox_upper < value_sbox_lower:
            self.span_slider.swapControls()
            self.span_slider.setUpperValue(value_sbox_lower)
            self.span_slider.setUpperPosition(value_sbox_lower)
            self.span_slider.setLowerValue(value_sbox_upper)
            self.span_slider.setLowerPosition(value_sbox_upper)
            self.sbox_upper.setValue(value_sbox_lower)
            self.sbox_lower.setValue(value_sbox_upper)
            return

        self.span_slider.setLowerValue(value_sbox_lower)
        self.span_slider.setLowerPosition(value_sbox_lower)

    def slot_sbox_upper_value_changed(self, value):
        value_sbox_upper = value
        value_sbox_lower = self.sbox_lower.value()

        if value_sbox_upper < value_sbox_lower:
            self.span_slider.swapControls()
            self.span_slider.setUpperValue(value_sbox_lower)
            self.span_slider.setUpperPosition(value_sbox_lower)
            self.span_slider.setLowerValue(value_sbox_upper)
            self.span_slider.setLowerPosition(value_sbox_upper)
            self.sbox_upper.setValue(value_sbox_lower)
            self.sbox_lower.setValue(value_sbox_upper)
            return

        self.span_slider.setUpperValue(value_sbox_upper)
        self.span_slider.setUpperPosition(value_sbox_upper)

    def slot_span_slider_lower_position_changed(self, value):
        self.sbox_lower.setValue(value)

    def slot_span_slider_upper_position_changed(self, value):
        self.sbox_upper.setValue(value)
