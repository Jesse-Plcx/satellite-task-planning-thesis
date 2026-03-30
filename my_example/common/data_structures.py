"""Data structures for task planning"""
import numpy as np


class TargetData:
    """Data structure for ground target information"""
    def __init__(self, name, lat, lon, alt, priority):
        self.name = name
        self.lat = lat  # radians
        self.lon = lon  # radians
        self.alt = alt  # meters
        self.priority = priority  # 0-1, higher is more important
        self.imaged = False
        self.imaged_time = None
        self.imaged_by = None


class SatelliteResources:
    """Data structure for satellite resource tracking"""
    def __init__(self, sat_id, config=None):
        """
        Initialize satellite resources
        
        Args:
            sat_id: Satellite identifier
            config: Optional configuration dict with resource parameters
        """
        self.sat_id = sat_id
        self.storage_used = 0.0  # bits
        
        # Load from config or use defaults
        if config:
            self.storage_capacity = config.get('storage_capacity_mbits', 100.0) * 1e6  # Convert Mbits to bits
            self.image_size = config.get('image_size_mbits', 10.0) * 1e6  # Convert Mbits to bits
            self.slew_time = config.get('slew_time_sec', 30.0)  # seconds
            self.imaging_time = config.get('imaging_time_sec', 10.0)  # seconds
            self.max_roll_angle = np.radians(config.get('max_roll_angle_deg', 45.0))  # convert to radians
            self.sensor_fov = np.radians(config.get('sensor_fov_deg', 2.5))  # convert to radians
        else:
            # Default values
            self.storage_capacity = 100e6  # 100 Mbits
            self.image_size = 10e6  # 10 Mbits per image
            self.slew_time = 30.0  # seconds to slew between targets
            self.imaging_time = 10.0  # seconds to capture image
            self.max_roll_angle = np.radians(45.0)  # ±45° max roll angle for agile pointing
            self.sensor_fov = np.radians(2.5)  # 2.5° half-angle sensor field of view
        
        self.tasks_completed = []
        self.last_task = None
