import subprocess
import time
from threading import Thread
from Queue import Queue, Empty
import traceback
import sys


def _populateQueue(addr, channel, cb):
    errors = 0
    while True:
        errors += 1
        try:
            print "Btmon: Starting", channel, errors
            time.sleep(1 + channel)
            cmd = ["gatttool", "--device=" + addr, "--char-write-req", "--handle=0x000e", "--value=0x0000", "--listen"]
            process = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, shell=False)
            stream = process.stdout
            while True:
                line = stream.readline()
                if line:
                    print "Btmon", str(channel) + ":", line,
                    if line.find("Notification") > -1:
                        cb(channel)
                else:
                    print "Btmont ", str(channel) + ":", "Error (" + str(errors) + "): End of stream"
                    traceback.print_exc()
                    sys.stdout.flush()
                    time.sleep(1)
                    break
                    #this.run(addr, channel, cb, errors+1)
                    #self.recbtmon = BTMon(addr, channel, cb, errors+1)
            stream.close()

        except Exception as e:
            print "Btmony", str(channel) + ":", "Exception (", str(errors), "): ", repr(e)
            traceback.print_exc()
            sys.stdout.flush()

class BTMon:
    def run(self, addr, channel, cb):
        try:
            self._t = Thread(target = _populateQueue, args = (addr, channel, cb))
            self._t.daemon = True
            self._t.start()
        except Exception as e:
            print "Btmon", str(channel) + ":", "Exception: ", repr(e)
            traceback.print_exc()
            sys.stdout.flush()

    def __init__(self, addr, channel, cb):
        self.run(addr, channel, cb)

if __name__ == "__main__":
    btaddr1 = "FF:FF:80:00:76:85"
    btaddr2 = "FF:FF:C3:0D:93:BB"

    def p(x):
        print x
    mon1 = BTMon(btaddr1, 1, p)
    mon2 = BTMon(btaddr2, 2, p)
    while True:
        pass

