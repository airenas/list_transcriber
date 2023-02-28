import argparse
import os
import queue
import sys
import threading
from os.path import exists

from tqdm import tqdm

from src.transcriber import Transcriber


class Work:
    def __init__(self, file: str, file_out: str):
        self.file = file
        self.file_out = file_out
        self.wait_queue = queue.Queue(maxsize=1)
        self.str = ""

    def done(self):
        return self.wait_queue.put(self, block=False)

    def wait(self):
        return self.wait_queue.get()

    def predict(self, trans) -> str:
        self.str = predict(trans, self.file, self.file_out)
        self.done()


err_lock = threading.Lock()
err_count = 0


def predict(trans, file, file_out):
    global err_count
    if exists(file_out):
        file_stats = os.stat(file_out)
        if file_stats and file_stats.st_size > 0:
            return "{} - exists".format(file_out)
    try:
        print("sending file %s" % file)
        str = trans.predict(file)
        with open(file_out, "w") as f:
            f.write(str)
    except BaseException as err:
        with err_lock:
            err_count += 1
        return "error {}".format(err)
    return "{} - done".format(file_out)


def main(argv):
    parser = argparse.ArgumentParser(description="Does Common Voice dataset prediction",
                                     epilog="E.g. " + sys.argv[0] + "",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--in_f", nargs='?', required=True, help="List file")
    parser.add_argument("--out_dir", nargs='?', required=True, help="Output dir for transcriptions")
    parser.add_argument("--url", nargs='?', default="https://atpazinimas.intelektika.lt", help="Transcriber URL")
    parser.add_argument("--key", nargs='?', required=False, help="Transcription API secret key")
    parser.add_argument("--workers", nargs='?', type=int, default=4, help="Workers count")
    args = parser.parse_args(args=argv)

    trans = Transcriber(args.url, key=args.key)

    jobs = []
    with open(args.in_f, 'r') as in_f:
        for line in in_f:
            line = line.strip()
            if not line:
                continue
            f = line
            _, fn = os.path.split(f)
            fn = os.path.splitext(fn)[0]
            out_f = os.path.join(args.out_dir, fn + ".txt")
            jobs.append(Work(f, out_f))
    print("URL    : {}".format(args.url))
    print("Workers: {}".format(args.workers))
    print("Files  : {}".format(len(jobs)))
    print("Out Dir: {}".format(args.out_dir))

    job_queue = queue.Queue(maxsize=10)
    workers = []
    wc = args.workers

    def add_jobs():
        for _j in jobs:
            job_queue.put(_j)
        for _i in range(wc):
            job_queue.put(None)

    def start_thread(method):
        thread = threading.Thread(target=method, daemon=True)
        thread.start()
        workers.append(thread)

    start_thread(add_jobs)

    def start():
        while True:
            _j = job_queue.get()
            if _j is None:
                return
            _j.predict(trans)

    for i in range(wc):
        start_thread(start)

    with tqdm("transcribing", total=len(jobs)) as pbar:
        for i, j in enumerate(jobs):
            j.wait()
            pbar.update(1)
            print("%s" % (j.str.replace("\n", " ")))
    for w in workers:
        w.join()
    with err_lock:
        if err_count > 0:
            print("Failed %d" % err_count)
            return 1
        print("DONE")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
