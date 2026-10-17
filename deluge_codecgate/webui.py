from deluge.plugins.pluginbase import WebPluginBase

from .common import get_resource


class WebUI(WebPluginBase):
    scripts = [get_resource('codecgate.js')]

    def enable(self):
        pass

    def disable(self):
        pass
