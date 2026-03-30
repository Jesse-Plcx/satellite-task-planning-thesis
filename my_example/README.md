# Satellite Task Planning Project

## 项目结构

```
my_example/
├── main.py                      # 主程序入口（算法对比）
├── config_loader.py             # 配置文件加载器
├── common/                      # 共享模块
│   ├── __init__.py
│   ├── data_structures.py      # 数据结构 (TargetData, SatelliteResources)
│   ├── scenario_generator.py   # Walker星座与目标生成
│   ├── simulator.py            # Basilisk仿真设置、访问窗口处理
│   └── visualization.py        # 绘图函数
├── algorithms/                  # 算法模块
│   ├── __init__.py
│   ├── random_baseline.py      # Random 下界基线
│   ├── ewf.py                  # EWF 基础贪心
│   ├── greedy.py               # 改进贪心算法
│   ├── sa.py                   # 模拟退火算法
│   └── genetic.py              # 遗传算法
├── configs/                     # 配置文件目录
│   ├── default.yaml            # 默认配置
│   ├── small.yaml              # 小规模配置
│   ├── medium.yaml             # 中规模配置
│   ├── large.yaml              # 大规模配置（24卫星×500目标）
│   ├── ablation_high_agility.yaml      # 敏捷性消融实验
│   └── ablation_resource_constrained.yaml  # 资源限制消融实验
├── res/                         # 输出结果根目录
│   └── runs/                    # 运行结果（按时间戳生成子目录）
├── reports/                     # 分析/报告文档
│   ├── KEY_FORMULAS.md          # 关键公式（与代码一致）
│   └── my_example_analysis.md
└── TODO.md                      # 待办事项
```

## 卫星资源配置（配置文件）

```yaml
satellite_resources:
  storage_capacity_mbits: 100.0  # 存储容量（Mbits）
  image_size_mbits: 10.0         # 单张图像大小（Mbits）
  slew_time_sec: 30.0            # 目标间机动时间（秒）
  imaging_time_sec: 10.0         # 成像时间（秒）
  max_roll_angle_deg: 45.0       # 最大滚动角（度）
  sensor_fov_deg: 2.5            # 传感器视场角半角（度）
```

说明：`max_roll_angle_deg` 会作为可见性约束使用（离天底角上限），`sensor_fov_deg` 仅作为传感器参数说明。

## 快速开始

### 1. 安装依赖

```bash
# 在仓库根目录安装依赖
pip install -r requirements.txt
```

### 2. 使用配置文件运行（推荐）

```bash
# 小规模测试
python main.py --config configs/small.yaml

# 中规模实验
python main.py --config configs/medium.yaml

# 大规模实验（24卫星，500目标，1天）
python main.py --config configs/large.yaml
```

### 3. 命令行参数覆盖配置

```bash
# 使用配置文件，但修改卫星和目标数量
python main.py --config configs/default.yaml --satellites 12 --targets 50

# 只运行随机基线
python main.py --config configs/default.yaml --algorithm random

# 只运行基础贪心算法
python main.py --config configs/default.yaml --algorithm ewf

# 只运行改进贪心算法
python main.py --config configs/default.yaml --algorithm greedy

# 只运行模拟退火算法
python main.py --config configs/default.yaml --algorithm sa

# 修改遗传算法参数
python main.py --config configs/default.yaml --pop-size 100 --generations 200
```

## 使用方法

### 1. 运行单个算法

```bash
python main.py --config configs/default.yaml --algorithm random
python main.py --config configs/default.yaml --algorithm ewf
python main.py --config configs/default.yaml --algorithm greedy
python main.py --config configs/default.yaml --algorithm sa
python main.py --config configs/default.yaml --algorithm genetic
```

### 2. 对比两个算法

```bash
# 主对比：改进贪心 vs 遗传算法
python main.py --config configs/default.yaml --algorithm both

# 五算法总对比：Random + EWF + Improved Greedy + SA + Genetic
python main.py --config configs/default.yaml --algorithm all
```

