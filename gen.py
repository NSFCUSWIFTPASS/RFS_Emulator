# (c) 2024 The Regents of the University of Colorado, a body corporate. Created by Oren Collaco.
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

import numpy as np
import time

class GaussianDataGenerator:
    def __init__(self, anchor, std_dev):
        self.original_anchor = anchor
        self.current_anchor = anchor
        self.std_dev = std_dev
        # Variables for managing temporary anchor changes.
        self.temp_anchor_start_time = None
        self.temp_anchor_duration = None

    def generate_data(self, size=1):
        """Generate data points around the current anchor with Gaussian distribution."""
        # Revert anchor back to original if temporary change duration has passed.
        if self.temp_anchor_start_time and (time.time() - self.temp_anchor_start_time) >= self.temp_anchor_duration:
            self.current_anchor = self.original_anchor
            self.temp_anchor_start_time = None
            self.temp_anchor_duration = None
        return np.random.normal(self.current_anchor, self.std_dev, size)

    def move_anchor_temporarily_rel(self, relative_change, duration):
        """Move anchor by a relative value temporarily."""
        self.current_anchor += relative_change
        self._start_temp_anchor(duration)

    def move_anchor_temporarily_abs(self, new_anchor, duration):
        """Move anchor to an absolute value temporarily."""
        self.current_anchor = new_anchor
        self._start_temp_anchor(duration)

    def _start_temp_anchor(self, duration):
        """Record start time and duration for a temporary anchor change."""
        self.temp_anchor_start_time = time.time()
        self.temp_anchor_duration = duration

# # Example usage:
# generator = GaussianDataGenerator(anchor=100, std_dev=15)
# # Move anchor relatively and generate data
# generator.move_anchor_temporarily_rel(20, 10)  # Move anchor for 10 seconds
# time.sleep(5)  # Wait to generate data during temporary state
# print("Data with relative change:", generator.generate_data(10))

# # Move anchor absolutely and generate data after original duration passes
# generator.move_anchor_temporarily_abs(150, 10)
# time.sleep(11)  # Wait longer than the temporary duration
# print("Data after revert to original:", generator.generate_data(10))
