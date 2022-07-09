import requests
import threading
import time
import os
import random
import hashlib
from Crypto.Cipher import AES
from _argparse import ArgParser


class LockError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return f"LockError: {self.text}"

__netSemaphore = threading.BoundedSemaphore(100)
# write_lock = threading.Lock()
_downloadSemaphore = threading.BoundedSemaphore(150)
_downloadListLock = threading.Lock()
_downloadList = []

def lock_acquire(lock, need_break_func=lambda: False, noexcept=False, callback=lambda: None):
    acquired = False
    try:
        while not acquired:
            if need_break_func():
                break
            acquired = lock.acquire()
    except Exception as e:
        if acquired:
            lock.release()
            acquired = False
        if noexcept:
            return False
        else:
            raise LockError(f"error while acquire, {e.__str__()}")

    if not acquired:
        if noexcept:
            return False
        else:
            raise LockError("lock acquire failed")

    try:
        callback()
    except Exception as e:
        lock.release()
        if noexcept:
            return False
        else:
            raise LockError(f"callback error while acquire, {e.__str__()}")

    return True

def lock_release(lock, noexcept=False, callback=lambda: None):
    try:
        callback()
    except Exception as e:
        lock.release()
        if noexcept:
            return False
        else:
            raise LockError(f"callback error while release, {e.__str__()}")

    lock.release()

def lock_running(lock, need_break_func=lambda: False, func=lambda: None):
    try: lock_acquire(lock=lock, need_break_func=need_break_func)
    except: raise

    try: res = func()
    except:
        lock_release(lock)
        raise
    else: lock_release(lock)

    return res

def add_to_16(value):
    if type(value) == str:
        x00 = '\x00'
    elif type(value) == bytes:
        x00 = b'\x00'
    else:
        x00 = '\x00'

    while len(value) % 16 != 0: value += x00
    return value


def _get(url, headers, timeout, details, need_break_func=lambda: None):
    random.seed(time.time())
    rt = 0
    while True:
        rt += 1
        try:
            res = lock_running(lock=__netSemaphore,
                need_break_func=need_break_func,
                func=lambda: requests.get(url=url, headers=headers, timeout=timeout))
        except (KeyboardInterrupt, EOFError):
            return False
        except Exception as e:
            print(f"Request error, retrying... ({details}, {rt}), ", e)
            for i in range(0, rt % 5):
                if need_break_func(): return False
                time.sleep(0.1)
            time.sleep(random.random() * 3)
            if need_break_func(): return False
        else:
            return res


headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36 Edg/103.0.1264.37'
}