### 3. 完整参数说明

```bash
python main.py --help
```

主要参数：
- `--config`
  配置文件路径，通常直接用 `configs/default.yaml`、`configs/small.yaml` 这类预设配置。
- `--algorithm`
  选择运行算法，可选 `random / ewf / greedy / sa / genetic / both / all`。
  `both` 表示主对比：`Improved Greedy vs Genetic`。
  `all` 表示全对比：`Random + EWF + Improved Greedy + SA + Genetic`。
- `--satellites`、`--targets`、`--target-mode`、`--duration`
  用来临时覆盖场景规模和仿真设置。
- `--seed`
  控制本次实验的随机种子；会同时影响目标场景生成和随机算法过程。
- `--planes`、`--altitude`、`--inclination`
  用来覆盖星座构型参数。
- `--sa-initial-temp`、`--sa-final-temp`、`--sa-cooling-rate`、`--sa-iter-per-temp`
  模拟退火参数。
- `--pop-size`、`--generations`、`--mutation-rate`
  遗传算法参数。

### 4. 多 seed 实验

当前脚本默认只服务主实验：对多个随机场景做统计汇总。

```bash
# 推荐主实验：default 场景下做 5 个 seed
python run_multiseed.py --config configs/default.yaml --algorithm all --seeds 1,2,3,4,5
```

批量统计结果会保存到：

- `res/multiseed/<config>_<timestamp>/all_runs.csv`
- `res/multiseed/<config>_<timestamp>/summary.csv`
- `res/multiseed/<config>_<timestamp>/summary.md`

## 算法说明

### 随机基线 (Random Baseline)
- 策略：随机打乱全部候选访问窗口，按可行性顺序接受任务
- 约束：与 EWF、改进贪心、SA、GA 使用同一套时间/存储/唯一性约束
- 仰角处理：与其余算法统一，采用实际成像中点估算仰角
- 用途：作为最低下界，衡量规则法和优化法相对“随机选择”的提升幅度

### 最早窗口优先 (Earliest Window First, EWF)
- 策略：按窗口开始时间从早到晚遍历候选任务，遇到可行任务就立即安排
- 排序规则：`windowStart -> windowEnd -> priority`
- 约束：存储容量、机动时间、成像时间、目标不重复成像
- 优点：实现简单、可解释性强，适合作为基础贪心基线
- 缺点：只强调“先到先服务”，不显式比较任务收益

### 改进贪心算法 (Improved Greedy)
- 策略：每次选择价值最高的任务执行
- 价值函数：`value = (priority + 0.3 * (elevation_factor - 1)) / (1 + time_to_start / time_half_life)`
- 仰角因子（基于窗口位置的中间点估算）：
  ```
  t_mid   = actual_start + imaging_time / 2
  t_peak  = (windowStart + windowEnd) / 2      # 近似峰值时刻
  phi     = max(0, 1 - ((t_mid - t_peak) / half_window)²)
  elev_est = 15° + (maxElev - 15°) * phi       # 最小仰角15°到峰值的插值
  elevation_factor = 1 + min(elev_est_deg / 90, 1)   # ∈ [1.17, 2.0]
  elevation_bonus = 0.3 * (elevation_factor - 1)
  ```
- 时间半衰期：`time_half_life = 1800.0`（30 分钟）
- 约束：存储容量、机动时间、成像时间、目标不重复成像
- 优点：在保持较快速度的同时，兼顾目标优先级、观测质量与等待代价
- 缺点：仍属于局部最优启发式

### 遗传算法 (Genetic)
- 编码：染色体 = 任务分配列表 [(satId, targetId, windowIdx), ...]
- 适应度：
  - `fitness = 100 * coverage_rate_internal + 0.5 * (priority_sum + 0.3 * elevation_bonus_sum)`
