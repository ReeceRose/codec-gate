# Changelog

## 0.2

- Added an option to auto-allow releases from before a configurable year, read from the name.
- Added webhook notifications (Discord or generic JSON) for held and/or allowed torrents, with a "Send test" button.
- Added the Web UI preferences page with a "Test a name" box; settings are checked before saving.
- Fixed: held torrents weren't actually paused, because Deluge's pause call was skipped right after adding.
- Fixed: Deluge's own resume just after adding was treated as approval and cleared the hold label.

## 0.1

- First version: pause h264/x264/AVC torrents for approval and let HEVC/x265/AV1 through.
