from collections import namedtuple

from migen import *
from artiq.gateware.rtio import rtlink

import sawg


_Phy = namedtuple("Phy", "rtlink probes overrides")


class Channel(sawg.Channel):
    def __init__(self, *args, **kwargs):
        sawg.Channel.__init__(self, *args, **kwargs)
        self.phys = []
        self.phys_names = {}
        for j, i in enumerate(self.i):
            rl = rtlink.Interface(rtlink.OInterface(
                min(64, len(i.payload))))
            self.comb += [
                i.stb.eq(rl.o.stb),
                rl.o.busy.eq(~i.ack),
                Cat(i.payload.flatten()).eq(rl.o.data),
            ]
            # TODO: probes, overrides
            phy = _Phy(rl, [], [])
            self.phys.append(phy)
            self.phys_names[self.i_names[j]] = phy
