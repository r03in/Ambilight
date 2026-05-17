#!/usr/bin/env python3
# Patches onPlayBackSeek in the Jellyfin for Kodi addon to restart the HLS
# stream from the seek position rather than trying to navigate within it.
#
# Problem: Jellyfin rotates the segment hash when restarting its FFmpeg session
# for a new seek position, so Kodi's cached manifest URLs 404 -> EOF after 20s.
# Fix: restart xbmc.Player with StartTimeTicks appended to the URL.
#
# Run on the RPi: python3 /tmp/patch_seek.py && systemctl restart kodi.service

path = '/storage/.kodi/addons/plugin.video.jellyfin/jellyfin_kodi/player.py'

with open(path) as f:
    src = f.read()

OLD = (
    '            self.report_playback()\n'
    '            LOG.info("--[ seek ]")\n'
    '\n'
    '            # Check skip segments immediately after seek\n'
    '            if settings("mediaSegmentsEnabled.bool"):\n'
    '                try:\n'
    '                    current_file = self.get_playing_file()\n'
    '                    item = self.get_file_info(current_file)\n'
    '                    current_pos = int(self.getTime())\n'
    '                    self.check_skip_segments(item, current_pos)\n'
    '                except Exception:\n'
    '                    pass'
)

NEW = (
    '            current_file = self.get_playing_file()\n'
    '            item = self.get_file_info(current_file)\n'
    '            if item and item.get("PlayMethod") == "Transcode":\n'
    '                import re as _re, threading\n'
    '                seek_ticks = time * 10000\n'
    '                url = item.get("File", "")\n'
    '                if url:\n'
    "                    clean_url = _re.sub(r'[&]StartTimeTicks=\\d+', '', url)\n"
    "                    new_url = clean_url + '&StartTimeTicks=%d' % seek_ticks\n"
    '                    LOG.info("--[ seek/transcode: restarting at ticks %d ]", seek_ticks)\n'
    '                    def _restart(u=new_url):\n'
    '                        xbmc.sleep(300)\n'
    '                        xbmc.Player().play(u)\n'
    '                    threading.Thread(target=_restart, daemon=True).start()\n'
    '                    return\n'
    '\n'
    '            self.report_playback()\n'
    '            LOG.info("--[ seek ]")\n'
    '\n'
    '            # Check skip segments immediately after seek\n'
    '            if settings("mediaSegmentsEnabled.bool"):\n'
    '                try:\n'
    '                    current_file = self.get_playing_file()\n'
    '                    item = self.get_file_info(current_file)\n'
    '                    current_pos = int(self.getTime())\n'
    '                    self.check_skip_segments(item, current_pos)\n'
    '                except Exception:\n'
    '                    pass'
)

if OLD not in src:
    print("ERROR: Pattern not found — printing onPlayBackSeek section for debugging:")
    idx = src.find('onPlayBackSeek')
    if idx >= 0:
        print(repr(src[idx:idx+900]))
    else:
        print("'onPlayBackSeek' not found in file at all")
    raise SystemExit(1)

src = src.replace(OLD, NEW, 1)
with open(path, 'w') as f:
    f.write(src)
print("Patched OK")
