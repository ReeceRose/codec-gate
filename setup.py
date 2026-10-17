from setuptools import find_packages, setup

__plugin_name__ = 'CodecGate'
__author__ = 'Reece Rose'
__author_email__ = 'reecerose18@gmail.com'
__version__ = '0.2'
__url__ = 'https://github.com/ReeceRose/codec-gate'
__license__ = 'MIT'
__description__ = 'Pause h264 downloads for approval; let HEVC/AV1 through.'
__long_description__ = """
Inspects newly added torrents. Anything whose name or video files look like
h264/x264/AVC is paused and labelled for manual approval (resume it to approve).
HEVC/x265/AV1 torrents download as normal.
"""
__pkg_data__ = {'deluge_' + __plugin_name__.lower(): ['data/*']}

setup(
    name=__plugin_name__,
    version=__version__,
    description=__description__,
    author=__author__,
    author_email=__author_email__,
    url=__url__,
    license=__license__,
    long_description=__long_description__,
    packages=find_packages(),
    package_data=__pkg_data__,
    zip_safe=False,
    entry_points="""
    [deluge.plugin.core]
    %s = deluge_%s:CorePlugin
    [deluge.plugin.gtk3ui]
    %s = deluge_%s:Gtk3UIPlugin
    [deluge.plugin.web]
    %s = deluge_%s:WebUIPlugin
    """
    % ((__plugin_name__, __plugin_name__.lower()) * 3),
)
