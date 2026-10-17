# CodecGate

A [Deluge](https://deluge-torrent.org) 2.x plugin that makes you approve h264 downloads. Torrents tagged x264, h264 or AVC are paused and labelled `needs-approval`. HEVC, x265 and AV1 download normally. To approve a held torrent, resume it.

Mainly written for Deluge running in Docker (Unraid, linuxserver/deluge, binhex), but it works on any Deluge 2 install.

## Features

- **Codec gate:** holds torrents whose name or video files match a "hold" codec, and lets "allow" codecs through. Both lists can be edited.
- **Approve by resuming:** resuming a held torrent approves it, and the `needs-approval` label is removed automatically.
- **Older releases:** optionally lets h264 through for releases from before a year you choose, because older films and shows often only exist in h264.
- **Unknown codecs:** you choose whether videos with no codec in the name are held or allowed.
- **Non-video torrents are ignored:** ISOs, music and so on are never touched.
- **Webhook notifications:** Discord or generic JSON, sent when a torrent is held and/or allowed.
- **Web UI settings page:** with a "test a name" box and a "send test" webhook button.
- **Plays nicely with Sonarr/Radarr:** a label set by another app is never overwritten.

## Requirements

- Deluge **2.x**
- The **Label** plugin enabled (ships with Deluge). It's optional: without it, held torrents are paused but not labelled.
- An egg built with the **same Python minor version as Deluge** (see [Building](#building))

## Installation

### Docker / Unraid

1. Check which Python version the container runs:
   ```bash
   docker exec deluge python3 --version   # e.g. Python 3.12.x
   ```
2. [Build](#building) the egg with that Python version, or use a release egg whose name ends in the same `py3.X`.
3. Copy it into the container's plugin folder and fix ownership:
   ```bash
   cp dist/CodecGate-*-py3.12.egg /mnt/user/appdata/deluge/plugins/
   chown 99:100 /mnt/user/appdata/deluge/plugins/CodecGate-*.egg   # Unraid nobody:users
   docker restart deluge
   ```
4. In the Web UI, open **Preferences → Plugins**, enable **Label** and **CodecGate**, and reload the page.

For other Docker hosts, `/config/plugins` inside the container is usually mapped to `<appdata>/plugins` on the host.

### Bare-metal Deluge

Copy the egg to `~/.config/deluge/plugins/` (Linux/macOS) or `%APPDATA%\deluge\plugins\` (Windows). Alternatively, use **Preferences → Plugins → Install** in the desktop client. Then restart Deluge.

If you use a separate daemon, install the egg wherever **deluged** runs.

### Upgrading

Delete the old egg from the plugins folder, copy in the new one and restart Deluge. Your settings are kept.

## Usage

When a torrent is added, CodecGate decides what to do with it:

| Torrent | Result |
|---|---|
| Matches a **hold** pattern (x264, h264, AVC…) | Paused and labelled `needs-approval` |
| Matches an **allow** pattern (x265, HEVC, AV1…) | Downloads normally |
| Has video but matches neither list | Held (default) or allowed, depending on your setting |
| Older than your cutoff year (if enabled) | Allowed, even if it's h264 |
| Contains no video files | Ignored |

**To approve** a held torrent, resume it in Deluge. The `needs-approval` label is removed.
**To reject** one, remove it.

To see everything waiting for approval, filter by the `needs-approval` label in the sidebar.

Torrents that are already there when Deluge starts are never checked again, so torrents you've approved stay approved after a restart.

## Settings

All settings are under **Preferences → CodecGate** in the Web UI. Changes only apply to torrents added after you save.

### Codecs

| Setting | Default | Notes |
|---|---|---|
| Hold for approval | `x\.?264`, `h\.?264`, `avc1?` | One pattern per line |
| Always allow | `x\.?265`, `h\.?265`, `hevc`, `av1` | One pattern per line |

Patterns are case-insensitive [regular expressions](https://docs.python.org/3/library/re.html), and they only match whole words. Each one is checked against the torrent name and every video file name. Some examples:

- `x\.?264` matches `x264` and `x.264`
- `av1` matches `Movie.AV1.Opus` but not `Movie.AV10`
- `avc1?` matches `AVC` and `AVC1` but not `AVCHD`
- Plain words like `vp9`, `xvid` or `mpeg2` work as typed

If a name matches both lists, it is **held**.

### Behaviour

| Setting | Default | Notes |
|---|---|---|
| Hold videos that match neither list | On | Turn off to let unlabelled releases through |
| Hold label | `needs-approval` | Only `a-z`, `0-9`, `_` and `-`. Leave blank to only pause |
| Video extensions | `.mkv .mp4 .m4v .avi .ts .m2ts .webm .mov .wmv` | Torrents with none of these are ignored |

### Older releases

| Setting | Default | Notes |
|---|---|---|
| Auto-allow releases from before year | Off | |
| Before year | `2015` | A release must be strictly older than this to be allowed |

The year is the **last** year-like number in the torrent name, so `2001.A.Space.Odyssey.1968.1080p` counts as 1968 and `Blade.Runner.2049.2017` as 2017. Resolutions such as `1920x1080` aren't treated as years. If the name has no year, CodecGate checks the video file names. If there's no year anywhere, this rule doesn't apply.

### Notifications

| Setting | Default | Notes |
|---|---|---|
| Webhook URL | *(empty)* | `http://` or `https://`. Leave blank to turn notifications off |
| Format | Generic JSON | `Generic JSON` or `Discord` |
| Notify when held | On | |
| Notify when allowed | Off | Sent for every allowed video torrent, which can be noisy |

**Send test** posts a sample notification using whatever is currently in the form, then shows the HTTP status or the error.

#### Discord

Create a webhook in *Channel settings → Integrations → Webhooks*, paste its URL and choose **Discord**. Each notification arrives as an embed showing the torrent name, the reason and the release year.

#### Generic JSON

Each notification is a `POST` with `Content-Type: application/json`:

```json
{
  "event": "held",
  "title": "Held for approval",
  "name": "Movie.2021.1080p.BluRay.x264-GRP",
  "reason": "Held codec",
  "year": 2021,
  "torrent_id": "78d24309afcc637749fb416522eaa9743355e0e8"
}
```

`event` is `held`, `allowed` or `test`. This format works with Home Assistant, n8n, Node-RED and similar tools.

### Config file

Settings are stored in `codecgate.conf` in Deluge's config folder (for example `/mnt/user/appdata/deluge/codecgate.conf`). If you edit it by hand, **stop Deluge first**, or it may overwrite your changes. The Web UI checks your settings before saving them; hand edits are not checked.

## Building

The egg's Python version **must match** the Python that Deluge runs on. The easiest way is to build in a throwaway container with that version:

```bash
docker run --rm -v "$PWD":/src -w /src python:3.12-alpine \
  sh -c "pip install -q 'setuptools<81' && python setup.py bdist_egg"
```

The output is `dist/CodecGate-<version>-py3.12.egg`. Change `3.12` to whatever `python3 --version` reports inside your Deluge container. If the Deluge image later moves to a new Python version, rebuild.

## Development

```
deluge_codecgate/
  core.py            # daemon side: events, pausing, labels, RPC methods
  rules.py           # codec/year decisions and settings validation (pure Python)
  notify.py          # webhook payloads and sending (stdlib only)
  webui.py           # registers the Web UI script
  data/codecgate.js  # Preferences page (ExtJS)
  gtk3ui.py          # stub, there is no desktop settings UI yet
tests/test_rules.py
```

Run the tests (Deluge isn't needed):

```bash
python3 tests/test_rules.py "$PWD"
```

`rules.py` and `notify.py` don't depend on Deluge, so you can test the matching logic and webhooks without a daemon.

### How it works

- On `TorrentAddedEvent`, the torrent is checked once its file list is available. Magnet links are re-checked every second until their metadata arrives.
- Held torrents are paused with auto-management turned off, so Deluge's queue won't restart them.
- On `TorrentResumedEvent`, the hold label is cleared if the torrent is running, or queued by auto-management. Deluge sends its own resume event just after adding a torrent; that one is ignored, because the torrent is still paused when it arrives.
- Webhooks are sent from a background thread, so a slow endpoint can't stall Deluge.

### RPC methods

These are available to clients as `codecgate.*`:

| Method | Description |
|---|---|
| `get_config()` | Current settings |
| `set_config(config)` | Check and save settings (raises `ValueError` on bad input) |
| `test_name(name, config=None)` | Returns `{action, reason, year}` for a release name |
| `test_webhook(config=None)` | Sends a test notification and returns the HTTP status |

## Troubleshooting

**The plugin doesn't appear in the plugin list.**
The egg's Python version doesn't match Deluge's. Compare the egg's `py3.X` suffix with `python3 --version` inside the container, and rebuild if they differ.

**Held torrents aren't labelled.**
Enable the **Label** plugin. Also note that if another app such as Sonarr or Radarr has already labelled the torrent, CodecGate leaves that label alone and only pauses.

**Something was held or allowed and I don't know why.**
Paste its name into **Test a name** on the settings page. The daemon log also records every decision:
```
CodecGate: Movie.2021.1080p.BluRay.x264-GRP -> hold (Held codec)
```
View it with `docker logs -f deluge` (you may need the `debug` log level).

**The webhook test fails.**
The error message is shown under the button. Check that the container can reach the URL. Discord URLs must be the full `https://discord.com/api/webhooks/...` link.

## Limitations

- A torrent can download for up to about a second before it's paused (after its metadata arrives, for magnets).
- Codec detection relies on names. A release that doesn't mention its codec is treated as "unknown".
- There's no settings UI in the GTK desktop client yet; use the Web UI.
- Only torrents added after the plugin is enabled are checked.

## License

[MIT](LICENSE)
