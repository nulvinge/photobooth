import subprocess
from threading import Thread
from Queue import Queue, Empty
import traceback


class BTMon:
    def __init__(self, addr, channel, cb):
        try:
            cmd = ["gatttool", "--device=" + addr, "--char-write-req", "--handle=0x000e", "--value=0000", "--listen"]
            self._p = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, shell=False)
            self._s = self._p.stdout

            def _populateQueue(stream, channel, cb):
                while True:
                    line = stream.readline()
                    if line:
                        print("Btmon " + str(channel) + ":" + line,)
                        if line.find("Notification") > -1:
                            cb(channel)
                    else:
                        raise Exception("UnexpectedEndOfStream")

            self._t = Thread(target = _populateQueue, args = (self._s, channel, cb))
            self._t.daemon = True
            self._t.start()
        except Exception as e:
            print("Btmon " + str(channel) + ": Exception: " + repr(e))
            traceback.print_exc()

if __name__ == "__main__":
    btaddr1 = "FF:FF:80:00:76:85"
    btaddr2 = "FF:FF:C3:0D:93:BB"

    def p(x):
        print (x)
    mon1 = BTMon(btaddr1, 1, p)
    mon2 = BTMon(btaddr2, 2, p)
    while True:
        pass

