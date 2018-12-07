import logging
import struct
from collections import namedtuple, deque
from evdev import UInput, AbsInfo, ecodes as ec
from time import time
from ebeam import ebeam

class ebeam_evdev(ebeam):
    """
    Bridge ebeam data to evdev
    """
    cap = {
        ec.EV_KEY : [ec.KEY_LEFTCTRL, ec.KEY_P, ec.KEY_PRINT, ec.KEY_F11],
        ec.EV_ABS : [
                (ec.ABS_X, AbsInfo(value=0, min=0, max=0xFFFF, fuzz=0, flat=0, resolution=0)),
                (ec.ABS_Y, AbsInfo(value=0, min=0, max=0xFFFF, fuzz=0, flat=0, resolution=0)),
                ]
    }

    def __init__(self, devname):
        ebeam.__init__(self, devname)
        self.ui = UInput(self.cap, name='ebeam', version=0x01)
        self.cur_x = None
        self.cur_y = None
        self.lasttime = time()
        self.button_queue = deque([], 3)

    def average_buttons(self, buttons):
        self.button_queue.append(buttons)
        count = [0, 0, 0]
        l = len(self.button_queue)
        for x in self.button_queue:
            for i in range(3):
                if x[i]: 
                    count[i] += 1
        return [ x > (l/2) for x in count]

    def got_frame(self, raw_data):
        now = time()
        delta_t = now-self.lasttime
        logging.debug( "pos=({}|{}) raw_x={} raw_y={} buttons={} delta_t={}".format(self.x, self.y, self.raw_x, self.raw_y, self.buttons, delta_t ) )
        self.lasttime = now

        # Smooth X/Y data
        if self.cur_x == None:
            self.cur_x = self.x
            self.cur_y = self.y
        self.cur_x = (self.cur_x + self.x)/2
        self.cur_y = (self.cur_y + self.y)/2
        # Majority-Vote buttons
        btn = self.average_buttons(self.buttons)

        self.ui.write(ec.EV_ABS, ec.ABS_X, self.x)
        self.ui.write(ec.EV_ABS, ec.ABS_Y, self.y)
        self.ui.write(ec.EV_KEY, ec.BTN_LEFT, btn[0])
        self.ui.write(ec.EV_KEY, ec.BTN_MIDDLE, btn[1])
        self.ui.write(ec.EV_KEY, ec.BTN_RIGHT, btn[2])
        self.ui.write(ec.EV_KEY, ec.KEY_LEFTCTRL, "PRINT" in self.keys)
        self.ui.write(ec.EV_KEY, ec.KEY_P, "PRINT" in self.keys)
        self.ui.write(ec.EV_KEY, ec.KEY_F11, "FULLSCREEN" in self.keys)
        self.ui.syn()
    

x = ebeam_evdev("/dev/hidraw0")

x.run()
