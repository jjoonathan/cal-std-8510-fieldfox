import skrf
from skrf.media import DefinedGammaZ0
import numpy as np

def keysight_calkit_offset_line(freq, offset_delay, offset_loss, offset_z0, port_z0):
    if offset_delay or offset_loss:
        alpha_l = (offset_loss * offset_delay) / (2 * offset_z0)
        alpha_l *= np.sqrt(freq.f / 1e9)
        beta_l = 2 * np.pi * freq.f * offset_delay + alpha_l
        zc = offset_z0 + (1 - 1j) * (offset_loss / (4 * np.pi * freq.f)) * np.sqrt(freq.f / 1e9)
        gamma_l = alpha_l + beta_l * 1j

        medium = DefinedGammaZ0(frequency=freq, z0_port=offset_z0, z0=zc, gamma=gamma_l)
        offset_line = medium.line(d=1, unit='m')
        return medium, offset_line
    else:
        medium = DefinedGammaZ0(frequency=freq, z0=offset_z0)
        line = medium.line(d=0)
        return medium, line


def keysight_calkit_open(freq, offset_delay, offset_loss, c0, c1, c2, c3, offset_z0=50, port_z0=50):
    medium, line = keysight_calkit_offset_line(freq, offset_delay, offset_loss, offset_z0, port_z0)
    # Capacitance is defined with respect to the port impedance offset_z0, not the lossy
    # line impedance. In scikit-rf, the return values of `shunt_capacitor()` and `medium.open()`
    # methods are (correctly) referenced to the port impedance.
    if c0 or c1 or c2 or c3:
        poly = np.poly1d([c3, c2, c1, c0])
        capacitance = medium.shunt_capacitor(poly(freq.f)) ** medium.open()
    else:
        capacitance = medium.open()
    return line ** capacitance


def keysight_calkit_short(freq, offset_delay, offset_loss, l0, l1, l2, l3, offset_z0=50, port_z0=50):
    # Inductance is defined with respect to the port impedance offset_z0, not the lossy
    # line impedance. In scikit-rf, the return values of `inductor()` and `medium.short()`
    # methods are (correctly) referenced to the port impedance.
    medium, line = keysight_calkit_offset_line(freq, offset_delay, offset_loss, offset_z0, port_z0)
    if l0 or l1 or l2 or l3:
        poly = np.poly1d([l3, l2, l1, l0])
        inductance = medium.inductor(poly(freq.f)) ** medium.short()
    else:
        inductance = medium.short()
    return line ** inductance


def keysight_calkit_load(freq, offset_delay=0, offset_loss=0, offset_z0=50, port_z0=50):
    medium, line = keysight_calkit_offset_line(freq, offset_delay, offset_loss, offset_z0, port_z0)
    load = medium.match()
    return line ** load


def keysight_calkit_thru(freq, offset_delay=0, offset_loss=0, offset_z0=50, port_z0=50):
    medium, line = keysight_calkit_offset_line(freq, offset_delay, offset_loss, offset_z0, port_z0)
    thru = medium.thru()
    return line ** thru

class Keysight85056D():
    def __init__(self, freqs):
        self.m_short = keysight_calkit_short(freqs, l0=2.1636e-12, l1=-146.35e-24, l2=4.0443e-33,  l3=-.0363e-42, offset_delay=22.548e-12, offset_loss=3.554e9)
        self.f_short = keysight_calkit_short(freqs, l0=2.1636e-12, l1=-146.35e-24, l2=4.0443e-33,  l3=-.0363e-42, offset_delay=22.548e-12, offset_loss=3.554e9)
        self.m_open  = keysight_calkit_open(freqs,  c0=29.722e-15, c1=165.78e-27,  c2=-3.5386e-36, c3=.071e-45  , offset_delay=20.837e-12, offset_loss=3.23e9)
        self.f_open  = keysight_calkit_open(freqs,  c0=29.72e-15 , c1=165.78e-27,  c2=-3.5385e-36, c3=.071e-45  , offset_delay=20.837e-12, offset_loss=3.23e9)
        self.m_load  = keysight_calkit_load(freqs)
        self.f_load  = keysight_calkit_load(freqs)
        self.thru    = keysight_calkit_thru(freqs)

    def apply_cal(self, net):
        return self.cal.apply_cal(net)
    
    @classmethod
    def one_port_m(cls, measured_f_short, measured_f_open, measured_f_load):
        assert measured_f_open.frequency == measured_f_short.frequency
        assert measured_f_short.frequency == measured_f_load.frequency
        self = cls(measured_f_open.frequency)
        self.cal = skrf.OnePort(
            ideals = [self.f_short, self.f_open, self.f_load],
            measured = [measured_f_short, measured_f_open, measured_f_load]
        )
        self.cal.run()
        return self   

    @classmethod
    def one_port_f(cls, measured_m_short, measured_m_open, measured_m_load):
        assert measured_m_open.frequency == measured_m_short.frequency
        assert measured_m_short.frequency == measured_m_load.frequency
        self = cls(measured_m_open.frequency)
        self.cal = skrf.OnePort(
            ideals = [self.m_short, self.m_open, self.m_load],
            measured = [measured_m_short, measured_m_open, measured_m_load]
        )
        self.cal.run()
        return self  


