import os
import time

import requests
from pyrate_limiter import RequestRate, Duration, Limiter


class Transcriber:
    def __init__(self, url: str, key: str = "", model: str = "", speakers: str = "", old_clean: int = 0):
        self.__url = url
        self.__key = key
        self.__model = model
        self.__speakers = speakers
        self.__old_clean = old_clean
        rate = RequestRate(10, Duration.SECOND)
        self.limiter = Limiter(rate)

    def predict(self, file: str, update_f) -> (str, str):
        try:
            _id = self.upload(file)
            print("send " + _id)
            finished = False
            while not finished:
                finished, st = self.is_finished(_id)
                update_f(st[0], st[1])
                if not finished:
                    time.sleep(1)
            res = self.get_result(_id, "resultFinal.txt")
            res_lat = self.get_result(_id, "lat.restored.txt")
            print("done " + _id)
            self.clean(_id)
            print("cleaned " + _id)
        except BaseException as err:
            raise err
        return res, res_lat

    def upload(self, file):
        with open(file, 'rb') as f:
            files = {'file': (os.path.basename(file).replace("..", "."), f.read())}
        # values = {'recognizer': 'ben', 'numberOfSpeakers': '1'}
        values = {'recognizer': self.__model, 'numberOfSpeakers': self.__speakers}
        url = "%s/ausis/transcriber/upload" % self.__url
        headers = {}
        if self.__key:
            headers = {"Authorization": "Key " + self.__key}
        self.rate_limit()
        r = requests.post(url, files=files, data=values, timeout=120, headers=headers)
        if r.status_code != 200:
            raise Exception("Can't upload '{}'".format(r.text))
        return r.json()["id"]

    def is_finished(self, _id):
        url = "%s/ausis/status.service/status/%s" % (self.__url, _id)
        self.rate_limit()
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            raise Exception("Can't get status '{}'".format(r.text))
        st = r.json()
        if st.get("error", ""):
            raise Exception(st["error"])
        return st["status"] == "COMPLETED", (st["progress"], st["status"])

    def get_result(self, _id: str, _file: str):
        url = "%s/ausis/result.service/result/%s/%s" % (self.__url, _id, _file)
        self.rate_limit()
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            raise Exception("Can't get result '{}'".format(r.text))
        return r.text

    def clean(self, _id):
        url = "%s/ausis/clean.service/delete/%s" % (self.__url, _id)
        if self.__old_clean > 0:
            url = "%s/ausis/clean.service/%s" % (self.__url, _id)
        self.rate_limit()
        r = requests.delete(url, timeout=10)
        if r.status_code != 200:
            raise Exception("Can't clean transcription '{}'".format(r.text))

    def rate_limit(self):
        self.limiter.ratelimit("request", delay=True, max_delay=Duration.SECOND * 60)
