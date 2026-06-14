from slowpy.control import control_system as ctrl
labjack = ctrl.import_control_module('LabJackU').labjack_U6()

import slowpy.store
store = slowpy.store.create_datastore_from_url('sqlite:///LabJack.db')

import time

def _loop():
    Tc = float(labjack.temperature().get()) - 273.15
    #print(f'DeviceTemperature: {Tc}')
    store.append(Tc, tag=f'degC.LabJack.Bakeout.CCA')
    
    for ch in range(14):
        mV = 1000 * float(labjack.ain(ch, gain=3))
        T = type_k_temperature_from_voltage(mV, Tc)
        #print(f'Ch{ch}: {mV} mV, {T} degC')
        store.append(mV, tag=f'mV.ThrmCpl{ch}.Bakeout.CCA')
        store.append(T, tag=f'degC.ThrmCpl{ch}.Bakeout.CCA')

    time.sleep(5)

    

def type_k_celsius_to_mv_0_500(t_c: float) -> float:
    """
    Type K thermocouple temperature [deg C] -> voltage [mV]
    referenced to 0 deg C.

    Valid for 0 to 500 deg C.
    """

    c = [
        0.000000000000e+00,
        0.394501280250e-01,
        0.236223735980e-04,
        -0.328589067840e-06,
        -0.499048287770e-08,
        -0.675090591730e-10,
        -0.574103274280e-12,
        -0.310888728940e-14,
        -0.104516093650e-16,
        -0.198892668780e-19,
        -0.163226974860e-22,
    ]

    e_mv = 0.0
    for a in reversed(c):
        e_mv = e_mv * t_c + a

    return e_mv


def type_k_mv_to_celsius_0_500(e_mv: float) -> float:
    """
    Type K thermocouple voltage [mV] -> temperature [deg C]
    referenced to 0 deg C.

    Valid for approximately 0 to 500 deg C,
    corresponding to 0 to 20.644 mV.
    """

    c = [
        0.000000e+00,
        2.508355e+01,
        7.860106e-02,
        -2.503131e-01,
        8.315270e-02,
        -1.228034e-02,
        9.804036e-04,
        -4.413030e-05,
        1.057734e-06,
        -1.052755e-08,
    ]

    t_c = 0.0
    for a in reversed(c):
        t_c = t_c * e_mv + a

    return t_c


def type_k_temperature_from_voltage(
    measured_mv: float,
    cold_c: float,
) -> float:
    """
    Type K thermocouple temperature with cold-junction compensation.

    Parameters
    ----------
    measured_mv:
        Measured thermocouple voltage in mV.
        This is the voltage between the hot junction and the cold junction.

    cold_c:
        Cold junction temperature in deg C.

    Returns
    -------
    hot_c:
        Estimated hot junction temperature in deg C.

    Assumptions
    -----------
    - Type K thermocouple
    - Hot junction temperature is in the range 0 to 500 deg C
    - Cold junction temperature is also roughly in the 0 to 500 deg C range,
      normally near room temperature
    """

    cold_mv = type_k_celsius_to_mv_0_500(cold_c)
    compensated_mv = measured_mv + cold_mv

    return type_k_mv_to_celsius_0_500(compensated_mv)


    
if __name__ == '__main__':
    while True:
        _loop()
        
