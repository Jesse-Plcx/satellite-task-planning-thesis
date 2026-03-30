"""Basilisk simulation setup and access window processing"""
import os
from datetime import datetime
import numpy as np
from Basilisk.simulation import spacecraft, groundLocation
from Basilisk.utilities import (SimulationBaseClass, macros, orbitalMotion,
                                simIncludeGravBody, unitTestSupport, vizSupport)
from Basilisk.architecture import astroConstants

if vizSupport.vizFound:
    from Basilisk.simulation import vizInterface

from .data_structures import TargetData, SatelliteResources
from .scenario_generator import CITY_DATABASE, generate_random_targets, generate_grid_targets



def _sample_priority(satResourcesConfig):
    """Sample a target priority from Uniform[priority_min, priority_max]."""
    cfg = satResourcesConfig or {}
    lo = float(cfg.get('priority_min', 0.1))
    hi = float(cfg.get('priority_max', 1.0))
    return float(np.random.uniform(lo, hi))


def setup_simulation(numSatellites, numTargets, walkerElements, targetMode='random', 
                     duration=None, useVizard=False, targetSeed=42, satResourcesConfig=None):
    """
    Setup Basilisk simulation with constellation and ground targets
    
    Args:
        satResourcesConfig: Optional dict with satellite resource configuration
    
    Returns:
        tuple: (scSim, targetList, satResources, accessRecorders, duration)
    """
    simTaskName = "simTask"
    simProcessName = "simProcess"
    
    scSim = SimulationBaseClass.SimBaseClass()
    scSim.SetProgressBar(True)
    
    dynProcess = scSim.CreateNewProcess(simProcessName)
    simulationTimeStep = macros.sec2nano(2.0)
    dynProcess.addTask(scSim.CreateNewTask(simTaskName, simulationTimeStep))
    
    gravFactory = simIncludeGravBody.gravBodyFactory()
    earth = gravFactory.createEarth()
    earth.isCentralBody = True
    mu = earth.mu
    
    timeInitString = "2024 January 1 00:00:00.0 (UTC)"
    spiceObject = gravFactory.createSpiceInterface(time=timeInitString)
    spiceObject.zeroBase = 'Earth'
    scSim.AddModelToTask(simTaskName, spiceObject)
    
    # ------------------------------------------------------------------ #
    # Minimum elevation angle constraint                                  #
    # (Use a single constraint for clarity; no explicit max-range filter.)#
    # ------------------------------------------------------------------ #
    MIN_ELEVATION_DEG = 15.0

    # Visibility criteria summary is now written to the run summary file.
    simulationTime = macros.sec2nano(duration)

    # Sampling interval: must be strictly less than imaging_time_sec so that
    # no valid window (duration ≥ imaging_time) can fall entirely between two
    # consecutive sample points.  Using (imaging_time - 1) s is the tightest
    # safe value and is uniform across all scenario sizes, keeping cross-
    # scenario results comparable.
    #
    # Worst-case memory: large_scale (24×500=12 000 pairs) at 9 s interval
    #   → 86400/9 × 12 000 ≈ 115 M records ≈ 920 MB  (acceptable)
    imaging_time = satResourcesConfig.get('imaging_time_sec', 10.0) if satResourcesConfig else 10.0
    sample_interval_sec = max(1.0, imaging_time - 1.0)   # e.g. 9 s for imaging_time=10 s

    numDataPoints = int(duration / sample_interval_sec)
    if os.environ.get("MY_EXAMPLE_DEBUG") == "1":
        print(f"\nData sampling: {numDataPoints} points ({sample_interval_sec:.0f}s interval)"
              f"  [imaging_time={imaging_time:.0f}s → max safe interval={sample_interval_sec:.0f}s]")
    samplingTime = unitTestSupport.samplingTime(simulationTime, simulationTimeStep, numDataPoints)
    
    # Create spacecraft
    scList = []
    satResources = []
    I = [900., 0., 0., 0., 800., 0., 0., 0., 600.]
    
    print(f"\nCreating constellation with {numSatellites} satellites...")
    for i in range(numSatellites):
        scList.append(spacecraft.Spacecraft())
        scList[i].ModelTag = f"s{i+1}"
    
    for sc in scList:
        scSim.AddModelToTask(simTaskName, sc)
    
    for sc in scList:
        gravFactory.addBodiesTo(sc)
    
    for i in range(numSatellites):
        config = walkerElements[i]
        oe = orbitalMotion.ClassicElements()
        oe.a = astroConstants.REQ_EARTH * 1e3 + config["altitude_km"] * 1e3
        oe.e = 0.001
        oe.i = config["inclination_deg"] * macros.D2R
        oe.Omega = config["raan_deg"] * macros.D2R
        oe.omega = 0.0
        oe.f = config["mean_anomaly_deg"] * macros.D2R
        
        rN, vN = orbitalMotion.elem2rv(mu, oe)
        scList[i].hub.r_CN_NInit = rN
        scList[i].hub.v_CN_NInit = vN
        scList[i].hub.mHub = 750.0
        scList[i].hub.IHubPntBc_B = unitTestSupport.np2EigenMatrix3d(I)
        scList[i].hub.sigma_BNInit = [[0.0], [0.0], [0.0]]
        scList[i].hub.omega_BN_BInit = [[0.0], [0.0], [0.0]]
        
        satResources.append(SatelliteResources(sat_id=i, config=satResourcesConfig))
    
    # Generate targets
    if targetMode == 'cities':
        targetLocations = CITY_DATABASE[:numTargets]
    elif targetMode == 'random':
        targetLocations = generate_random_targets(numTargets, seed=targetSeed)
    elif targetMode == 'grid':
        lat_pts = int(np.sqrt(numTargets / 2))
        lon_pts = int(numTargets / lat_pts)
        targetLocations = generate_grid_targets(lat_pts, lon_pts)[:numTargets]
    else:
        raise ValueError(f"Invalid targetMode: {targetMode}")
    
    # Create ground targets
    targetList = []
    targetObjects = []
    
    print(f"\nCreating {numTargets} ground targets...")
    for i in range(numTargets):
        loc = targetLocations[i % len(targetLocations)]
        name = f"{loc[0]}_{i+1}" if i >= len(targetLocations) else loc[0]
        
        target = TargetData(
            name=name,
            lat=np.radians(loc[1]),
            lon=np.radians(loc[2]),
            alt=loc[3],
            priority=_sample_priority(satResourcesConfig)
        )
        targetList.append(target)
        
        groundTarget = groundLocation.GroundLocation()
        groundTarget.ModelTag = f"target_{name}"
        groundTarget.planetRadius = astroConstants.REQ_EARTH * 1e3  # WGS-84 Earth radius
        groundTarget.planetInMsg.subscribeTo(spiceObject.planetStateOutMsgs[0])  # 关键：关联到自转的地球！
        groundTarget.specifyLocation(target.lat, target.lon, target.alt)
        groundTarget.minimumElevation = np.radians(MIN_ELEVATION_DEG)  # 15° minimum elevation
        # NOTE: maximumRange not set (no explicit range filter)
        
        for sc in scList:
            groundTarget.addSpacecraftToModel(sc.scStateOutMsg)
        
        scSim.AddModelToTask(simTaskName, groundTarget, ModelPriority=100)
        targetObjects.append(groundTarget)
    
    # Setup Vizard if requested
    if vizSupport.vizFound and useVizard:
        genericSensorList = []
        for i in range(numSatellites):
            genericSensor = vizInterface.GenericSensor()
            genericSensor.r_SB_B = [0.0, 0.0, 1.0]
            genericSensor.fieldOfView.push_back(2.5 * macros.D2R)  # 2.5° half-angle FOV
            genericSensor.normalVector = [0.0, 0.0, 1.0]
            genericSensor.color = vizInterface.IntVector(vizSupport.toRGBA255("red", alpha=0.25))
            genericSensor.label = f"s{i+1}"
            genericSensorList.append([genericSensor])
        
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # my_example directory
        viz_dir = os.path.join(script_dir, "res", "viz")
        os.makedirs(viz_dir, exist_ok=True)
        viz_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        viz_save_path = os.path.join(viz_dir, f"my_example_{viz_ts}.bin")

        viz = vizSupport.enableUnityVisualization(
            scSim, simTaskName, scList,
            saveFile=viz_save_path,
            genericSensorList=genericSensorList
        )
        
        vizSupport.setInstrumentGuiSetting(viz, showGenericSensorLabels=True)
        viz.settings.spacecraftSizeMultiplier = 1.5
        viz.settings.showLocationCommLines = 1
        viz.settings.showLocationCones = 1
        viz.settings.showLocationLabels = 1
        viz.settings.orbitLinesOn = 1
        viz.settings.trueTrajectoryLinesOn = 1
        viz.settings.showSpacecraftLabels = True
        viz.settings.mainCameraTarget = 'earth'
        
        for target in targetList:
            vizSupport.addLocation(
                viz, stationName=target.name, parentBodyName=earth.displayName,
                lla_GP=[target.lat, target.lon, target.alt],
                fieldOfView=np.radians(15.0), color="pink", range=3000.0 * 1e3
            )
    
    # Setup access recorders
    accessRecorders = []
    for targetId, targetObj in enumerate(targetObjects):
        recorders = []
        for satId, msg in enumerate(targetObj.accessOutMsgs):
            recorder = msg.recorder(samplingTime)
            scSim.AddModelToTask(simTaskName, recorder)
            recorders.append(recorder)
        accessRecorders.append(recorders)
    
    # Initialize and run simulation
    scSim.InitializeSimulation()
    print(f"\nRunning simulation for {duration/60:.1f} minutes...")
    scSim.ConfigureStopTime(simulationTime)
    scSim.ExecuteSimulation()
    
    return scSim, targetList, satResources, accessRecorders, duration


