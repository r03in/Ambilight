#!/usr/bin/env python3
# Replaces the seek restart logic in player.py with a proper PlaybackInfo-based approach.
# Root cause: Jellyfin requires a PlaybackInfo API call with StartTimeTicks to register a
# transcoding session before it will serve segments at that position. URL manipulation alone
# produces HTTP 400 on all segment requests.

path = '/storage/.kodi/addons/plugin.video.jellyfin/jellyfin_kodi/player.py'

with open(path) as f:
    src = f.read()

OLD = (
    '                import re as _re, threading, uuid as _uuid\n'
    '                seek_ticks = time * 10000\n'
    '                url = item.get("File", "")\n'
    '                if url:\n'
    "                    clean_url = _re.sub(r'[&]StartTimeTicks=\\d+', '', url)\n"
    "                    clean_url = _re.sub(r'PlaySessionId=[^&]+', 'PlaySessionId=' + _uuid.uuid4().hex, clean_url)\n"
    "                    new_url = clean_url.replace(' ', '%20') + '&StartTimeTicks=%d' % seek_ticks\n"
    '                    LOG.info("--[ seek/transcode: restarting at ticks %d ]", seek_ticks)\n'
    '                    def _restart(u=new_url):\n'
    '                        xbmc.Player().stop()\n'
    '                        xbmc.sleep(1500)\n'
    '                        xbmc.Player().play(u)\n'
    '                    threading.Thread(target=_restart, daemon=True).start()\n'
    '                    return\n'
)

NEW = (
    '                import threading\n'
    '                from urllib.parse import urlparse, parse_qs\n'
    '                seek_ticks = time * 10000\n'
    '                url = item.get("File", "")\n'
    '                server = item.get("Server")\n'
    '                item_id = item.get("Id", "")\n'
    '                if url and server and item_id:\n'
    '                    def _seek_restart(srv=server, iid=item_id, furl=url, ticks=seek_ticks):\n'
    '                        try:\n'
    '                            import time as _time\n'
    '                            xbmc.Player().stop()\n'
    '                            t0 = _time.time()\n'
    '                            parsed = urlparse(furl)\n'
    "                            server_url = '%s://%s' % (parsed.scheme, parsed.netloc)\n"
    '                            qs = parse_qs(parsed.query)\n'
    "                            video_codec = qs.get('VideoCodec', ['hevc'])[0]\n"
    "                            audio_codec = qs.get('AudioCodec', ['aac'])[0].split(',')[0]\n"
    "                            media_source_id = qs.get('MediaSourceId', [iid])[0]\n"
    "                            audio_idx = qs.get('AudioStreamIndex', [''])[0]\n"
    '                            profile = {\n'
    '                                "Name": "Kodi",\n'
    '                                "MaxStaticBitrate": 999744000,\n'
    '                                "MaxStreamingBitrate": 999744000,\n'
    '                                "TranscodingProfiles": [{"Type": "Video", "Container": "m3u8", "AudioCodec": audio_codec, "VideoCodec": video_codec, "MaxAudioChannels": "6"}],\n'
    '                                "DirectPlayProfiles": [],\n'
    '                                "ResponseProfiles": [],\n'
    '                                "ContainerProfiles": [],\n'
    '                                "CodecProfiles": [],\n'
    '                                "SubtitleProfiles": [],\n'
    '                            }\n'
    '                            pi_params = {"StartTimeTicks": ticks, "MediaSourceId": media_source_id}\n'
    '                            if audio_idx:\n'
    '                                pi_params["AudioStreamIndex"] = audio_idx\n'
    '                            info = srv.jellyfin.items(\n'
    '                                "/%s/PlaybackInfo" % iid, "POST",\n'
    '                                params=pi_params,\n'
    '                                json={"UserId": "{UserId}", "DeviceProfile": profile, "AutoOpenLiveStream": True}\n'
    '                            )\n'
    '                            if not info or not info.get("MediaSources"):\n'
    '                                LOG.error("--[ seek/transcode: PlaybackInfo returned no sources ]")\n'
    '                                return\n'
    "                            transcoding_url = info['MediaSources'][0].get('TranscodingUrl', '')\n"
    '                            if not transcoding_url:\n'
    '                                LOG.error("--[ seek/transcode: no TranscodingUrl in PlaybackInfo ]")\n'
    '                                return\n'
    '                            base, pstr = transcoding_url.split("?", 1)\n'
    '                            base = base.replace("stream", "master", 1)\n'
    "                            new_url = '%s%s?%s' % (server_url, base, pstr)\n"
    '                            LOG.info("--[ seek/transcode: PlaybackInfo OK at ticks %d ]", ticks)\n'
    '                            elapsed_ms = int((_time.time() - t0) * 1000)\n'
    '                            remaining = max(0, 1000 - elapsed_ms)\n'
    '                            if remaining:\n'
    '                                xbmc.sleep(remaining)\n'
    '                            xbmc.Player().play(new_url)\n'
    '                        except Exception as _e:\n'
    '                            LOG.error("--[ seek/transcode restart error: %s ]", _e)\n'
    '                    threading.Thread(target=_seek_restart, daemon=True).start()\n'
    '                    return\n'
)

if OLD not in src:
    print("Pattern not found — printing seek/transcode context:")
    idx = src.find('seek/transcode')
    print(repr(src[idx-100:idx+600]) if idx >= 0 else "not found")
    raise SystemExit(1)

src = src.replace(OLD, NEW, 1)
with open(path, 'w') as f:
    f.write(src)
print("OK")
