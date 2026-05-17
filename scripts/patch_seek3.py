#!/usr/bin/env python3
# Root cause: Jellyfin's GetDynamicSegment explicitly throws
# System.ArgumentException: StartTimeTicks is not allowed.
# when a segment request URL contains StartTimeTicks. Jellyfin
# propagates StartTimeTicks from the master.m3u8 URL into the generated
# segment URLs in main.m3u8, but then rejects requests carrying it.
#
# Fix: strip StartTimeTicks from the master.m3u8 URL before playing.
# PlaybackInfo already registered the session at the right seek position,
# so Jellyfin knows where to start transcoding via the PlaySessionId alone.
#
# Run on the RPi:
#   python3 /tmp/patch_seek3.py && systemctl restart kodi.service

path = '/storage/.kodi/addons/plugin.video.jellyfin/jellyfin_kodi/player.py'

with open(path) as f:
    src = f.read()

OLD = (
    '                            base, pstr = transcoding_url.split("?", 1)\n'
    '                            base = base.replace("stream", "master", 1)\n'
    "                            new_url = '%s%s?%s' % (server_url, base, pstr)\n"
    '                            LOG.info("--[ seek/transcode: new session ready, playing from %d ]", ticks)\n'
    '                            xbmc.Player().play(new_url)\n'
)

NEW = (
    '                            base, pstr = transcoding_url.split("?", 1)\n'
    '                            base = base.replace("stream", "master", 1)\n'
    '                            import re as _re\n'
    # Jellyfin rejects segment requests that include StartTimeTicks
    # (System.ArgumentException: StartTimeTicks is not allowed).
    # The session already knows the start position from PlaybackInfo.
    '                            pstr = _re.sub(r\'&StartTimeTicks=\\d+\', \'\', pstr)\n'
    "                            new_url = '%s%s?%s' % (server_url, base, pstr)\n"
    '                            LOG.info("--[ seek/transcode: playing from %d ]", ticks)\n'
    '                            xbmc.Player().play(new_url)\n'
)

if OLD not in src:
    print("Pattern not found — current seek/transcode context:")
    idx = src.find('seek/transcode')
    print(repr(src[idx-50:idx+500]) if idx >= 0 else "not found")
    raise SystemExit(1)

src = src.replace(OLD, NEW, 1)
with open(path, 'w') as f:
    f.write(src)
print("OK")
