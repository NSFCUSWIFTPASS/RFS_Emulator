# RFS Stats Emulator

Generates RF statistics based on existing schema deployed on HCRO Node1
Supports RFI generation for testing systems ahead in the chain

## Installation

1. Clone this repository or download the source code to your local machine.
2. Install the required Python packages using pip:

```bash
pip install numpy requests
pip install -r requirements
```
3. Set the connection configuration in db_config.ini

## Usage

```bash
python3 rf_stats_gen.py --noise_floor 100 --hardware_id 1 --metadata_id 1 --noise_duration 30 --rfi_duration 15 --rfi_shift 20 --write_interval 5
```

- `--noise_floor`: The noise floor of the output data
- `--hardware_id`: Hardware ID used when inserting in the database
- `--metadata_id`: Metadata ID used when inserting in the database
- `--noise_duration`: Duration for which stats generated are at noise floor
- `--rfi_duration`: Duration for which stats generated are at RFI level
- `--rfi_shift`: Amount in dBm by which stats move up
- `--write_interval`: Interval between two stats generations


Use start_sensor.py to start multiple instances of rf_stats_gen.py based on the number of metadata IDs required. Each metadata ID is put in an array inside start_sensor.py

```bash
python3 start_sensor.py
```



