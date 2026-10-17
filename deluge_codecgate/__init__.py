from deluge.plugins.init import PluginInitBase


class CorePlugin(PluginInitBase):
    def __init__(self, plugin_name):
        from .core import Core as _plugin_cls

        self._plugin_cls = _plugin_cls
        super().__init__(plugin_name)


class Gtk3UIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        from .gtk3ui import Gtk3UI as _plugin_cls

        self._plugin_cls = _plugin_cls
        super().__init__(plugin_name)


class WebUIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        from .webui import WebUI as _plugin_cls

        self._plugin_cls = _plugin_cls
        super().__init__(plugin_name)
