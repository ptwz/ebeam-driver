import logging
import struct
from collections import namedtuple
from evdev import UInput, AbsInfo, ecodes as ec



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
     *  pkt[5] : fiability ?
     *	often 0xC0
     *	> 0x80 : OK
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
    _fmt = "<bHHbbb"
    _tuple = namedtuple("ebeam_pkt", "sensors,raw_x,raw_y,fiability1,buttons,fiability2".split(","))

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
            # All bits set: Position should be valid
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
        self.got_frame()

    def got_frame(self):
        """
        Stub for implementing proper drivers
        """
        logging.error( "pos=({}|{}) raw_x={} raw_y={} buttons={}".format(self.x, self.y, self.raw_x, self.raw_y, self.buttons ) )

class ebeam_evdev(ebeam):
    """
    Bridge ebeam data to evdev
    """
    cap = {
        ec.EV_KEY : [ec.KEY_A, ec.KEY_B, ec.BTN_LEFT],
        ec.EV_ABS : [
                (ec.ABS_X, AbsInfo(value=0, min=0, max=0xFFFF, fuzz=0, flat=0, resolution=0)),
                (ec.ABS_Y, AbsInfo(value=0, min=0, max=0xFFFF, fuzz=0, flat=0, resolution=0)),
                ]
    }

    def __init__(self, devname):
        ebeam.__init__(self, devname)
        self.ui = UInput(self.cap, name='ebeam', version=0x01)

    def got_frame(self):
        logging.error( "pos=({}|{}) raw_x={} raw_y={} buttons={}".format(self.x, self.y, self.raw_x, self.raw_y, self.buttons ) )
        self.ui.write(ec.EV_ABS, ec.ABS_X, self.raw_x)
        self.ui.write(ec.EV_ABS, ec.ABS_Y, self.raw_y)
        self.ui.write(ec.EV_KEY, ec.BTN_LEFT, self.buttons[0])
        self.ui.write(ec.EV_KEY, ec.BTN_MIDDLE, self.buttons[1])
        self.ui.write(ec.EV_KEY, ec.BTN_RIGHT, self.buttons[2])
        self.ui.syn()
    

x = ebeam_evdev("/dev/hidraw0")

x.run()