- `priority_sum = sum(priority)`，`elevation_bonus_sum = sum(elevation_factor - 1)`
- 遗传算子：锦标赛选择、均匀/双点交叉、自适应变异（含局部搜索）
- 优点：全局搜索能力强
- 缺点：计算时间长、参数敏感

### 模拟退火算法 (Simulated Annealing)
- 编码：与遗传算法一致，使用任务三元组 `(satId, targetId, windowIdx)`
- 初始解：从高质量候选任务中构造初始调度
- 邻域操作：
  - 替换低质量任务
  - 添加未覆盖高质量任务
  - 删除低质量任务
  - 切换同一任务的不同窗口
  - 对同一目标切换执行卫星
- 接受准则：若新解更优则直接接受；若更差，则按 `exp(Δfitness / T)` 概率接受
- 温度参数：
  - `initial_temperature`：默认自动标定，也可手动指定
  - `final_temperature`
  - `cooling_rate`
  - `iterations_per_temp`
- 优点：实现简单，能跳出局部最优，适合作为 GA 之外的全局搜索对照
- 缺点：参数同样敏感，规模增大后耗时也会明显上升

## 约束条件（与代码一致）

1. 可见性约束  
最小仰角：15°（当前唯一的可见性约束）  
最小窗口时长：imaging_time_sec（短于成像时间的窗口会被丢弃）  
传感器视场角与滚动角当前仅打印，不参与可见性/调度约束计算

2. 卫星资源约束  
存储容量、图像大小、机动时间、成像时间均在调度中生效  
滚动角限制当前仅打印

3. 任务约束  
每个目标只能被成像一次  
任务必须在访问窗口内完成  
任务之间需要满足机动时间间隔

## 输出结果

控制台输出：  
仿真配置、访问窗口统计、算法过程、评估指标、算法对比

可视化图表：  
Gantt 图、任务分配与存储利用、任务完成度饼图

输出目录：  
`my_example/res/runs/<config_name>_<timestamp>/`

## 关键公式

关键公式与变量说明见 `reports/KEY_FORMULAS.md`（与代码一致）。

## 开发扩展

### 添加新算法

1. 在 `algorithms/` 目录创建新文件（如 `simulated_annealing.py`）
2. 实现算法函数：
```python
def your_algorithm_task_planning(accessWindows, targetList, satResources,
                                 numSatellites, numTargets, **kwargs):
    return None
```
3. 在 `algorithms/__init__.py` 中导出
4. 在 `main.py` 中添加算法选项

### 修改约束条件

编辑 `common/data_structures.py` 中的 `SatelliteResources` 类参数：
```python
def __init__(self, satId):
    self.storage_capacity = 100.0  # Mbits
    self.image_size = 10.0         # Mbits
    self.slew_time = 30.0          # s
    self.imaging_time = 10.0       # s
```

### 调整星座配置

在 `common/scenario_generator.py` 中使用：
```python
walkerElements = generate_walker_constellation(
    numSatellites=6,
    numPlanes=3,
    altitude_km=550.0,
    inclination_deg=53.0
)
```

## 依赖项

主要依赖：
- Basilisk (仿真框架)
- NumPy
- Matplotlib
- PyYAML (配置文件支持)
- Python 3

## 配置文件系统

为什么使用配置文件：  
可维护性、可重复性、版本控制、批量实验

预设配置说明：

| 配置文件 | 卫星 | 目标 | 时长 | 用途 |
|---------|------|------|------|------|
| `default.yaml` | 6 | 150 | 1天 | 主实验标准场景 |
| `small.yaml` | 3 | 100 | 1天 | 小规模验证 |
| `medium.yaml` | 12 | 300 | 1天 | 中规模扩展 |
| `large.yaml` | 24 | 500 | 1天 | 大规模验证 |

## 注意事项

1. 遗传算法计算时间较长，建议先用小规模测试
2. 增大种群大小与迭代代数会提高任务完成度，但会显著增加运行时间
3. Vizard 可视化需要安装 Unity 后端支持
4. 随机种子影响目标分布，可调整以测试不同场景