class Download:

    class DownloadError(Exception):
        def __init__(self, text):
            self.text = text

        def __str__(self):
            return f"DownloadError: {self.text}"

    _mainAlive = False

    def setMainDead(self):
        self._mainAlive = False

    def setMainAlive(self):
        self._mainAlive = True

    def mainAlive(self):
        return self._mainAlive

    def mainNotAlive(self):
        return not self._mainAlive

    def __init__(self, url, filename="new"):
        self.origin_url = url
        self.filename = filename
        self._download_count = 0 # downloading + downloaded
        self._running_count = 0  # downloading
        self.total = 0

    def downloaded_count(self):
        return self._download_count - self._running_count

    def _download_start(self, url):
        def increasing():
            _downloadList.append(url)
            self._running_count += 1
        lock_running(lock=_downloadListLock, need_break_func=self.mainNotAlive, func=increasing)
        return lock_acquire(lock=_downloadSemaphore, need_break_func=self.mainNotAlive)

    def _download_check_started(self, url):
        return lock_running(lock=_downloadListLock, need_break_func=self.mainNotAlive, func=lambda: url in _downloadList)

    def _download_end(self, url):
        def decreasing():
            _downloadList.remove(url)
            self._running_count -= 1
        lock_running(lock=_downloadListLock, need_break_func=self.mainNotAlive, func=decreasing)
        return lock_release(_downloadSemaphore)

    ###下载ts文件
    def _download_main(self, url, name, encoded=False, cryptor=None):
        if not self._download_check_started(url): self._download_start(url)
        while True:
            if self.mainNotAlive(): return
            r = _get(url=url, headers=headers, timeout=15, details=name, need_break_func=self.mainNotAlive)
            if r.status_code == 200 and r.headers.get("content-type").lower() != "text/html":
                break
            else:
                print(f"Request error, status code={r.status_code},", 
                      f"content-type={r.headers.get('content-type')},",
                      f"retrying... ({name})")
                # print("headers:", r.headers)
                # print("content:", r.content)
                time.sleep(2)

        if not r:
            print(f"Unknown error, ({name})")
            return
        if self.mainNotAlive(): return

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

    def _download(self, url, name, encoded=False, cryptor=None):
        self._download_main(url, name, encoded, cryptor)
        self._download_end(url)

    default_folder = "Downloads/"

    def run(self):
        self.setMainAlive()
        cryptor = None
        url = self.origin_url
        res = _get(url=url, headers=headers, timeout=15, details="run", need_break_func=self.mainNotAlive)
        if "EXT-X-STREAM-INF" in res.text:  
            file_line = res.text.split("\n")
            for line in file_line:
                if '.m3u8' in line:
                    url = requests.compat.urljoin(url, line)
                    # print("real url:", url)
                    res = _get(url=url, headers=headers, timeout=15, details="run", need_break_func=self.mainNotAlive)

        ts_list = res.text.replace("\r\n", '\n').split('\n')
        # with open("index.m3u8", 'wb') as f:
        #     f.write(res.content)
        # print(ts_list)
        # exit()
        if ts_list[0] != "#EXTM3U":
            print(ts_list)
            raise DownloadError(f"{url} is not M3U8")

        self.total = 0
        for line in ts_list:
            if line and "#" not in line:
                self.total += 1
        print("total:", self.total)
        # with open("index.m3u8","r") as f:
        #     ts_list = f.readlines()

        self._download_count = 0
        try:
            if not os.path.exists(self.default_folder):
                os.mkdir(self.default_folder)
        except Exception as e:
            print("Warning:", e.__repr__())

        folder = os.path.join(self.default_folder, hashlib.new('sha256', url.encode()).hexdigest()[:16])
        if not os.path.exists(folder):
            os.mkdir(folder)

        with open(os.path.join(folder, "url.txt"), 'w') as f:
            f.write(f"origin: {self.origin_url}\nurl: {url}")

        if not os.path.exists(os.path.join(folder, "downloading.inf")): now = 0
        else:
            try:
                with open(os.path.join(folder, "downloading.inf"), "r") as f:
                    now = int(f.read())
            except: now = 0
        if now == 0:
            with open(os.path.join(folder, f"{self.filename}.mp4"), "wb") as dst:
                dst.write(b'')

        mergedone = False
        def startmerge(folder):
            nonlocal now, mergedone
            # kill = False
            # if self.total == -1:
            #     self.total = 10000000
            #     kill = True
            while now < self.total:
                while not os.path.exists(os.path.join(folder, "%07d.ts" % now)):
                    # if kill: return False
                    if self.mainNotAlive(): return False
                    time.sleep(1)
                if self.mainNotAlive(): return False
                # if self.mainNotAlive() and not kill: return False
                try:
                    with open(os.path.join(folder, "%07d.ts" % now), "rb") as src:
                        res = src.read()
                except:
                    # if kill: return False
                    time.sleep(0.5)
                    continue
                if res[1:4] == b"PNG": res = res[4:] # for age!
                with open(os.path.join(folder, f"{self.filename}.mp4"), "ab+") as dst:
                    dst.write(res)
                now += 1
                with open(os.path.join(folder, "downloading.inf"), "w") as f:
                    f.write(f"{now}")
            # if kill:
            #     self.total = now
            #     print("self.total:", self.total)
            mergeing_now = 0
            if self.mainNotAlive(): return False
            # if self.mainNotAlive() and not kill: return False
            while mergeing_now < self.total:
                if os.path.exists(os.path.join(folder, "%07d.ts" % mergeing_now)):
                    os.remove(os.path.join(folder, "%07d.ts" % mergeing_now))
                mergeing_now += 1
            mergedone = True

        threading.Thread(target=startmerge, args=(folder,)).start()

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
                    res = _get(url = key_url, headers = headers, timeout = 15, details = "key", need_break_func=self.mainNotAlive)
                    key = res.content
                    print("key: " , key)
                    cryptor = AES.new(key, AES.MODE_CBC, key)

            elif line and "#" not in line:
                if mergedone: return True
                if self._download_count >= now and not os.path.exists(os.path.join(folder, "%07d.ts" % self._download_count)):
                    line = requests.compat.urljoin(url, line.replace("\n", ""))
                    if mergedone: return True
                    self._download_start(url=line)
                    threading.Thread(target=self._download, args=(line, os.path.join(folder, "%07d.ts" % self._download_count), encrypted, cryptor)).start()
                self._download_count = self._download_count + 1
                # print(f"{int((self._download_count - self._running_count) / self.total * 1000) / 10}%, {self._download_count - self._running_count}/{self.total}", end = '\r')

        while self._running_count:
            # print(f"{int((self.total - self._running_count) / self.total * 1000) / 10}%, {self.total - self._running_count}/{self.total}", end = '\r')
            time.sleep(1)
        while not mergedone:
            # print(f"{int((self.total - self._running_count) / self.total * 1000) / 10}%, {self.total - self._running_count}/{self.total}, merging...", end = '\r')
            time.sleep(1)
        return True

def MainDownload(url, filename):
    download_main = Download(url, filename)
    download_accomplished = False
    def Main(url, filename):
        nonlocal download_main, download_accomplished
        try:
            download_accomplished = download_main.run()
        except Exception as e:
            print("main error", e)
            raise

    try:
        download_thread = threading.Thread(target=Main, args=(url, filename))
        download_thread.start()
        while not download_accomplished:
            time.sleep(1)
            pass
    except Exception as e:
        print(e)
        print("###Main error and dead.")
        download_main.setMainDead()
        download_thread.join()
        return False
    else:
        print("###Main accomplished and dead.")
        download_main.setMainDead()
        download_thread.join()
        return True

if __name__ == "__main__":
    args = ArgParser().parse_args()
    if args.url:
        url = args.url
    else:
        url = input("input url:") #https://vod2.bdzybf2.com/20201023/uXcl3glH/1000kb/hls/index.m3u8
    video_name = args.video_name

    # if url[:5] == "merge":
    #     folder = input("input folder:")
    #     if not folder: folder = Download.default_folder
    #     if not os.path.exists(os.path.join(folder, f"{video_name}.txt")): now = 0
    #     else:
    #         try:
    #             with open(os.path.join(folder, f"{video_name}.txt"), "r") as f:
    #                 now = int(f.read())
    #         except: now = 0
    #     if now == 0:
    #         with open(os.path.join(folder, f"{video_name}.mp4"), "wb") as dst:
    #             dst.write(b'')
    #     startmerge(folder, -1, f"{video_name}")
    # else:
    MainDownload(url, f"{video_name}")
