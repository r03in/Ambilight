#!/usr/bin/env python3
# Fixes intermittent seek failure caused by JellyfinClient losing its server
# connection (auth.server becomes empty) during playback. The prior patch used
# srv.jellyfin.items() which goes through the dead client -> MissingSchema.
#
# Fix: read credentials from server.config.data before stop() is called (while
# they're still likely valid), fall back to data.json if empty, then use direct
# urllib for the PlaybackInfo POST — completely bypassing JellyfinClient state.
#
# Run on the RPi:
#   python3 /tmp/patch_seek4.py && systemctl restart kodi.service

path = '/storage/.kodi/addons/plugin.video.jellyfin/jellyfin_kodi/player.py'

with open(path) as f:
    src = f.read()

OLD = (
    '            if item and item.get("PlayMethod") == "Transcode":\n'
    '                import threading\n'
    '                from urllib.parse import urlparse, parse_qs\n'
    '                seek_ticks = time * 10000\n'
    '                url = item.get("File", "")\n'
    '                server = item.get("Server")\n'
    '                item_id = item.get("Id", "")\n'
    '                if url and server and item_id:\n'
    '                    def _seek_restart(srv=server, iid=item_id, furl=url, ticks=seek_ticks):\n'
    '                        try:\n'
    '                            xbmc.Player().stop()\n'
    '                            # Wait for stop_playback to finish: session_stop + close_transcode\n'
    '                            # must complete before we create the new session, or Jellyfin\n'
    '                            # will sweep the new session when it deletes active encodings.\n'
    '                            xbmc.sleep(2000)\n'
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
    '                            import re as _re\n'
    "                            pstr = _re.sub(r'&StartTimeTicks=\\d+', '', pstr)\n"
    "                            new_url = '%s%s?%s' % (server_url, base, pstr)\n"
    '                            LOG.info("--[ seek/transcode: playing from %d ]", ticks)\n'
    '                            xbmc.Player().play(new_url)\n'
    '                        except Exception as _e:\n'
    '                            LOG.error("--[ seek/transcode restart error: %s ]", _e)\n'
    '                    threading.Thread(target=_seek_restart, daemon=True).start()\n'
    '                    return\n'
)

