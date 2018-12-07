import logging
import struct
from collections import namedtuple, deque
from evdev import UInput, AbsInfo, ecodes as ec
from time import time


class ebeam(object):
    """
     * Packet description : 8 bytes
     *
     *  nop packet : FF FF FF FF FF FF FF FF
     *
     *  pkt[0] : Sensors
     *	bit 1 : ultrasound signal (guessed)
     *	bit 2 : IR signal (tested with a remote...) ;
     *	readings OK : 0x03 (anything else is a show-stopper)
     *
     *  pkt[1] : raw_x low
     *  pkt[2] : raw_x high
     *
     *  pkt[3] : raw_y low
     *  pkt[4] : raw_y high
     *
     *  pkt[5] : keyboad info?
     *      When pressing membrane keys (calibrate,etc) on the board
     *      sensors==3 and buttons==0xFE:
     *      bit 0 : ????
     *      bit 1 : Screen plus (==Fullscreen?)
     *      bit 2 : Mirror
     *      bit 3 : Print
     *      bit 4 : E-Mail
     *      bit 5 : Movie?
     *      bit 7 : Calibrate
     *
     *  pkt[6] :
     *	buttons state (low 4 bits)
     *		0x1 = no buttons
     *		bit 0 : tip (WARNING inversed : 0=pressed)
     *		bit 1 : ? (always 0 during tests)
     *		bit 2 : little (1=pressed)
     *		bit 3 : big (1=pressed)
     *
     *	pointer ID : (hight 4 bits)
     *		Tested  : 0x6=wand ;
     *		Guessed : 0x1=red ; 0x2=blue ; 0x3=green ; 0x4=black ;
     *			  0x5=eraser
     *		bit 4 : pointer ID
     *		bit 5 : pointer ID
     *		bit 6 : pointer ID
     *		bit 7 : pointer ID
     *
     *
     *  pkt[7] : fiability ?
     *	often 0xFF
    """
    _fmt = "<BHHBBB"
    _tuple = namedtuple("ebeam_pkt", "sensors,raw_x,raw_y,keyboard,buttons,fiability2".split(","))

    _calmatrix = [ 1, 0, 0,
                   0, 1, 0,
                   0, 0, 1 ]

    def __init__(self, devname):
        self.dev = open(devname, "rb")
        self.ok = False
        self._pktlen = struct.calcsize(self._fmt)
        self.raw_x = 0
        self.raw_y = 0
        self.buttons = [0, 0, 0]
        self.calibrated = False
        self.keymap = {0x02: "FULLSCREEN", 0x04: "MIRROR", 0x08: "PRINT", 0x10: "EMAIL", 0x20: "MOVIE", 0x40: "CALIBRATE"}
        self.keys = set()

    def run(self):
        while True:
            logging.debug("Will read len {}".format(self._pktlen))
            pkt = self.dev.read(self._pktlen)
            if pkt is None:
                break
            self.process_frame(pkt)

    def process_frame(self, pkt):
        data = self._tuple(*struct.unpack(self._fmt, pkt))
        if data.sensors & 3 == 3:
            # All bits set: Datagram should be valid

            if data.buttons == 0xFE:
                # Only keypress on board
                self.keys.clear()
                for x in self.keymap:
                    if data.keyboard & x:
                        self.keys.add(self.keymap[x])
            else:
                # When actual buttons are pressed on stylus
                self.raw_x = data.raw_x
                self.raw_y = data.raw_y

                scale = self._calmatrix[6] * self.raw_x + self._calmatrix[7] * self.raw_y + self._calmatrix[8];

                if scale==0:
                    return

                if self.calibrated:
                    self.x = (self._calmatrix[0] * self.raw_x +
                                   self._calmatrix[1] * self.raw_y +
                                   self._calmatrix[2]) / scale
                    self.y = (self._calmatrix[3] * self.raw_x +
                                   self._calmatrix[4] * self.raw_y +
                                   self._calmatrix[5]) / scale 
                else:
                    self.x = self.raw_x
                    self.y = self.raw_y

                self.buttons = [ (data.buttons & 1 == 0), # bit0 inverted!!!
                                 (data.buttons & 2 == 1),
                                 (data.buttons & 4 == 1)
                         ]
        self.got_frame(data)

    def got_frame(self, raw_data):
        """
        Stub for implementing proper drivers
        """
        print (raw_data, self.keys)
