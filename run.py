import os

if __name__ == "__main__":
    with open("download.txt", 'r') as f:
        r = f.read()
    r = r.split('\n')
    for x in r:
        if not x:
            continue
        os.system(f"start /MIN cmd /C python strange.py -u=\"{x}\"")