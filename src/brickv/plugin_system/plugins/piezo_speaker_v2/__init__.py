# -*- coding: utf-8 -*-
"""
Piezo Speaker 2.0 Plugin
Copyright (C) 2018 Olaf Lüke <olaf@tinkerforge.com>

__init__.py: package initialization

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

from brickv.plugin_system.plugins.piezo_speaker_v2.piezo_speaker_v2 import PiezoSpeakerV2

device_class = PiezoSpeakerV2
