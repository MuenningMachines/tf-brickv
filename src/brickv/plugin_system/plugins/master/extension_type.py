# -*- coding: utf-8 -*-
"""
Master Plugin
Copyright (C) 2010-2012 Olaf Lüke <olaf@tinkerforge.com>
Copyright (C) 2012-2014 Matthias Bolte <matthias@tinkerforge.com>

extension_type.py: ExtensionType for Master Plugin implementation

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

from PyQt5.QtWidgets import QDialog, QMessageBox

from brickv.plugin_system.plugins.master.ui_extension_type import Ui_ExtensionType
from brickv.async_call import async_call
from brickv.utils import get_main_window, get_modeless_dialog_flags

class ExtensionType(QDialog, Ui_ExtensionType):
    def __init__(self, parent):
        QDialog.__init__(self, parent, get_modeless_dialog_flags())

        self.setupUi(self)

        self.parent = parent
        self.master = parent.master
        self.button_type_save.clicked.connect(self.save_clicked)
        self.combo_extension.currentIndexChanged.connect(self.index_changed)

        self.index_changed(0)

        self.button_close.clicked.connect(self.close)

    def reject(self):
        pass # avoid closing using ESC key

    def closeEvent(self, event):
        pass # dont touch event to avoid closing using ESC key

    def popup_ok(self):
        QMessageBox.information(get_main_window(), "Extension Type", "Successfully saved extension type", QMessageBox.Ok)

    def popup_fail(self):
        QMessageBox.critical(get_main_window(), "Extension Type", "Could not save extension type", QMessageBox.Ok)

    def get_extension_type_async(self, extension_type):
        if extension_type < 0 or extension_type > (self.type_box.count() - 1):
            extension_type = 0

        self.type_box.setCurrentIndex(extension_type)

    def index_changed(self, index):
        async_call(self.master.get_extension_type, index, self.get_extension_type_async, self.parent.increase_error_count)

    def save_clicked(self):
        extension = self.combo_extension.currentIndex()
        typ = self.type_box.currentIndex()

        try:
            self.master.set_extension_type(extension, typ)
        except:
            self.popup_fail()
            return

        try:
            new_type = self.master.get_extension_type(extension)
        except:
            self.popup_fail()
            return

        if typ == new_type:
            self.popup_ok()
        else:
            self.popup_fail()
