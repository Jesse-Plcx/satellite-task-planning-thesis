"""Visualization functions for task planning results"""
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime



def plot_task_planning_results(targetList, satResources, numSatellites, duration, 
                               algorithmName="Algorithm", output_dir=None):

    """
    Generate comprehensive visualization:
    - Figure 1: Gantt chart of task execution timeline
    - Figure 2: Three-panel analysis (task distribution, storage, coverage)
    Saves figures to res/YYYYMMDD_HHMMSS/ directory
    
    Args:
        output_dir: Optional existing directory path. If None, creates new timestamped directory.
    
    Returns:
        str: Path to the output directory containing saved figures
    """
    # Create or use timestamped output directory
    if output_dir is None:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # my_example directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join(script_dir, 'res', 'runs', timestamp)
        os.makedirs(output_dir, exist_ok=True)
    else:
        # Ensure the provided directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    # Find actual task time range
    all_starts = []
    all_ends = []
    for i in range(numSatellites):
        for task in satResources[i].tasks_completed:
            all_starts.append(task['start'])
            all_ends.append(task['end'])
    
    if all_starts:
        time_min = min(all_starts)
        time_max = max(all_ends)
        time_range = time_max - time_min
        # Add 5% padding on each side
        time_start = max(0, time_min - time_range * 0.05)
        time_end = time_max + time_range * 0.05
    else:
        time_start = 0
        time_end = duration
    
    # Figure 1: Gantt Chart
    fig1, ax1 = plt.subplots(figsize=(16, max(8, numSatellites * 0.4)))
    colors = plt.cm.tab20(np.linspace(0, 1, 20))  # More colors for better distinction
    
    for i in range(numSatellites):
        for task in satResources[i].tasks_completed:
            targetId = task['targetId']
            start = task['start']
            duration_task = task['end'] - start
            
            # Draw task bar
            ax1.barh(i, duration_task, left=start, height=0.7, 
                    color=colors[targetId % 20], edgecolor='black', linewidth=0.8, alpha=0.9)
            
            # Only show label if bar is wide enough
            bar_width_in_pixels = (duration_task / (time_end - time_start)) * fig1.get_figwidth() * fig1.dpi
            if bar_width_in_pixels > 30:  # Only show if wider than 30 pixels
                ax1.text(start + duration_task/2, i, f"t{targetId+1}", 
                        ha='center', va='center', fontsize=8, color='white', weight='bold')
    
    # Format x-axis with time in minutes
    ax1.set_xlabel('Time (minutes)', fontsize=12, weight='bold')
    ax1.set_ylabel('Satellite', fontsize=12, weight='bold')
    ax1.set_yticks(range(numSatellites))
    ax1.set_yticklabels([f's{i+1}' for i in range(numSatellites)], fontsize=10)
    ax1.set_title(f'{algorithmName} - Task Execution Timeline', fontsize=14, weight='bold', pad=15)
    ax1.set_xlim(time_start, time_end)
    
    # Convert x-axis to minutes using FuncFormatter
    from matplotlib.ticker import FuncFormatter
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{int(x/60)}'))
    
    ax1.grid(axis='x', linestyle='--', alpha=0.4, linewidth=0.8)
    ax1.grid(axis='y', linestyle=':', alpha=0.2)
    ax1.set_axisbelow(True)
    
    # Add statistics text
    total_tasks = sum(len(satResources[i].tasks_completed) for i in range(numSatellites))
    stats_text = f'Total Tasks: {total_tasks} | Time Range: {time_min/60:.1f}-{time_max/60:.1f} min'
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Save Gantt chart
    fig1.savefig(
        os.path.join(output_dir, f'{algorithmName.lower()}_gantt.png'),
        dpi=300,
        bbox_inches='tight'
    )
    
    # Figure 2: Three-panel Analysis
    fig2, (ax2_1, ax2_2, ax2_3) = plt.subplots(1, 3, figsize=(15, 5))
    
    # Panel 1: Task Distribution
    task_counts = [len(satResources[i].tasks_completed) for i in range(numSatellites)]
    bars = ax2_1.bar(range(numSatellites), task_counts, color='steelblue', edgecolor='black')
    for bar, count in zip(bars, task_counts):
        height = bar.get_height()
        ax2_1.text(bar.get_x() + bar.get_width()/2., height,
                  f'{int(count)}', ha='center', va='bottom', fontsize=9)
    ax2_1.set_xlabel('Satellite ID', fontsize=11)
    ax2_1.set_ylabel('Number of Tasks', fontsize=11)
    ax2_1.set_title('Task Distribution', fontsize=12, weight='bold')
    ax2_1.set_xticks(range(numSatellites))
    ax2_1.set_xticklabels([f's{i+1}' for i in range(numSatellites)], fontsize=9)
    ax2_1.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Panel 2: Storage Utilization
    storage_used = [satResources[i].storage_used / 1e6 for i in range(numSatellites)]  # Convert to Mbits
    max_storage = satResources[0].storage_capacity / 1e6
    bars = ax2_2.bar(range(numSatellites), storage_used, color='coral', edgecolor='black')
    for bar, used in zip(bars, storage_used):
        height = bar.get_height()
        ax2_2.text(bar.get_x() + bar.get_width()/2., height,
                  f'{int(used)}', ha='center', va='bottom', fontsize=9)
    ax2_2.axhline(y=max_storage, color='red', linestyle='--', linewidth=2, label=f'Max: {max_storage} Mbits')
    ax2_2.set_xlabel('Satellite ID', fontsize=11)
    ax2_2.set_ylabel('Storage Used (Mbits)', fontsize=11)
    ax2_2.set_title('Storage Utilization', fontsize=12, weight='bold')
    ax2_2.set_xticks(range(numSatellites))
    ax2_2.set_xticklabels([f's{i+1}' for i in range(numSatellites)], fontsize=9)
    ax2_2.legend(fontsize=9)
    ax2_2.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Panel 3: Coverage Summary
    covered = sum(1 for target in targetList if target.imaged)
    uncovered = len(targetList) - covered
    coverage_pct = (covered / len(targetList)) * 100
    
    sizes = [covered, uncovered]
    labels = [f'Imaged: {covered}\n({coverage_pct:.1f}%)', f'Not Imaged: {uncovered}']
    colors_pie = ['#66c2a5', '#fc8d62']
    explode = (0.05, 0)
    
    wedges, texts, autotexts = ax2_3.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
                                          autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10})
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_weight('bold')
    ax2_3.set_title('Target Coverage', fontsize=12, weight='bold')
    
    plt.tight_layout()
    
    # Save analysis figure
    fig2.savefig(
        os.path.join(output_dir, f'{algorithmName.lower()}_analysis.png'),
        dpi=300,
        bbox_inches='tight'
    )
    
    # Non-blocking show so batch runs can continue
    plt.show(block=False)
    plt.pause(0.1)
    
    return output_dir
