import requests
import threading
import time
import os
import random
import hashlib
from Crypto.Cipher import AES
from _argparse import ArgParser
__netSemaphore = threading.BoundedSemaphore(20)
# write_lock = threading.Lock()

def add_to_16(value):
    if type(value) == str:
        x00 = '\x00'
    elif type(value) == bytes:
        x00 = b'\x00'
    else:
        x00 = '\x00'

    while len(value) % 16 != 0: value += x00
    return value

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36 Edg/103.0.1264.37'
}
__mainAlive = False

def _get(url, headers, timeout, details):
    global __mainAlive
    random.seed(time.time())
    rt = 0
    while True:
        rt += 1
        acquired = False
        try:
            while not acquired:
                if __mainAlive == False:
                    print("Main not alive.")
                    return
                acquired = __netSemaphore.acquire()
            res = requests.get(url = url, headers = headers, timeout = timeout)
        except (KeyboardInterrupt, EOFError):
            if acquired: __netSemaphore.release()
            raise
        except Exception as e:
            if acquired: __netSemaphore.release()
            print(f"Request error, retrying... ({details}, {rt}), ", e)
            for i in range(0, rt % 5):
                if __mainAlive == False:
                    print("Main not alive.")
                    return
                time.sleep(0.1)
            time.sleep(random.random() * 3)
            if __mainAlive == False:
                print("Main not alive.")
                return
        else:
            if acquired: __netSemaphore.release()
            return res


###下载ts文件
def download(url, name, encoded = False, cryptor = None):
    global __mainAlive

    while True:
        if __mainAlive == False: return
        r = _get(url = url, headers = headers, timeout = 15, details = name)
        if r.status_code == 200 and r.headers.get("content-type").lower() != "text/html":
            break
        else:
            print(f"Request error, status code={r.status_code},", 
                  f"content-type={r.headers.get('content-type')},",
                  f"retrying... ({name})")
            time.sleep(0.5)

    if not r:
        print(f"Unknown error, ({name})")
        return
    if __mainAlive == False: return

    while True:
        try:
            if encoded:
                with open(name, "wb") as f:
                    f.write(cryptor.decrypt(add_to_16(r.content)))
            else:
                with open(name, "wb") as f:
                    f.write(r.content)
        except (KeyboardInterrupt, EOFError):
            if os.path.exists(name): os.remove(name)
            return
        except Exception as e:
            if os.path.exists(name): os.remove(name)
            print(f"Something error, retrying... ({name}), ", e)
            time.sleep(0.5)
        else:
            return

downloadpath = "Downloads/"
#https://v7.dious.cc/20210326/oGO9MXsC/index.m3u8

mergedone = False
def startmerge(total, filename):
    global __mainAlive, mergedone, now, downloadpath
    kill = False
    if total == -1:
        total = 10000000
        kill = True
    while now < total:
        while not os.path.exists(os.path.join(downloadpath, "%07d.ts" % now)):
            if kill: return
            if not __mainAlive: return
            time.sleep(1)
        if not __mainAlive and not kill: return
        try:
            with open(os.path.join(downloadpath, "%07d.ts" % now), "rb") as src:
                res = src.read()
        except:
            if kill: return
            time.sleep(0.5)
            continue
        with open(os.path.join(downloadpath, f"{filename}.mp4"), "ab+") as dst:
            dst.write(res)
        now += 1
        with open(os.path.join(downloadpath, "downloading.inf"), "w") as f:
            f.write(f"{now}")
    if kill:
        total = now
        print("total:", total)
    now = 0
    if not __mainAlive and not kill: return
    while now < total:
        if os.path.exists(os.path.join(downloadpath, "%07d.ts" % now)):
            os.remove(os.path.join(downloadpath, "%07d.ts" % now))
        now += 1

    mergedone = True

MAXTHREAD = 30
cryptor = None

