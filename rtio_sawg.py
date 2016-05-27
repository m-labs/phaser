from collections import namedtuple

from migen import *
from artiq.gateware.rtio import rtlink

import sawg


_Phy = namedtuple("Phy", "rtlink probes overrides")


class Channel(sawg.Channel):
    def __init__(self, *args, **kwargs):
        sawg.Channel.__init__(self, *args, **kwargs)
        self.phys = []
        for i in self.i:
            rl = rtlink.Interface(rtlink.OInterface(len(i.payload)))
            self.comb += [
                i.stb.eq(rl.o.stb),
                rl.o.busy.eq(~i.ack),
                Cat(i.payload.flatten()).eq(rl.o.data),
            ]
            self.phys.append(_Phy(rl, [], []))
