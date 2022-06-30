import requests

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36 Edg/103.0.1264.37'
}

url = "https://zj.shankuwang.com:8443/?url=https://dy.jx1024.com:8443/uploads/%E5%99%AC%E8%A1%80%E7%8B%82%E8%A2%AD02.m3u8&vlt_l=0&vlt_r=0"

res = requests.get(url=url, headers=headers)

new_url = res.text.split('video_url', 1)[1].split("\'", 2)[1]

new_url = requests.compat.urljoin(url, new_url)

print(new_url)

from strange import MainDownload

MainDownload(url=new_url, filename="1")