def main(url, filename="new"):
    global headers, __mainAlive, total, count, downloadpath, now, cryptor, mergedone
    __mainAlive = True
    res = _get(url = url, headers = headers, timeout = 15, details = "main")
    if "EXT-X-STREAM-INF" in res.text:  
        file_line = res.text.split("\n")
        for line in file_line:
            if '.m3u8' in line:
                url = requests.compat.urljoin(url, line)
                print("real url:", url)
                res = _get(url = url, headers = headers, timeout = 15, details = "main")

    ts_list = res.text.replace("\r\n", '\n').split('\n')
    # with open("index.m3u8", 'wb') as f:
    #     f.write(res.content)
    # print(ts_list)
    # exit()
    if ts_list[0] != "#EXTM3U":
        print("not M3U8.")
        print(ts_list)
        exit()

    total = 0
    for line in ts_list:
        if line and "#" not in line:
            total += 1
    print("total:", total)
    # with open("index.m3u8","r") as f:
    #     ts_list = f.readlines()

    count = 0
    if not os.path.exists(downloadpath):
        os.mkdir(downloadpath)

    downloadpath = os.path.join(downloadpath, hashlib.new('sha256', url.encode()).hexdigest()[:16])
    if not os.path.exists(downloadpath):
        os.mkdir(downloadpath)

    with open(os.path.join(downloadpath, "url.txt"), 'w') as f:
        f.write(url)

    if not os.path.exists(os.path.join(downloadpath, "downloading.inf")): now = 0
    else:
        try:
            with open(os.path.join(downloadpath, "downloading.inf"), "r") as f:
                now = int(f.read())
        except: now = 0
    if now == 0:
        with open(os.path.join(downloadpath, f"{filename}.mp4"), "wb") as dst:
            dst.write(b'')

    threading.Thread(target=startmerge, args=(total, filename)).start()

    encrypted = False
    for line in ts_list:
        if "#EXT-X-KEY" in line:
            method_pos = line.find("METHOD")
            comma_pos = line.find(",")
            if comma_pos == -1:
                comma_pos = len(line)
            method = line[method_pos:comma_pos].split('=')[1]
            print("Decode Method: ", method)
            if method == "NONE":
                encrypted = False
            else:
                encrypted = True
                uri_pos = line.find("URI")
                quotation_mark_pos = line.rfind('"')
                key_url = line[uri_pos:quotation_mark_pos].split('"')[1]
                key_url = requests.compat.urljoin(url, key_url)
                res = _get(url = key_url, headers = headers, timeout = 15, details = "key")
                key = res.content
                print("key: " , key)
                cryptor = AES.new(key, AES.MODE_CBC, key)

        elif line and "#" not in line:
            if mergedone: exit()
            if count >= now and not os.path.exists(os.path.join(downloadpath, "%07d.ts" % count)):
                line = requests.compat.urljoin(url, line.replace("\n", ""))
                if mergedone: exit()
                while(threading.active_count() > MAXTHREAD): time.sleep(1)
                if mergedone: exit()
                threading.Thread(target=download, args=(line, os.path.join(downloadpath, "%07d.ts" % count), encrypted, cryptor)).start()
            count = count + 1
            print(f"{int(count / total * 1000) / 10}%, {count}/{total}", end = '\r')

    print("\n\nWaiting threads end...")

import argparse

def setMainDead():
    __mainAlive = False

def setMainAlive():
    __mainAlive = True

def MainDownload(url, filename):
    def Main(url, filename):
        try:
            main(url=url, filename=filename)
        except Exception as e:
            print("main error", e)

    try:
        threading.Thread(target=Main, args=(url, filename)).start()
        while(True):
            time.sleep(1)
            print(f"active_count: {threading.active_count()}", end = '\r')
            if threading.active_count() == 1:
                break
    # except KeyboardInterrupt:
    #     print("Main dead.")
    #     __mainAlive = False
    except Exception as e:
        print(e)
        print("###Main dead.")
        __mainAlive = False
        return False
    else:
        print("###Main dead.")
        __mainAlive = False
        return True

if __name__ == "__main__":
    args = ArgParser().parse_args()
    if args.url:
        url = args.url
    else:
        url = input("input url:") #https://vod2.bdzybf2.com/20201023/uXcl3glH/1000kb/hls/index.m3u8
    video_name = args.video_name

    if url[:5] == "merge":
        downloadpath = input("input downloadpath:")
        if not os.path.exists(os.path.join(downloadpath, f"{video_name}.txt")): now = 0
        else:
            try:
                with open(os.path.join(downloadpath, f"{video_name}.txt"), "r") as f:
                    now = int(f.read())
            except: now = 0
        if now == 0:
            with open(os.path.join(downloadpath, f"{video_name}.mp4"), "wb") as dst:
                dst.write(b'')
        startmerge(-1, f"{video_name}")
    else:
        MainDownload(url, f"{video_name}")
