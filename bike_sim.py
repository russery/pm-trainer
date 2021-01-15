"""
Very basic bike simulator.
"""

class BikeSim():
    '''
    Very basic bike simulator, calculates speed and distance
    based on power input and a few rider parameters.
    '''
    def __init__(self, weight_kg=75):
        self._weight_kg = weight_kg
        self._last_update_time_s = None
        self._total_distance_m = 0.0
        self._speed_mps = 0.0

    def update(self, power_watts, time_s):
        '''
        Calculate speed and distance based on power

        Simulator based on https://www.omnicalculator.com/sports/cycling-wattage
        P = (Fg + Fr + Fa) * v / (1 - loss) -> v = P * (1-loss) / (Fg + Fr + Fa)
        Fg = longitudinal component of gravity
        Fr = rolling resistance
        Fa = aerodynamic drag
        v = speed in m/s
        loss = drivetrain losses
        '''

        # Calculate longitudinal component of gravity
        Fg_N = 0 # assumes we're on a flat course

        # Calculate rolling resistance
        G_mps2 = 9.80655 # Gravitational acceleration constant, assume we're on a flat surface
        CRR = 0.005 # Coefficient of rolling resistance, varies with tire type and surface
        Fr_N = G_mps2 * self._weight_kg * CRR

        # Calculate aerodynamic drag
        CDA_m2 = 0.324 # Coefficient of aerodynamic drag times frontal area
        RHO_kgpm3 = 1.225 # Air density, assumes sea level
        Fa_N = 0.5 * CDA_m2 * RHO_kgpm3 * pow(self._speed_mps, 2) # Use previous speed

        # Calculate rider pedalling force
        LOSS = 0.035 # powertrain losses
        if self._speed_mps < 0.5:
            # Avoid divide-by-zero, and make pedal force realistic
            # (hard to develop high wattage at low speed)
            pow_spd_mps = 0.5
        else:
            pow_spd_mps = self._speed_mps
        Fp_N = power_watts * (1-LOSS) / pow_spd_mps

        # Calculate time delta
        if self._last_update_time_s is None:
            self._last_update_time_s = time_s
        DeltaT_s = time_s - self._last_update_time_s

        # Calculate new speed
        A_mps2 = (Fp_N - (Fg_N + Fr_N + Fa_N)) / self._weight_kg
        self._speed_mps = self._speed_mps + A_mps2 * DeltaT_s

        # Update time and calculate distance travelled from avg. speed
        self._total_distance_m += self._speed_mps * DeltaT_s
        self._last_update_time_s = time_s

    @property
    def speed_mps(self):
        '''
        Speed in meters per second.
        '''
        return self._speed_mps

    @property
    def speed_miph(self):
        '''
        Speed in miles per hour.
        '''
        return self._speed_mps * 2.23694

    @property
    def total_distance_m(self):
        '''
        Total distance travelled in meters.
        '''
        return self._total_distance_m

    @property
    def total_distance_mi(self):
        '''
        Total distance travelled in miles.
        '''
        return self._total_distance_m / 1609

if __name__ == "__main__":
    # Basic test of hard-coded values
    sim = BikeSim(weight_kg=80)
    for i in range(1,100):
        sim.update(200, i)
    print('Steady-state speed for 200W: {:4.2f}mph'.format(sim.speed_miph))
    assert 20.5 <= sim.speed_miph <= 21.7
