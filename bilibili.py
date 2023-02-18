import requests
import json
import os

headers = {}
bvid = "BV12g411r7mB"
api = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}"
headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.52"
headers["referer"] = f"https://www.bilibili.com/video/{bvid}"
headers["origin"] = "https://www.bilibili.com"
headers["cookie"] = "YOURCOOKIE"
print("bvid:", bvid)

res = requests.get(api, headers=headers)
cid = json.loads(res.text)["data"][0]["cid"]

print("cid:", cid)

api = f"https://api.bilibili.com/x/player/playurl?qn=32&fnver=0&fnval=16&fourk=1&voice_balance=1&bvid={bvid}&cid={cid}"
res = requests.get(api, headers=headers)
data = json.loads(res.text)["data"]["dash"]

videoid = data["video"][0]["id"]
audioid = data["audio"][0]["id"]

print("video-id:", videoid)
print("audio-id:", audioid)

video_file_name = f"{bvid}-video-{videoid}.m4s"
audio_file_name = f"{bvid}-audio-{audioid}.m4s"

video = data["video"][0]["base_url"]
audio = data["audio"][0]["base_url"]

print("videoUrl:", video)
print("audioUrl:", audio)

headers["range"] = "bytes=0-"

res = requests.get(video, headers=headers)
with open(video_file_name, "wb") as f:
    f.write(res.content)

res = requests.get(audio, headers=headers)
with open(audio_file_name, "wb") as f:
    f.write(res.content)

os.system(f"ffmpeg -i {video_file_name} -i {audio_file_name} -c:v copy -c:a copy {bvid}-{videoid}-{audioid}.mkv")
