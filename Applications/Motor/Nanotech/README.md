# Nanotech C5E Motor Controller

## Device Setup
Connect the device via USB.

### Firmware Version
See `info.bin` file. The version name is in the form of `FIR-vxxxx-Rxxxx`.


### Configuration
Edit the `cfg.txt` file.

#### For open-loop mode
```
2030:00=50      ; pole-pair count, 50 is for 1.8 deg
2031:00=1800    ; max motor current in mA; 5.5 A per motor spec
6075:00=1800    ; motor rated current

3202:00=0x0008  ; open loop (bit 0, 0:open-loop; 1:closed-loop), current reduction (bit 3)
```

#### For closed-loop mode with an encoder
```
2030:00=50      ; pole-pair count, 50 is for 1.8 deg
2031:00=1800    ; max motor current in mA; 5.5 A per motor spec
6075:00=1800    ; motor rated current

3202:00=0x0001    ; closed loop (bit 0, 0:open-loop; 1:closed-loop)
2059:00=0x0000    ; encoder configuration (bit 1, 0:differential, 1:single-ended)
```

After editing the `CFG.txt` file, power-cycle the device.

### Running Auto Setup
```
cd PATH/TO/THIS/APP/utils
slowdash-activate-venv
python run_auto_setup.py
```

Then power-cycle the device again.


### SlowDash Project Setup
Edit `SlowdashProject.yaml` for the IP address and firmware version.
```yaml
slowdash_project:
  name: Nanotech_Motor

  environment:
    - DB_URL=${DB_URL:-sqlite:///SlowMotor}

  data_source:
    url: ${DB_URL}
    time_series:
      schema: data [channel] @timestamp(unix) = value

  task:
    name: NanotechMotor
    auto_load: true
    parameters:
      IP: "192.168.50.176"  # or use MAC: "44:aa:e8:00:1f:f4"
      db_url: ${DB_URL}
      firmware_version: 2213
```

The firmware version is important as the register mapping was changed after FIR-v2039.
