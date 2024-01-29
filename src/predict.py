import argparse
import os
import queue
import sys
import threading
from os.path import exists

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress

from src.transcriber import Transcriber


class Work:
    def __init__(self, file: str, file_out: str, file_out_sync: str):
        self.file = file
        self.file_out = file_out
        self.file_out_sync = file_out_sync
        self.wait_queue = queue.Queue(maxsize=1)
        self.str = ""

    def done(self):
        return self.wait_queue.put(self, block=False)

    def wait(self):
        return self.wait_queue.get()

    def predict(self, trans, pb) -> str:
        self.str = predict(trans, self.file, self.file_out, self.file_out_sync, pb)
        self.done()


err_lock = threading.Lock()
err_count = 0


def non_empty_file(file: str):
    if exists(file):
        file_stats = os.stat(file)
        if file_stats and file_stats.st_size > 0:
            return True


def predict(trans, file, file_out, file_out_sync, update_f):
    global err_count
    if exists(file_out) and exists(file_out_sync):
        return "{} - exists".format(file_out)
    try:
        print("sending file %s" % file)
        (txt, lat) = trans.predict(file, update_f)
        with open(file_out, "w") as f:
            f.write(txt)
        with open(file_out_sync, "w") as f:
            f.write(lat)
    except BaseException as err:
        with err_lock:
            err_count += 1
        return "    error {}".format(err)
    return "{} - done".format(file_out)


def main(argv):
    parser = argparse.ArgumentParser(description="Does Common Voice dataset prediction",
                                     epilog="E.g. " + sys.argv[0] + "",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--in_f", nargs='?', required=True, help="List file")
    parser.add_argument("--out_dir", nargs='?', required=True, help="Output dir for transcriptions")
    parser.add_argument("--url", nargs='?', default="https://atpazinimas.intelektika.lt", help="Transcriber URL")
    parser.add_argument("--model", nargs='?', type=str, default="ben", help="Transcriber model")
    parser.add_argument("--speakers", nargs='?', type=str, default="", help="Speakers count")
    parser.add_argument("--old_clean", nargs='?', type=int, default="0", help="Use old clean service")
    parser.add_argument("--key", nargs='?', required=False, help="Transcription API secret key")
    parser.add_argument("--workers", nargs='?', type=int, default=4, help="Workers count")
    args = parser.parse_args(args=argv)

    trans = Transcriber(args.url, key=args.key, model=args.model, speakers=args.speakers, old_clean=args.old_clean)

    progress = Progress()

    jobs = []
    with open(args.in_f, 'r') as in_f:
        for line in in_f:
            line = line.strip()
            if not line:
                continue
            f = line
            _, fn = os.path.split(f)
            fn = os.path.splitext(fn)[0]
            jobs.append(Work(f, file_out=os.path.join(args.out_dir, fn + ".txt"),
                             file_out_sync=os.path.join(args.out_dir, fn + ".sync.txt")))
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
        task = progress.add_task("Transcribing", total=100)
        while True:
            _j = job_queue.get()
            if _j is None:
                return

            _f = os.path.basename(_j.file)
            _f, _ = os.path.splitext(_f)

            def update(st, name):
                progress.update(task, description=f"{_f} - {name}")
                progress.update(task, completed=st)

            progress.update(task, description=f"tr{_f} - Uploading", total=100)

            _j.predict(trans, update)

    for i in range(wc):
        start_thread(start)

    overall_progress = Progress()
    overall_task = overall_progress.add_task("All Jobs", total=len(jobs))
    progress_group = Group(
        Panel(Group(progress)),
        overall_progress,
    )

    with Live(progress_group, refresh_per_second=10):
        for i, j in enumerate(jobs):
            j.wait()
            overall_progress.update(overall_task, advance=1)
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
