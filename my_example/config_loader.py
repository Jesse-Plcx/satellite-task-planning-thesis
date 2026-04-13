"""
Configuration file loader for experiment parameters
Supports YAML format with defaults and validation
"""
import yaml
import os
from typing import Dict, Any


class ConfigLoader:
    """Load and validate experiment configuration"""
    
    DEFAULT_CONFIG = {
        'simulation': {
            'satellites': 6,
            'targets': 150,
            'target_mode': 'random',
            'duration': 86400.0,
            'seed': None,
            'vizard': False
        },
        'constellation': {
            'num_planes': 3,
            'altitude_km': 550.0,
            'inclination_deg': 53.0
        },
        'satellite_resources': {
            'storage_capacity_mbits': 100.0,
            'image_size_mbits': 10.0,
            'slew_time_sec': 30.0,
            'imaging_time_sec': 10.0,
            'max_roll_angle_deg': 45.0,
            'sensor_fov_deg': 2.5,
            'priority_min': 0.1,           # lower bound for uniform mode
            'priority_max': 1.0,           # upper bound for uniform mode
        },
        'algorithms': {
            'run': 'both',
            'random': {
                'enabled': True
            },
            'ewf': {
                'enabled': True
            },
            'greedy': {
                'enabled': True
            },
            'sa': {
                'enabled': True,
                'initial_temperature': None,
                'final_temperature': 0.05,
                'cooling_rate': 0.97,
                'iterations_per_temp': 40
            },
            'genetic': {
                'enabled': True,
                'population_size': 120,
                'num_generations': 200,
                'mutation_rate': 0.15
            }
        },
        'output': {
            'save_plots': True,
            'plot_format': 'png',
            'results_dir': 'res/runs/default'
        }
    }
    
    @staticmethod
    def load_config(config_path: str = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        When config_path is None, automatically loads configs/default.yaml
        (relative to this file's directory) so that running without --config
        gives identical results to --config configs/default.yaml.
        The hardcoded DEFAULT_CONFIG is used only if that file is missing.

        Args:
            config_path: Path to YAML config file. If None, load configs/default.yaml
            
        Returns:
            Configuration dictionary
        """
        config = ConfigLoader.DEFAULT_CONFIG.copy()

        # When no path given, try configs/default.yaml next to this file
        if config_path is None:
            _here = os.path.dirname(os.path.abspath(__file__))
            _fallback = os.path.join(_here, 'configs', 'default.yaml')
            if os.path.exists(_fallback):
                config_path = _fallback

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    config = ConfigLoader._merge_configs(config, user_config)
            print(f"✓ Loaded configuration from: {config_path}")
        else:
            if config_path:
                print(f"⚠ Config file not found: {config_path}, using defaults")
            else:
                print("✓ Using hardcoded default configuration")
        
        # Validate configuration
        ConfigLoader._validate_config(config)
        
        return config
    
    @staticmethod
    def _merge_configs(base: Dict, override: Dict) -> Dict:
        """Recursively merge override config into base config"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def _validate_config(config: Dict):
        """Validate configuration parameters"""
        sim = config.get('simulation', {})
        
        # Validate simulation parameters
        if sim.get('satellites', 1) < 1:
            raise ValueError("Number of satellites must be at least 1")
        if sim.get('targets', 1) < 1:
            raise ValueError("Number of targets must be at least 1")
        if sim.get('duration', 0) <= 0:
            raise ValueError("Simulation duration must be positive")
        if sim.get('target_mode') not in ['random', 'cities', 'grid']:
            raise ValueError("target_mode must be 'random', 'cities', or 'grid'")
        
        # Validate constellation parameters
        const = config.get('constellation', {})
        if const.get('num_planes', 1) < 1:
            raise ValueError("Number of planes must be at least 1")
        if const.get('altitude_km', 0) <= 0:
            raise ValueError("Altitude must be positive")
        if not -90 <= const.get('inclination_deg', 0) <= 90:
            raise ValueError("Inclination must be between -90 and 90 degrees")
        
        # Validate satellite resources
        sat_res = config.get('satellite_resources', {})
        if sat_res.get('storage_capacity_mbits', 0) <= 0:
            raise ValueError("Storage capacity must be positive")
        if sat_res.get('image_size_mbits', 0) <= 0:
            raise ValueError("Image size must be positive")
        if sat_res.get('slew_time_sec', 0) < 0:
            raise ValueError("Slew time must be non-negative")
        if sat_res.get('imaging_time_sec', 0) <= 0:
            raise ValueError("Imaging time must be positive")
        if not 0 <= sat_res.get('max_roll_angle_deg', 0) <= 90:
            raise ValueError("Max roll angle must be between 0 and 90 degrees")
        if not 0 < sat_res.get('sensor_fov_deg', 0) <= 90:
            raise ValueError("Sensor FOV must be between 0 and 90 degrees")
        
        # Validate algorithm parameters
        algo = config.get('algorithms', {})
        if algo.get('run') not in ['random', 'ewf', 'greedy', 'sa', 'genetic', 'both', 'all', 'all_no_ga']:
            raise ValueError("algorithms.run must be 'random', 'ewf', 'greedy', 'sa', 'genetic', 'both', 'all', or 'all_no_ga'")

        sa = algo.get('sa', {})
        if sa.get('final_temperature', 0) <= 0:
            raise ValueError("SA final_temperature must be positive")
        if sa.get('initial_temperature') is not None:
            if sa.get('initial_temperature', 0) <= 0:
                raise ValueError("SA initial_temperature must be positive when specified")
            if sa.get('final_temperature', 0) >= sa.get('initial_temperature', 1):
                raise ValueError("SA final_temperature must be smaller than initial_temperature")
        if not 0 < sa.get('cooling_rate', 0.97) < 1:
            raise ValueError("SA cooling_rate must be between 0 and 1")
        if sa.get('iterations_per_temp', 1) < 1:
            raise ValueError("SA iterations_per_temp must be at least 1")
        
        genetic = algo.get('genetic', {})
        if genetic.get('population_size', 1) < 1:
            raise ValueError("Population size must be at least 1")
        if genetic.get('num_generations', 1) < 1:
            raise ValueError("Number of generations must be at least 1")
        if not 0 <= genetic.get('mutation_rate', 0.1) <= 1:
            raise ValueError("Mutation rate must be between 0 and 1")
    
    @staticmethod
    def save_config(config: Dict, config_path: str):
        """Save configuration to YAML file"""
        os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"✓ Configuration saved to: {config_path}")
    
    @staticmethod
    def print_config(config: Dict):
        """Pretty print configuration"""
        return


