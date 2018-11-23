import usb.core
import logging
import struct
from collections import namedtuple

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
    _supported_devices = {
        (0x2650, 0x1320): "eBeam BT USB",
        (0x2650, 0x1315): "eBeam USB",
        (0x2650, 0x1311): "eBeam USB2",
        (0x2650, 0x1313): "eBeam BT"
        }

    _calmatrix = [ 1, 0, 0, 0,
                   0, 1, 0, 0,
                   0, 0, 1, 0,
                   0, 0, 0, 1 ]

    def __init__(self):
        for key in self._supported_devices:
            (vid, pid) = key
            dev = usb.core.find(idVendor=vid, idProduct=pid)
            if dev is not None:
                if dev.is_kernel_driver_active(0):
                    dev.detach_kernel_driver(0)
                dev.set_configuration()
                self.cfg = dev.get_active_configuration()

                self.endpnt = usb.util.find_descriptor(
                    self.cfg[(0,0)],
                    # match the first OUT endpoint
                    custom_match = \
                    lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

                self.dev = dev
                self.ok = True
                self._pktlen = struct.calcsize(self._fmt)
                return
        logging.error("No matching device found..")
        self.ok = False

    def run(self):
        while True:
            logging.debug("Will read form endpoint {}, len {}".format(self.endpnt, self._pktlen))
            pkt = self.dev.read(self.endpnt, self._pktlen, 500)
            if pkt is None:
                break
            self.process_frame(pkt)

    def process_frame(self, pkt):
        data = self._tuple(*struct.unpack(self._fmt, pkt))
        logging.error( repr(data) )


x = ebeam()
x.run()
