import sys
sys.path.insert(0, sys.argv[1])
import importlib.util
def load(name):
    spec = importlib.util.spec_from_file_location(name, sys.argv[1] + '/deluge_codecgate/%s.py' % name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

rules = load('rules')
notify = load('notify')

hold = rules.compile_patterns([r'x\.?264', r'h\.?264', r'avc1?'])
allow = rules.compile_patterns([r'x\.?265', r'h\.?265', r'hevc', r'av1'])
ext = ['.mkv', '.mp4']
cases = [
    ('Movie.2023.1080p.BluRay.x264-GRP', ['Movie.mkv'], 'hold'),
    ('Movie 2023 1080p WEB-DL DDP5.1 H.264-GRP', ['a.mkv'], 'hold'),
    ('Movie.2023.2160p.UHD.BluRay.REMUX.AVC', ['a.mkv'], 'hold'),
    ('Show.S01E01.1080p.WEB.H264-GRP', ['x.mkv'], 'hold'),
    ('Movie.2023.2160p.WEB-DL.DV.HDR.H.265-GRP', ['a.mkv'], 'allow'),
    ('Movie.2023.1080p.x265.10bit', ['a.mkv'], 'allow'),
    ('Show.S02.1080p.HEVC', ['e1.mkv'], 'allow'),
    ('Movie.2023.1080p.WEB.AV1.Opus', ['a.mkv'], 'allow'),
    ('Some Show Season 1', ['Ep1.x264.mkv'], 'hold'),
    ('Some Show Season 1', ['Ep1.mkv'], 'unknown'),
    ('ubuntu-24.04-desktop-amd64', ['ubuntu.iso'], 'ignore'),
    ('AVCHD.Camera.Dump', ['a.mkv'], 'unknown'),
    ('Movie.Hevcorp.2023', ['a.mkv'], 'unknown'),
]
bad = 0
for name, files, want in cases:
    got = rules.classify(name, files, hold, allow, ext)
    flag = 'ok ' if got == want else 'BAD'
    bad += got != want
    print(flag, f'{got:8}', name)
if bad:
    sys.exit(bad)

v = rules.validate_config
assert v({'hold_patterns': [' x264 ', '', 'vc-?1']}) == {'hold_patterns': ['x264', 'vc-?1']}
assert v({'video_extensions': ['mkv', '.MP4', '']}) == {'video_extensions': ['.mkv', '.mp4']}
assert v({'hold_label': ' Needs-Approval '}) == {'hold_label': 'needs-approval'}
assert v({'older_than_year': '2012'}) == {'older_than_year': 2012}
assert v({'webhook_url': ' https://discord.com/api/webhooks/1/x '}) == {'webhook_url': 'https://discord.com/api/webhooks/1/x'}
assert v({'webhook_url': ''}) == {'webhook_url': ''}
for bad in ({'hold_patterns': ['x26(4']}, {'hold_label': 'needs approval'}, {'nope': 1},
            {'older_than_year': ''}, {'older_than_year': 1800}, {'webhook_url': 'discord.com/x'},
            {'webhook_format': 'slack'}):
    try:
        v(bad)
    except ValueError as ex:
        print('ok  rejects', bad, '->', ex)
    else:
        print('BAD accepted', bad); sys.exit(1)

years = [
    ('2001.A.Space.Odyssey.1968.1080p.BluRay.x264', 1968),
    ('Blade.Runner.2049.2017.2160p.x264', 2017),
    ('Movie.1998.1920x1080.x264', 1998),
    ('Show.S01E01.1080p.WEB.H264', None),
    ('Movie.2999.1080p', None),
]
for name, want in years:
    got = rules.release_year(name)
    assert got == want, (name, got, want)
    print('ok  year', got, name)

old = dict(rules.DEFAULT_PREFS, allow_older=True, older_than_year=2015)
decisions = [
    (rules.DEFAULT_PREFS, 'Movie.1998.1080p.BluRay.x264', [], 'hold'),
    (old, 'Movie.1998.1080p.BluRay.x264', [], 'allow'),
    (old, 'Movie.2019.1080p.BluRay.x264', [], 'hold'),
    (old, 'Movie.2015.1080p.BluRay.x264', [], 'hold'),
    (old, 'Show.S01.1080p.x264', ['Show.S01/Show.1999.E01.mkv'], 'allow'),
    (old, 'Movie.2019.1080p.HEVC', [], 'allow'),
    (old, 'Old.Thing.1990', ['a.iso'], 'ignore'),
    (dict(old, hold_unknown=False), 'Movie.2020.1080p', [], 'allow'),
    (old, 'Movie.2020.1080p', [], 'hold'),
]
for settings, name, files, want in decisions:
    got = rules.decide(name, files, settings)
    assert got['action'] == want, (name, got, want)
    print('ok  %-6s' % got['action'], name, '-', got['reason'])

d = notify.build_payload('discord', 'held', 'Movie.x264', 'Held codec', 1998, 'abc')
assert d['embeds'][0]['title'] == 'Held for approval' and d['embeds'][0]['fields'][1]['value'] == '1998'
j = notify.build_payload('json', 'allowed', 'Movie.x264', 'Released 1998, before 2015', 1998, 'abc')
assert j == {'event': 'allowed', 'title': 'Auto-allowed', 'name': 'Movie.x264',
             'reason': 'Released 1998, before 2015', 'year': 1998, 'torrent_id': 'abc'}

import http.server, json, threading
received = []
class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        received.append((self.headers['Content-Type'], self.headers['User-Agent'], json.loads(body)))
        self.send_response(204); self.end_headers()
    def log_message(self, *a): pass
server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.handle_request, daemon=True).start()
status = notify.send('http://127.0.0.1:%d/hook' % server.server_port, j)
assert status == 204 and received[0] == ('application/json', notify.USER_AGENT, j), received
print('ok  webhook POST delivered, HTTP', status)
