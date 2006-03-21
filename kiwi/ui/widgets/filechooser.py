#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2006 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
#
# Author(s): Ali Afshar <aafshar@gmail.com>
#


"""Filechooser widgets for the kiwi framework"""

import gtk

from kiwi.ui.widgets.proxy import ProxyWidgetMixin
from kiwi.utils import PropertyObject, gsignal

class _FileChooserMixin(object):
    """Mixin to use common methods of the FileChooser interface"""

    allowed_data_types = str,

    gsignal('selection_changed', 'override')
    def do_selection_changed(self):
        self.emit('content-changed')
        self.chain()

    def read(self):
        return self.get_filename()

    def update(self, data):
        if data is None:
            return
        self.set_filename(data)

class FileChooserButton(_FileChooserMixin, PropertyObject,
                        gtk.FileChooserButton, ProxyWidgetMixin):
    def __init__(self):
        ProxyWidgetMixin.__init__(self)
        PropertyObject.__init__(self, data_type=str)
        gtk.FileChooserButton.__init__(self)

class FileChooserWidget(_FileChooserMixin, PropertyObject,
                        gtk.FileChooserWidget, ProxyWidgetMixin):
    def __init__(self):
        ProxyWidgetMixin.__init__(self)
        PropertyObject.__init__(self, data_type=str)
        gtk.FileChooserWidget.__init__(self)

