import time
import os
from strange import Download, lock_running, headers
import threading
import requests

_downloadAccomplishedLock = threading.Lock()

def total_count(download_mains):
    return sum([download_main.total for download_main in download_mains])

def downloaded_count(download_mains):
    return sum([download_main.downloaded_count() for download_main in download_mains])

def MainDownload(download_mains):
    download_total = len(download_mains)
    download_accomplished = 0

    def download_accomplishing():
        nonlocal download_accomplished
        download_accomplished += 1

    def Main(download_main):
        try:
            ret = download_main.run()
            if ret == 0:
                raise RuntimeError("Unexpected error")
            lock_running(lock=_downloadAccomplishedLock, func=download_accomplishing)
        except Exception as e:
            print("main error", e)
            raise

    try:
        for download_main in download_mains:
            download_thread = threading.Thread(target=Main, args=(download_main,))
            download_thread.start()
        while download_accomplished < download_total:
            if total_count(download_mains) != 0:
                print(f"{int(downloaded_count(download_mains) / total_count(download_mains) * 1000) / 10}%, {downloaded_count(download_mains)}/{total_count(download_mains)}", end = '\r')
            time.sleep(0.1)
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
    with open("agedownload.txt", 'r', encoding="utf8") as f:
        r = f.read()
    r = r.split('\n')

    download_mains = []
    count = 1
    for x in r:
        if not x:
            continue

        try:
            # headers["origin"] = "https://www.agemys.cc/"
            res = requests.get(url=x, headers=headers)
            if "text/html" in res.headers.get("content-type").lower().replace("; ", ";").split(";"): # age type
                new_url = res.text.split('video_url', 1)[1].split("\'", 2)[1]
                new_url = requests.compat.urljoin(x, new_url)
                print("Age:", new_url)
                download_main = Download(new_url, f"{count}")
            else:
                download_main = Download(x, f"{count}")
            download_mains.append(download_main)
        except Exception as e:
            print(f"{count} Error. ", e.__repr__())

        count += 1
        # os.system(f"start /MIN cmd /K python strange.py -u=\"{x}\" -o={count}")

    MainDownload(download_mains)