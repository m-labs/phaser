from migen import *


def set_dict(e, **k):
    for k, v in k.items():
        if isinstance(v, dict):
            yield from set_dict(getattr(e, k), **v)
        else:
            yield getattr(e, k).eq(v)


def xfer(dut, **kw):
    ep = []
    for e, v in kw.items():
        e = getattr(dut, e)
        yield from set_dict(e, **v)
        ep.append(e)
    for e in ep:
        yield e.stb.eq(1)
    while ep:
        yield
        for e in ep[:]:
            if hasattr(e, "busy") and (yield e.busy):
                raise ValueError(e, "busy")
            if not hasattr(e, "ack") or (yield e.ack):
                yield e.stb.eq(0)
                ep.remove(e)


class Delay(Module):
    def __init__(self, i, delay, o=None):
        if isinstance(i, (int, tuple)):
            z = [Signal(i) for j in range(delay + 1)]
        elif isinstance(i, list):
            z = [Record(i) for j in range(delay + 1)]
        elif isinstance(i, Record):
            z = [Record(i.layout) for j in range(delay + 1)]
        else:
            z = [Signal.like(i) for j in range(delay + 1)]
        self.i = z[0]
        self.o = z[-1]
        if not isinstance(i, (int, list, tuple)):
            self.comb += self.i.eq(i)
        if o is not None:
            self.comb += o.eq(self.o)
        self.latency = delay
        self.sync += [z[j + 1].eq(z[j]) for j in range(delay)]
