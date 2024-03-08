import subprocess
import threading

# metadata_id values for Hardware ID 1
metadata_ids = [
    47, 48, 49, 50, 55, 56, 77, 78, 79, 80,
    1, 2, 5, 6, 17, 18, 19, 20, 25, 26
]

# Base command without metadata_id
base_command = [
    "python3", "rf_stats_gen.py",
    "--noise_floor", "-115",
    "--hardware_id", "1",
    "--noise_duration", "25",
    "--rfi_duration", "12",
    "--rfi_shift", "20",
    "--write_interval", "5"
]

def run_command(meta_id):
    # Create a copy of the base command for safe modification
    command = base_command.copy()

    # Append the metadata_id argument
    command.extend(["--metadata_id", str(meta_id)])

    # Execute the command
    subprocess.run(command)

    print(f"Command for metadata_id {meta_id} executed.")

# Create and start a thread for each metadata_id
threads = []
for meta_id in metadata_ids:
    thread = threading.Thread(target=run_command, args=(meta_id,))
    thread.start()
    threads.append(thread)

# Wait for all threads to complete
for thread in threads:
    thread.join()

print("All commands executed.")
