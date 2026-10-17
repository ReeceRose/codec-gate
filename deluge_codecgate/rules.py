"""Codec classification. Pure Python so it can be tested without Deluge."""
import datetime
import functools
import os
import re

HOLD = 'hold'
ALLOW = 'allow'
UNKNOWN = 'unknown'
IGNORE = 'ignore'  # no video files at all

WEBHOOK_FORMATS = ('json', 'discord')

DEFAULT_PREFS = {
    # Label applied to held torrents ('' to only pause). Requires the Label plugin.
    'hold_label': 'needs-approval',
    # Hold video torrents that don't mention any codec at all.
    'hold_unknown': True,
    'hold_patterns': [r'x\.?264', r'h\.?264', r'avc1?'],
    'allow_patterns': [r'x\.?265', r'h\.?265', r'hevc', r'av1'],
    'video_extensions': [
        '.mkv', '.mp4', '.m4v', '.avi', '.ts', '.m2ts', '.webm', '.mov', '.wmv',
    ],
    # Let releases from before this year through regardless of codec.
    'allow_older': False,
    'older_than_year': 2015,
    'webhook_url': '',
    'webhook_format': 'json',
    'notify_held': True,
    'notify_allowed': False,
}

LABEL_RE = re.compile(r'[a-z0-9_-]*')
# A plausible release year as its own token; not part of 1920x1080 etc.
YEAR_RE = re.compile(r'(?<![0-9])(19[2-9][0-9]|20[0-9]{2})(?![0-9]|x[0-9])')


@functools.lru_cache(maxsize=16)
def _compile(patterns):
    """Match any pattern as a standalone token (not inside a longer word)."""
    if not patterns:
        return None
    joined = '|'.join('(?:%s)' % p for p in patterns)
    return re.compile(r'(?<![a-z0-9])(?:%s)(?![a-z0-9])' % joined, re.IGNORECASE)


def compile_patterns(patterns):
    return _compile(tuple(patterns))


def video_files(file_paths, video_extensions):
    video_exts = tuple(e.lower() for e in video_extensions)
    return [p for p in file_paths if os.path.splitext(p)[1].lower() in video_exts]


def classify(name, file_paths, hold_re, allow_re, video_extensions):
    videos = video_files(file_paths, video_extensions)
    if file_paths and not videos:
        return IGNORE

    texts = [name] + videos
    if hold_re and any(hold_re.search(t) for t in texts):
        return HOLD
    if allow_re and any(allow_re.search(t) for t in texts):
        return ALLOW
    return UNKNOWN


def release_year(text):
    """The last year-like token, so '2001.A.Space.Odyssey.1968' gives 1968."""
    latest = datetime.date.today().year + 1
    years = [int(y) for y in YEAR_RE.findall(text) if int(y) <= latest]
    return years[-1] if years else None


def decide(name, file_paths, settings):
    """Return {'action': hold/allow/ignore, 'reason': str, 'year': int or None}."""
    codec = classify(
        name,
        file_paths,
        compile_patterns(settings['hold_patterns']),
        compile_patterns(settings['allow_patterns']),
        settings['video_extensions'],
    )
    if codec == IGNORE:
        return {'action': IGNORE, 'reason': 'No video files', 'year': None}
    if codec == ALLOW:
        return {'action': ALLOW, 'reason': 'Allowed codec', 'year': None}
    if codec == UNKNOWN and not settings['hold_unknown']:
        return {'action': ALLOW, 'reason': 'No codec found', 'year': None}

    year = release_year(name)
    if year is None:
        for path in video_files(file_paths, settings['video_extensions']):
            year = release_year(os.path.basename(path))
            if year:
                break
    cutoff = settings['older_than_year']
    if settings['allow_older'] and year and year < cutoff:
        return {
            'action': ALLOW,
            'reason': 'Released %d, before %d' % (year, cutoff),
            'year': year,
        }

    reason = 'Held codec' if codec == HOLD else 'No codec found'
    return {'action': HOLD, 'reason': reason, 'year': year}


def validate_config(config, defaults=DEFAULT_PREFS):
    """Normalise settings from a UI, raising ValueError on anything bad."""
    clean = {}
    for key, value in config.items():
        if key not in defaults:
            raise ValueError('Unknown setting: %s' % key)
        if key in ('hold_patterns', 'allow_patterns'):
            value = [p.strip() for p in value if p.strip()]
            for pattern in value:
                try:
                    re.compile(pattern)
                except re.error as ex:
                    raise ValueError('Invalid pattern "%s": %s' % (pattern, ex))
        elif key == 'video_extensions':
            value = ['.' + e.strip().lstrip('.').lower() for e in value if e.strip()]
        elif key == 'hold_label':
            value = value.strip().lower()
            if not LABEL_RE.fullmatch(value):
                raise ValueError('Label may only contain a-z, 0-9, _ and -')
        elif key == 'older_than_year':
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError('Year must be a number')
            if not 1900 <= value <= 2100:
                raise ValueError('Year must be between 1900 and 2100')
        elif key == 'webhook_url':
            value = value.strip()
            if value and not re.match(r'https?://', value, re.IGNORECASE):
                raise ValueError('Webhook URL must start with http:// or https://')
        elif key == 'webhook_format':
            if value not in WEBHOOK_FORMATS:
                raise ValueError('Webhook format must be one of: %s' % ', '.join(WEBHOOK_FORMATS))
        elif isinstance(defaults[key], bool):
            value = bool(value)
        clean[key] = value
    return clean
