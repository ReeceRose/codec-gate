import os
import tempfile
from importlib import resources

try:
    from pkg_resources import resource_filename
except ImportError:
    resource_filename = None

_extract_dir = None


def get_resource(filename):
    """Real, lasting path to a data file, even when running from a zipped egg.

    deluge.common.resource_filename extracts to a temp file that is deleted
    straight away, which leaves the Web UI with a 404 for our script.
    """
    if resource_filename:
        return resource_filename(__package__, os.path.join('data', filename))

    global _extract_dir
    if _extract_dir is None:
        _extract_dir = tempfile.mkdtemp(prefix='codecgate-')
    path = os.path.join(_extract_dir, filename)
    if not os.path.exists(path):
        data = (resources.files(__package__) / 'data' / filename).read_bytes()
        with open(path, 'wb') as f:
            f.write(data)
    return path
