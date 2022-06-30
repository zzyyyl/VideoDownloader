import time
import os
from strange import Download, lock_running
import threading

_downloadAccomplishedLock = threading.Lock()

def total_count(download_mains):
    return sum([download_main.total for download_main in download_mains])

def downloaded_count(download_mains):
    return sum([download_main.downloaded_count() for download_main in download_mains])

def download_accomplishing():
    download_accomplished += 1

def MainDownload(download_mains):
    download_total = len(download_mains)
    download_accomplished = 0
    def Main(download_main):
        nonlocal download_accomplished
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
    with open("download.txt", 'r', encoding="utf8") as f:
        r = f.read()
    r = r.split('\n')

    download_mains = []
    count = 1
    for x in r:
        if not x:
            continue
        # os.system(f"start /MIN cmd /K python strange.py -u=\"{x}\" -o={count}")
        download_main = Download(x, f"{count}")
        download_mains.append(download_main)
        count += 1

    MainDownload(download_mains)