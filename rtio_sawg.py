from collections import namedtuple

from migen import *
from artiq.gateware.rtio import rtlink

import sawg


_Phy = namedtuple("Phy", "rtlink probes overrides")


class Channel(Module):
    def __init__(self, *args, **kwargs):
        self.submodules._ll = ClockDomainsRenamer("rio_phy")(
            sawg.Channel(*args, **kwargs))
        self.phys = []
        for i in self._ll.i:
            rl = rtlink.Interface(rtlink.OInterface(
                min(64, len(i.payload))))
            self.comb += [
                i.stb.eq(rl.o.stb),
                rl.o.busy.eq(~i.ack),
                Cat(i.payload.flatten()).eq(rl.o.data),
            ]
            # TODO: probes, overrides
            self.phys.append(_Phy(rl, [], []))

    def connect_q(self, other):
        return self._ll.connect_q(other._ll)