NEW = (
    '            if item and item.get("PlayMethod") == "Transcode":\n'
    '                import threading\n'
    '                seek_ticks = time * 10000\n'
    '                item_id = item.get("Id", "")\n'
    '                server = item.get("Server")\n'
    # Capture credentials now, before stop() clears the connection state
    '                srv_url = server.config.data.get("auth.server", "") if server else ""\n'
    '                srv_token = server.config.data.get("auth.token", "") if server else ""\n'
    '                srv_user = server.config.data.get("auth.user_id", "") if server else ""\n'
    # Fall back to persisted data.json if the client has already dropped its connection
    '                if not srv_url or not srv_token:\n'
    '                    import json as _json\n'
    '                    try:\n'
    "                        with open('/storage/.kodi/userdata/addon_data/plugin.video.jellyfin/data.json') as _f:\n"
    "                            for _s in _json.load(_f).get('Servers', []):\n"
    "                                if _s.get('AccessToken') and _s.get('address'):\n"
    "                                    srv_url = _s['address']\n"
    "                                    srv_token = _s['AccessToken']\n"
    "                                    srv_user = _s.get('UserId', '')\n"
    '                                    break\n'
    '                    except Exception as _ce:\n'
    '                        LOG.error("--[ seek/transcode: cannot read credentials: %s ]", _ce)\n'
    '                if item_id and srv_url and srv_token:\n'
    # Parse codec params from the current play URL for the device profile
    '                    from urllib.parse import urlparse, parse_qs\n'
    '                    furl = item.get("File", "")\n'
    '                    qs = parse_qs(urlparse(furl).query) if furl else {}\n'
    "                    _video_codec = qs.get('VideoCodec', ['hevc'])[0]\n"
    "                    _audio_codec = qs.get('AudioCodec', ['aac'])[0].split(',')[0]\n"
    "                    _media_source_id = qs.get('MediaSourceId', [item_id])[0]\n"
    "                    _audio_idx = qs.get('AudioStreamIndex', [''])[0]\n"
    '                    def _seek_restart(ticks=seek_ticks, iid=item_id, msid=_media_source_id,\n'
    '                                      aidx=_audio_idx, base_url=srv_url, tok=srv_token,\n'
    '                                      uid=srv_user, vc=_video_codec, ac=_audio_codec):\n'
    '                        try:\n'
    '                            import urllib.request, urllib.parse, json as _json, re as _re\n'
    '                            xbmc.Player().stop()\n'
    '                            xbmc.sleep(2000)\n'
    '                            profile = {\n'
    '                                "Name": "Kodi",\n'
    '                                "MaxStaticBitrate": 999744000,\n'
    '                                "MaxStreamingBitrate": 999744000,\n'
    '                                "TranscodingProfiles": [{"Type": "Video", "Container": "m3u8", "AudioCodec": ac, "VideoCodec": vc, "MaxAudioChannels": "6"}],\n'
    '                                "DirectPlayProfiles": [],\n'
    '                                "ResponseProfiles": [],\n'
    '                                "ContainerProfiles": [],\n'
    '                                "CodecProfiles": [],\n'
    '                                "SubtitleProfiles": [],\n'
    '                            }\n'
    '                            pi_params = {"StartTimeTicks": ticks, "MediaSourceId": msid}\n'
    '                            if aidx:\n'
    '                                pi_params["AudioStreamIndex"] = int(aidx)\n'
    "                            pi_url = '%s/Items/%s/PlaybackInfo?%s' % (base_url, iid, urllib.parse.urlencode(pi_params))\n"
    '                            req = urllib.request.Request(pi_url,\n'
    '                                data=_json.dumps({"UserId": uid, "DeviceProfile": profile, "AutoOpenLiveStream": True}).encode(),\n'
    "                                method='POST')\n"
    "                            req.add_header('Authorization', 'MediaBrowser Token=%s' % tok)\n"
    "                            req.add_header('Content-Type', 'application/json')\n"
    '                            info = _json.loads(urllib.request.urlopen(req, timeout=15).read())\n'
    '                            if not info or not info.get("MediaSources"):\n'
    '                                LOG.error("--[ seek/transcode: PlaybackInfo returned no sources ]")\n'
    '                                return\n'
    "                            transcoding_url = info['MediaSources'][0].get('TranscodingUrl', '')\n"
    '                            if not transcoding_url:\n'
    '                                LOG.error("--[ seek/transcode: no TranscodingUrl in PlaybackInfo ]")\n'
    '                                return\n'
    '                            base, pstr = transcoding_url.split("?", 1)\n'
    '                            base = base.replace("stream", "master", 1)\n'
    "                            pstr = _re.sub(r'&StartTimeTicks=\\d+', '', pstr)\n"
    "                            new_url = '%s%s?%s' % (base_url, base, pstr)\n"
    '                            LOG.info("--[ seek/transcode: playing from %d ]", ticks)\n'
    '                            xbmc.Player().play(new_url)\n'
    '                        except Exception as _e:\n'
    '                            LOG.error("--[ seek/transcode restart error: %s ]", _e)\n'
    '                    threading.Thread(target=_seek_restart, daemon=True).start()\n'
    '                    return\n'
)

if OLD not in src:
    print("Pattern not found — current seek/transcode context:")
    idx = src.find('seek/transcode')
    print(repr(src[idx-200:idx+800]) if idx >= 0 else "not found")
    raise SystemExit(1)

src = src.replace(OLD, NEW, 1)
with open(path, 'w') as f:
    f.write(src)
print("OK")
