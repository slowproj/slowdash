# Created by Sanshiro Enomoto on 5 June 2023 #

import time, random, math

def normal(mean, sigma):
    u1 = random.random()
    u2 = random.random()
    r = math.sqrt(-2.0*math.log(u1)) * math.cos(2.0 * math.pi * u2)
    
    return mean + r * sigma


def poisson(mean):
    sum = 0
    counts = -1
    
    while sum < mean:
        counts += 1
        step = random.random()
        if step == 0:
            break
        sum += -math.log(step)

    return counts


def exponential(scale=1.0):
    y = random.random()
    while y == 0:
        y = random.random()
        
    return -math.log(y) * scale




class RandomWalkDevice:
    def __init__(self, n=16, walk=1.0, decay=0.1, initial=0, tick=1.0):
        self.n = n
        self.walk = walk
        self.decay = decay
        self.tick = tick

        self.t = [time.time()] * n
        self.x0 = [initial] * n
        self.x = [initial] * n
        for ch in range(self.n):
            self.x[ch] = normal(self.x0[ch], 3*self.walk)


    def channels(self):
        return range(self.n)
            
        
    def write(self, channel, value):
        if channel < 0 or channel >= len(self.x0):
            return None
        
        self.x0[channel] = float(value)
        self.x[channel] = normal(self.x0[channel], self.walk)

        
    def read(self, channel):
        if channel >= len(self.x):
            return None
        
        now = time.time()
        if self.tick > 0:
            steps = int((now - self.t[channel]) / self.tick)
            self.t[channel] = self.t[channel] + self.tick * steps
        else:
            steps = 1
            self.t[channel] = now
            
        for k in range(steps):
            self.x[channel] -= self.decay * (self.x[channel] - self.x0[channel]) + normal(0, self.walk)
        
        return round(self.x[channel], 3)



class RandomHitDevice:
    def __init__(self, n=16, occupancy=0.7):
        self.n = n
        self.occupancy = occupancy


    def channels(self):
        return range(self.n)
            
        
    def read(self, channel):
        return random.random() < self.occupancy


    
class RandomChargeDevice:
    def __init__(self, n=16, mean=10, sigma=2):
        self.n = n
        self.mean = mean
        self.sigma = sigma


    def channels(self):
        return range(self.n)
            
        
    def read(self, channel):
        if channel >= self.n:
            return None

        x = poisson(self.mean) + normal(0, self.sigma)
        
        return int(x) if x > 0 else 0



class RandomTimeDevice:
    def __init__(self, n=16, time_constant=0.1):
        self.n = n
        self.time_constant = time_constant


    def channels(self):
        return range(self.n)
            
        
    def read(self, channel):
        if channel >= self.n:
            return None

        return exponential(self.time_constant)



class FirstOrderPlant:
    """First-order system:
        dy/dt = (gain * u - y) / tau
    """

    def __init__(self, gain=1.0, tau=10, initial_value=0.0, noise=0):
        self.gain = float(gain)
        self.tau = float(tau)
        self.noise = noise

        self._u = 0.0
        self._y = float(initial_value)
        self._time = time.monotonic()


    @property
    def control_input(self):
        return self._u
        
    @control_input.setter
    def control_input(self, value):
        self._u = value

        
    @property
    def state(self):
        return self._y
        
    @state.setter
    def state(self, value):
        self._y = value
        
        
    def update(self):
        now = time.monotonic()
        dt = now - self._time
        if dt > 0:
            # Exact solution while u is constant:
            #   y(t+dt) = gain*u + (y(t) - gain*u) exp(-dt/tau)
            y_inf = self.gain * self._u
            self._y = y_inf + (self._y - y_inf) * math.exp(-dt / self.tau)
            self._time = now
            
            self._y += normal(0, self.noise)  # this should be scaled with the time step
            


class SecondOrderPlant:
    """Second-order system, aka Damped oscillator
    d2y/dt2 + 2*zeta*omega*dy/dt + omega^2*y = gain*omega^2*u
    """

    def __init__(self, gain=1.0, omega=0.2, zeta=0.5, initial_value=0.0, initial_velocity=0.0, noise=0):
        self.gain = float(gain)
        self.omega = float(omega)
        self.zeta = float(zeta)
        self.noise = noise

        self._u = 0.0
        self._y = float(initial_value)
        self._v = float(initial_velocity)
        self._time = time.monotonic()


    @property
    def control_input(self):
        return self._u
        
    @control_input.setter
    def control_input(self, value):
        self._u = value

        
    @property
    def state(self):
        return self._y
        
    @state.setter
    def state(self, value):
        self._y = value
        
        
    def update(self):
        now = time.monotonic()
        dt = now - self._time
        if dt <= 0:
            return

        omega = self.omega
        zeta = self.zeta

        # Shift the equilibrium:
        #   x = y - gain*u
        # then
        #   x'' + 2*zeta*omega*x' + omega^2*x = 0
        x = self._y - self.gain * self._u
        v = self._v

        if zeta < 1.0: # Underdamped
            a = zeta * omega
            wd = omega * math.sqrt(1.0 - zeta*zeta)
            e = math.exp(-a * dt)
            c = math.cos(wd * dt)
            s = math.sin(wd * dt)
            B = (v + a*x) / wd
            x_new = e * (x*c + B*s)
            v_new = e * (v*c + (-a*B - wd*x)*s)
        elif zeta == 1.0: # Critically damped
            e = math.exp(-omega * dt)
            B = v + omega*x
            x_new = e * (x + B*dt)
            v_new = e * (v - omega*B*dt)
        else: # Overdamped
            q = omega * math.sqrt(zeta*zeta - 1.0)
            r1 = -zeta*omega + q
            r2 = -zeta*omega - q
            c1 = (v - r2*x) / (r1 - r2)
            c2 = (r1*x - v) / (r1 - r2)
            e1 = math.exp(r1 * dt)
            e2 = math.exp(r2 * dt)
            x_new = c1*e1 + c2*e2
            v_new = r1*c1*e1 + r2*c2*e2

        self._y = self.gain * self._u + x_new
        self._v = v_new
        self._time = now

        self._y += normal(0, self.noise)  # this should be scaled with the time step

        