def process_access_windows(accessRecorders, numSatellites, numTargets, min_window_duration=10.0,
                           sat_altitudes_km=None, max_roll_angle_deg=None):
    print("\nProcessing access windows...")
    accessWindows = {}
    
    # Optional off-nadir (roll-only) constraint
    max_off_nadir_rad = np.radians(max_roll_angle_deg) if max_roll_angle_deg is not None else None
    use_off_nadir_filter = (sat_altitudes_km is not None) and (max_off_nadir_rad is not None)
    if use_off_nadir_filter:
        max_off_nadir_deg = np.degrees(max_off_nadir_rad)
    
    for targetId, recorders in enumerate(accessRecorders):
        for satId, recorder in enumerate(recorders):
            times = recorder.times() * macros.NANO2SEC
            hasAccess = np.array(recorder.hasAccess, dtype=bool)
            
            # Extract BSK's rich access data
            elevations = np.array(recorder.elevation)  # [rad]
            slantRanges = np.array(recorder.slantRange)  # [m]

            # Optional off-nadir (roll/FOV) filter using slant range geometry
            if use_off_nadir_filter:
                sat_alt_km = sat_altitudes_km[satId]
                earth_radius_m = astroConstants.REQ_EARTH * 1e3
                sat_radius_m = earth_radius_m + sat_alt_km * 1e3
                safe_rho = np.where(slantRanges > 0.0, slantRanges, np.nan)
                cos_theta = (sat_radius_m**2 + safe_rho**2 - (earth_radius_m**2)) / (2.0 * sat_radius_m * safe_rho)
                cos_theta = np.clip(cos_theta, -1.0, 1.0)
                off_nadir = np.arccos(cos_theta)  # [rad]
                off_nadir_mask = np.isfinite(off_nadir) & (off_nadir <= max_off_nadir_rad)
                hasAccess = hasAccess & off_nadir_mask
            
            if len(times) == 0 or not np.any(hasAccess):
                continue
            
            # Vectorized detection of access window changes
            # Add False at boundaries to detect first/last windows
            access_padded = np.concatenate([[False], hasAccess, [False]])
            access_changes = np.diff(access_padded.astype(int))
            
            # Indices where access starts (0->1) and ends (1->0)
            start_indices = np.where(access_changes > 0)[0]
            end_indices = np.where(access_changes < 0)[0] - 1  # -1 because diff shifts by 1
            
            
            windows = []
            for start_idx, end_idx in zip(start_indices, end_indices):
                windowStart = times[start_idx]
                windowEnd = times[end_idx]
                duration = windowEnd - windowStart
                
                # Filter minimum duration
                if duration >= min_window_duration:  # Discard windows too short to complete imaging
                    # Extract quality metrics for this window
                    window_elevations = elevations[start_idx:end_idx+1]
                    window_ranges = slantRanges[start_idx:end_idx+1]
                    
                    max_elevation = np.max(window_elevations) if len(window_elevations) > 0 else 0.0
                    min_range = np.min(window_ranges) if len(window_ranges) > 0 else np.inf
                    
                    windows.append((
                        windowStart, 
                        windowEnd, 
                        duration,
                        max_elevation,  # [rad] - higher is better
                        min_range       # [m] - lower is better
                    ))
            
            if windows:
                accessWindows[(satId, targetId)] = windows
    
    totalWindows = sum(len(windows) for windows in accessWindows.values())
    targets_with_windows = set(targetId for (satId, targetId) in accessWindows.keys())
    
    print(f"✓ Found {totalWindows} valid access windows for {len(targets_with_windows)}/{numTargets} targets")
    print(f"  (with elevation and range metrics for quality assessment)")
    
    return accessWindows
