import os

def copy(src: str, dst: str):
    os.popen(f"copy \"{src}\" \"{dst}\"", 'r').close()

def make_or_del(path):
    if not os.path.exists(path): os.mkdir(path)
    else: os.popen(f"del \"{path}\" /Q", 'r').close()


if __name__ == "__main__":
    output_origin_path = ".\\Downloads"

    make_or_del(os.path.join(output_origin_path, "summary"))

    for root, dirs, files in os.walk(output_origin_path):
        for f in files:
            if os.path.splitext(f)[1] != ".mp4":
                continue
            file = os.path.join(root, f)
            copy(file, os.path.join(output_origin_path, "summary", f))
