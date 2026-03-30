"""Walker constellation and target generation utilities"""
import numpy as np
import math


def calculate_repeat_cycle(altitude_km, inclination_deg=53.0):
    """
    Calculate satellite repeat cycle (nodal period) for ground track repetition.
    
    This function computes how many days it takes for a satellite to repeat its
    ground track, which is essential for systematic Earth observation missions.
    
    Args:
        altitude_km (float): Orbital altitude in km
        inclination_deg (float): Orbital inclination in degrees (default: 53.0)
    
    Returns:
        tuple: (repeat_days, num_revs, duration_seconds)
            - repeat_days: Number of days for ground track repeat
            - num_revs: Number of satellite revolutions in one repeat cycle
            - duration_seconds: Duration of one repeat cycle in seconds
    
    Physics:
        Due to Earth's J2 oblateness perturbation, the satellite's ascending node
        precesses. The repeat cycle occurs when:
            N_revs * T_orbit = D_days * T_sidereal
        where N_revs and D_days are integers (coprime for minimal repeat).
    """
    # Constants
    R_EARTH = 6371.0  # km, Earth mean radius
    MU_EARTH = 398600.4418  # km³/s², Earth gravitational parameter
    J2 = 1.08263e-3  # Earth's J2 coefficient
    OMEGA_EARTH = 7.2921159e-5  # rad/s, Earth rotation rate
    T_SIDEREAL_DAY = 86164.0905  # seconds, sidereal day
    
    # Orbital parameters
    a = R_EARTH + altitude_km  # semi-major axis in km
    i_rad = math.radians(inclination_deg)
    n = math.sqrt(MU_EARTH / (a**3))  # mean motion (rad/s)
    T_orbit = 2 * math.pi / n  # orbital period (seconds)
    
    # J2-induced nodal precession rate (rad/s)
    # Ω_dot = -1.5 * n * J2 * (R_EARTH/a)² * cos(i)
    nodal_precession_rate = -1.5 * n * J2 * (R_EARTH / a)**2 * math.cos(i_rad)
    
    # Find integer ratio N_revs / D_days for ground track repeat
    # Search for the smallest integers that satisfy:
    # N_revs / D_days ≈ T_sidereal / T_orbit
    revs_per_day = T_SIDEREAL_DAY / T_orbit
    
    # Search for best rational approximation (continued fractions)
    best_num_revs = 1
    best_num_days = 1
    min_error = float('inf')
    
    # Search within reasonable range for LEO missions (typically 1-30 days)
    for num_days in range(1, 31):
        num_revs = round(revs_per_day * num_days)
        actual_ratio = num_revs / num_days
        error = abs(actual_ratio - revs_per_day)
        
        if error < min_error:
            min_error = error
            best_num_revs = num_revs
            best_num_days = num_days
        
        # If we find an excellent match, stop early
        if error < 1e-4:
            break
    
    repeat_duration_sec = best_num_days * T_SIDEREAL_DAY
    
    return best_num_days, best_num_revs, repeat_duration_sec


def generate_walker_constellation(numSatellites, altitude_km, inclination_deg, numPlanes, relativeSpacing=1):
    """Generate Walker constellation orbital elements (T/P/F).

    Args:
        numSatellites (int): Total number of satellites (T)
        altitude_km (float): Orbit altitude above Earth in km
        inclination_deg (float): Inclination in degrees
        numPlanes (int): Number of orbital planes (P)
        relativeSpacing (int): Relative spacing factor (F)

    Returns:
        list: List of dicts with keys: altitude_km, inclination_deg, raan_deg, mean_anomaly_deg
    """
    if numPlanes <= 0:
        raise ValueError("numPlanes must be > 0")
    if numSatellites <= 0:
        raise ValueError("numSatellites must be > 0")

    satsPerPlane = int(np.ceil(numSatellites / numPlanes))
    deltaRAAN = 360.0 / numPlanes
    deltaM = 360.0 / satsPerPlane if satsPerPlane > 0 else 0.0

    elements = []
    satIndex = 0
    for plane in range(numPlanes):
        raan = plane * deltaRAAN
        for s in range(satsPerPlane):
            if satIndex >= numSatellites:
                break
            mean_anomaly = (s * deltaM + (plane * relativeSpacing) * (360.0 / numSatellites)) % 360.0
            elements.append({
                "altitude_km": altitude_km,
                "inclination_deg": inclination_deg,
                "raan_deg": raan,
                "mean_anomaly_deg": mean_anomaly
            })
            satIndex += 1

    return elements


# Ground target database (20 major cities)
CITY_DATABASE = [
    ("Beijing", 39.9042, 116.4074, 50),
    ("NewYork", 40.7128, -74.0060, 10),
    ("London", 51.5074, -0.1278, 20),
    ("Tokyo", 35.6762, 139.6503, 40),
    ("Sydney", -33.8688, 151.2093, 15),
    ("Moscow", 55.7558, 37.6173, 150),
    ("Cairo", 30.0444, 31.2357, 20),
    ("BuenosAires", -34.6037, -58.3816, 25),
    ("Mumbai", 19.0760, 72.8777, 10),
    ("Toronto", 43.6532, -79.3832, 175),
    ("Paris", 48.8566, 2.3522, 35),
    ("Berlin", 52.5200, 13.4050, 34),
    ("Rome", 41.9028, 12.4964, 20),
    ("Madrid", 40.4168, -3.7038, 650),
    ("Seoul", 37.5665, 126.9780, 38),
    ("Singapore", 1.3521, 103.8198, 15),
    ("Dubai", 25.2048, 55.2708, 5),
    ("Shanghai", 31.2304, 121.4737, 4),
    ("LosAngeles", 34.0522, -118.2437, 71),
    ("SaoPaulo", -23.5505, -46.6333, 760),
]


def generate_random_targets(num_targets, seed=None):
    """Generate random ground targets distributed globally
    
    Args:
        num_targets (int): Number of targets to generate
        seed (int, optional): Random seed for reproducibility
    
    Returns:
        list: List of (name, lat, lon, alt) tuples in degrees
    """
    if seed is not None:
        np.random.seed(seed)
    
    targets = []
    for i in range(num_targets):
        lat = np.random.uniform(-53, 53)  # Core coverage zone for Walker constellation
        lon = np.random.uniform(-180, 180)
        alt = np.random.uniform(0, 1000)  # 0-1000m altitude
        name = f"t{i+1}"
        targets.append((name, lat, lon, alt))
    
    return targets


def generate_grid_targets(num_lat=5, num_lon=7):
    """Generate ground targets in a regular grid pattern
    
    Args:
        num_lat (int): Number of latitude bands
        num_lon (int): Number of longitude divisions
    
    Returns:
        list: List of (name, lat, lon, alt) tuples in degrees
    """
    targets = []
    lats = np.linspace(-60, 60, num_lat)
    lons = np.linspace(-180, 150, num_lon)
    
    idx = 1
    for lat in lats:
        for lon in lons:
            name = f"t{idx}"
            alt = 100.0  # Fixed altitude
            targets.append((name, lat, lon, alt))
            idx += 1
    
    return targets
