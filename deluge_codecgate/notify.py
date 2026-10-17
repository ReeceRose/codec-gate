"""Webhook payloads and delivery. Pure stdlib; send() blocks, so run it in a thread."""
import json
import urllib.request

USER_AGENT = 'CodecGate (Deluge plugin)'

TITLES = {
    'held': 'Held for approval',
    'allowed': 'Auto-allowed',
    'test': 'CodecGate test notification',
}
DISCORD_COLOURS = {'held': 0xE67E22, 'allowed': 0x2ECC71, 'test': 0x3498DB}


def build_payload(fmt, event, name, reason, year=None, torrent_id=None):
    if fmt == 'discord':
        embed = {
            'title': TITLES[event],
            'description': name[:4000],
            'color': DISCORD_COLOURS[event],
            'fields': [{'name': 'Reason', 'value': reason[:1000] or '-', 'inline': True}],
        }
        if year:
            embed['fields'].append({'name': 'Year', 'value': str(year), 'inline': True})
        return {'username': 'CodecGate', 'embeds': [embed]}

    return {
        'event': event,
        'title': TITLES[event],
        'name': name,
        'reason': reason,
        'year': year,
        'torrent_id': torrent_id,
    }


def send(url, payload, timeout=10):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': USER_AGENT},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status
