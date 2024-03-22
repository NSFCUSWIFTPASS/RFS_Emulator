# (c) 2024 The Regents of the University of Colorado, a body corporate. Created by Oren Collaco.
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

# Generates RF statistics based on existing schema deployed on HCRO Node1
# Supports RFI generation for testing systems ahead in the chain

# Usage: python3 rf_stats_gen.py --noise_floor 100 --hardware_id 1 --metadata_id 1 --noise_duration 30 --rfi_duration 15 --rfi_shift 20 --write_interval 5

import numpy as np
import time
import scipy.stats
from configparser import ConfigParser
import psycopg2
import argparse
from gen import GaussianDataGenerator
from datetime import datetime, timezone, timedelta
import requests
import base64

class Database:
    def __init__(self, direct=True, config_filename='db_config.ini', config_section='postgresql'):
        self.connection = None
        if(not direct):
            self.connect(config_filename, config_section)

    def connect(self, filename, section):
        parser = ConfigParser()
        parser.read(filename)
        if parser.has_section(section):
            params = dict(parser.items(section))
            self.connection = psycopg2.connect(**params)
            self.connection.autocommit = True
            print("Database connection established.")
        else:
            raise Exception(f'Section {section} not found in the {filename} file')

    def insert_data(self, hardware_id, metadata_id, created_at, average_db, max_db, median_db, std_dev, kurtosis):
        query = """INSERT INTO outputs(hardware_id, metadata_id, created_at, average_db, max_db, median_db, std_dev, kurtosis)
                   VALUES(%s, %s, %s, %s, %s, %s, %s, %s);"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (hardware_id, metadata_id, created_at, average_db, max_db, median_db, std_dev, kurtosis))
            #print("Data inserted successfully")
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error while inserting data:", error)
        finally:
            if cursor is not None:
                cursor.close()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            print("Database connection closed.")

class StatsGenerator:
    def __init__(self, noise, generator, hardware_id, metadata_id, db, noise_duration, rfi_duration, rfi_shift, direct=False, api_token=None, dst_http=None, monitor_id=None):
        self.generator = generator
        self.hardware_id = hardware_id
        self.metadata_id = metadata_id
        self.db = db
        self.noise = noise
        self.noise_duration = noise_duration
        self.rfi_duration = rfi_duration
        self.rfi_shift = rfi_shift
        self.direct = direct
        self.api_token = api_token
        self.dst_http = dst_http
        self.monitor_id = monitor_id
        self.data_history = []  # Initialize an empty list to store data history
        self.should_stop = False

    def encode_data(self, data):
        return base64.b64encode(data.encode()).decode('utf-8')

    def format_data_as_csv(self, created_at, average_db, max_db, median_db, std_dev, kurtosis):
        """
        Format the generated data into a CSV string.

        Returns:
            str: A CSV-formatted string of data.
        """
        
        frequency = 915000000
        power = average_db
        center_freq = frequency
        bandwidth = 1000000
        gain = 35
        length = 1.0
        interval = 10
        if(kurtosis > 4):
            violation = 1
        else:
            violation = 0
        
        abovefloor = - 60 - average_db

        # Format the CSV string
        csv_data = (f"frequency,power,center_freq,max_db,median_db,std_dev,kurtosis,"
                    f"bandwidth,gain,length,interval,created_at,violation,abovefloor\n"
                    f"{frequency},{power:.3f},{center_freq},{max_db:.3f},{median_db:.3f},{std_dev:.3f},"
                    f"{kurtosis:.3f},{bandwidth},{gain},{length},{interval},"
                    f"{created_at},{violation},{abovefloor}\n")
        
        print(csv_data)
        return csv_data

    def send_data(self, encoded_data):
        now = datetime.utcnow()
        starts_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        ends_at = (now + timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        headers = {
            "X-Api-Token": self.api_token,
            "Content-Type": "application/json"
        }
        payload = {
            "monitor_id": self.monitor_id,
            "types": "inline,sweep",
            "format": "rfs-csv-inline",
            "starts_at": starts_at,
            "ends_at": ends_at,
            "description": "inline violation",
            "data": encoded_data,
        }
        try:
            response = requests.post(f"{self.dst_http}/observations", json=payload, headers=headers)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def write_data_periodically(self, interval):
        start_time = time.time()
        last_rfi_time = start_time  # Initialize with start time to trigger RFI immediately
        in_rfi_mode = False  # Track whether we are currently in RFI mode

        while not self.should_stop:
            current_time = time.time()
            elapsed_since_last_rfi = current_time - last_rfi_time

            if elapsed_since_last_rfi >= self.noise_duration and not in_rfi_mode:
                self.generator.move_anchor_temporarily_rel(self.rfi_shift, self.rfi_duration)
                print(f"Switching to RFI generation: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
                in_rfi_mode = True
                last_rfi_time = current_time
            elif elapsed_since_last_rfi >= self.rfi_duration and in_rfi_mode:
                print(f"Switching back to noise floor: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
                in_rfi_mode = False
                last_rfi_time = current_time

            data = self.generator.generate_data(10)
            self.data_history.append(data)  # Append the generated data to the history list

            # Ensure data_history does not exceed 20 generations
            if len(self.data_history) > 20:
                self.data_history.pop(0)  # Remove the oldest generation

            # Flatten the list of lists to get a combined array of all data points
            combined_data = np.concatenate(self.data_history)

            average_db = np.mean(data)
            max_db = np.max(data)
            median_db = np.median(data)
            std_dev = np.std(data)
            fake_kurtosis = ((np.mean(data) - self.noise) + 2) * 0.6  # Fake kurtosis calculation
            fake_kurtosis = 0 if fake_kurtosis < 0 else fake_kurtosis  # Ensure kurtosis is not negative
            kurtosis = fake_kurtosis
            created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + '+00:00'

            if self.direct:
                csv_data = self.format_data_as_csv(created_at, average_db, max_db, median_db, std_dev, kurtosis)
                encoded_data = self.encode_data(csv_data)
                self.send_data(encoded_data)
            else:
                print(f"Inserting: Hardware ID: {self.hardware_id}, Metadata ID: {self.metadata_id}, "
                    f"Created At: {created_at}, Average DB: {average_db:.2f}, Max DB: {max_db:.2f}, "
                    f"Median DB: {median_db:.2f}, Std Dev: {std_dev:.4f}, Kurtosis: {kurtosis:.2f}")

                self.db.insert_data(self.hardware_id, self.metadata_id, created_at, average_db, max_db, median_db, std_dev, kurtosis)
            time.sleep(interval)

    def stop(self):
        self.should_stop = True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stats Generator with RFI Simulation')
    parser.add_argument('--noise_floor', type=int, required=True, help='Noise floor value to be used in the database')
    parser.add_argument('--hardware_id', type=int, required=True, help='Hardware ID to be used in the database')
    parser.add_argument('--metadata_id', type=int, required=True, help='Metadata ID to be used in the database')
    parser.add_argument('--noise_duration', type=int, required=True, help='Duration (seconds) for noise floor data generation')
    parser.add_argument('--rfi_duration', type=int, required=True, help='Duration (seconds) for RFI data generation')
    parser.add_argument('--rfi_shift', type=float, required=True, help='Value to shift the anchor by during RFI generation')
    parser.add_argument('--write_interval', type=float, required=True, help='Interval (seconds) between data writes to the database')
    parser.add_argument('--direct', action='store_true', help='Send data directly to OpenZMS if specified')
    parser.add_argument('--api_token', type=str, help='API Token for OpenZMS')
    parser.add_argument('--dst_http', type=str, help='Destination HTTP path for OpenZMS')
    parser.add_argument('--monitor_id', type=str, help='Monitor ID for OpenZMS')
    args = parser.parse_args()
    db = Database(direct=args.direct)
    generator = GaussianDataGenerator(anchor=args.noise_floor, std_dev=2)
    stats_generator = StatsGenerator(args.noise_floor, generator, args.hardware_id, args.metadata_id, db,
                                     args.noise_duration, args.rfi_duration, args.rfi_shift,
                                     direct=args.direct, api_token=args.api_token, dst_http=args.dst_http, monitor_id=args.monitor_id)
    try:
        stats_generator.write_data_periodically(args.write_interval)  # Use the provided interval for data writes
    except KeyboardInterrupt:
        print("Stopping data generation...")
    finally:
        stats_generator.stop()
        db.close()