class Keysight85058BP():
    def __init__(self, freqs):
        self.m_short1_bb = keysight_calkit_short(freqs, l0=0.9658e-12,  l1=8.9552e-24,  l2=-0.7884,     l3=0.0079e-42 ,  offset_delay=18.012e-12, offset_loss=4.0608e9)
        self.m_short1_lb = keysight_calkit_short(freqs, l0=-0.0845e-12, l1=163.6838e-24,l2=-7.0736e-33, l3=0.0811e-42 ,  offset_delay=17.998e-12, offset_loss=4.1099e9)
        self.m_short1_hb = keysight_calkit_short(freqs, l0=-26.329-12,  l1=1436.9e-24,  l2=-24.863e-33, l3=0.1393e-42,   offset_delay=18.012e-12, offset_loss=4.0087e9)
        self.m_short2    = keysight_calkit_short(freqs, l0=5.2837e-12,  l1=-255.25e-24, l2=4.4398e-33,  l3=-0.0248e-42,  offset_delay=21.015e-12, offset_loss=3.9424e9)
        self.m_short3    = keysight_calkit_short(freqs, l0=-18.399e-12, l1=854.22e-24,  l2=-12.502e-33, l3=0.0595e-42,   offset_delay=23.750e-12, offset_loss=3.9568e9)
        self.m_short4    = keysight_calkit_short(freqs, l0=31.176e-12,  l1=-1738.2e-24, l2=32.421e-33,  l3=-0.1988e-42,  offset_delay=25.351e-12, offset_loss=3.8911e9)

        self.f_short1_bb = keysight_calkit_short(freqs, l0=1.4957e-12,  l1=-323.18e-24, l2=11.624e-33,  l3=-0.10939e-42 , offset_delay=18.012e-12, offset_loss=4.0812e9)
        self.f_short1_lb = keysight_calkit_short(freqs, l0=1.8222e-12,  l1=-934.86e-24, l2=64.091e-33,  l3=-1.1161e-42 ,  offset_delay=18.012e-12, offset_loss=3.9664e9)
        self.f_short1_hb = keysight_calkit_short(freqs, l0=81.443e-12,  l1=-5397.5e-24, l2=114.29e-33,  l3=-0.77746e-42,  offset_delay=18.012e-12, offset_loss=4.0306e9)
        self.f_short2    = keysight_calkit_short(freqs, l0=-168.11e-12, l1=10025e-24,   l2=-195.63e-33, l3=1.2447e-42,    offset_delay=21.015e-12, offset_loss=3.9661e9)
        self.f_short3    = keysight_calkit_short(freqs, l0=-85.542e-12, l1=5237.9e-24,  l2=-105.29e-33, l3=0.68943e-42,   offset_delay=23.750e-12, offset_loss=3.9432e9)
        self.f_short4    = keysight_calkit_short(freqs, l0=83.336e-12,  l1=-4925.8e-24, l2=95.83e-33,   l3=-0.61258e-42,  offset_delay=25.351e-12, offset_loss=3.8798e9)
        
        self.m_open_bb  = keysight_calkit_open(freqs,  c0=2.2757e-15,   c1=0.60959e-27, c2=-3.9739e-36, c3=0.05204e-45,   offset_delay=18.011e-12, offset_loss=3.2815e9)
        self.m_open_lb  = keysight_calkit_open(freqs,  c0=2.127e-15,    c1=73.815e-27,  c2=-9.1135e-36, c3=0.13886e-45,   offset_delay=18.011e-12, offset_loss=3.2762e9)

        self.f_open_bb  = keysight_calkit_open(freqs,  c0=-3.5342e-15,  c1=425.24e-27,  c2=-13.946e-36, c3=0.12741e-45,   offset_delay=18.001e-12, offset_loss=3.2822e9)
        self.f_open_lb  = keysight_calkit_open(freqs,  c0=-7.7748e-15,  c1=1332.4e-27,  c2=-64.26e-36,  c3=0.90991e-45,   offset_delay=18.015e-12, offset_loss=3.2754e9)

        self.m_load  = keysight_calkit_load(freqs)
        
        self.f_load  = keysight_calkit_load(freqs)

    def apply_cal(self, net):
        return self.cal.apply_cal(net)

    @classmethod
    def one_port_m(cls, measured_f_short1, measured_f_open, measured_f_load, use_coarse_definition=True):
        assert measured_f_open.frequency == measured_f_short1.frequency
        assert measured_f_short1.frequency == measured_f_load.frequency
        self = cls(measured_f_open.frequency)
        if use_coarse_definition:
            self.cal = skrf.OnePort(
                ideals = [self.f_short1_bb, self.f_open_bb, self.f_load],
                measured = [measured_f_short1, measured_f_open, measured_f_load]
            )
            self.cal.run()
            return self
        self.cal_lb = skrf.OnePort(
            ideals = [self.f_short1_lb, self.f_open_bb, self.f_load],
            measured = [measured_f_short1, measured_f_open, measured_f_load]
        )

    @classmethod
    def one_port_f(cls, measured_m_short1, measured_m_open, measured_m_load, use_coarse_definition=True):
        assert measured_m_open.frequency == measured_m_short1.frequency
        assert measured_m_short1.frequency == measured_m_load.frequency
        self = cls(measured_m_open.frequency)
        if use_coarse_definition:
            self.cal = skrf.OnePort(
                ideals = [self.m_short1_bb, self.m_open_bb, self.m_load],
                measured = [measured_m_short1, measured_m_open, measured_m_load]
            )
            self.cal.run()
            return self  
