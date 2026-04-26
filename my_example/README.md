# Satellite Task Planning Project

本项目用于多星对地观测任务规划仿真与算法对比。当前论文第四章正式实验已经统一切换为“三类任务压力场景”：资源富余、正常冲突、严重冲突。旧版 `small/default/medium/large/ablation_*` 配置已移动到 `configs/legacy/`，只用于追溯历史实验。

## 项目结构

```text
my_example/
  main.py
  config_loader.py
  run_multiseed.py
  run_all_configs.py
  configs/
    scenario_surplus_30sat_100tar.yaml
    scenario_normal_30sat_400tar.yaml
    scenario_severe_30sat_1000tar.yaml
    legacy/
  algorithms/
  common/
  res/
  reports/
```

## 正式实验配置

固定条件：

| 参数 | 数值 |
| --- | ---: |
| 卫星数 | 30 |
| 轨道面数 | 6 |
| 单星存储 | 200 Mbits |
| 单目标图像大小 | 10 Mbits |
| 单星理论容量 | 20 个目标/天 |
| 星座理论总容量 | 600 个目标/天 |
| 仿真时长 | 86400 s |
| 姿态转换时间 | 30 s |
| 成像时间 | 10 s |

正式场景：

| 场景 | 配置文件 | 目标数 | 目标/容量 |
| --- | --- | ---: | ---: |
| 资源富余 | `configs/scenario_surplus_30sat_100tar.yaml` | 100 | 0.167 |
| 正常冲突 | `configs/scenario_normal_30sat_400tar.yaml` | 400 | 0.667 |
| 严重冲突 | `configs/scenario_severe_30sat_1000tar.yaml` | 1000 | 1.667 |

正式优化算法参数：

| 场景 | GA population | GA generations | GA mutation | SA cooling | SA iter/T |
| --- | ---: | ---: | ---: | ---: | ---: |
| 资源富余 | 120 | 200 | 0.15 | 0.970 | 60 |
| 正常冲突 | 220 | 350 | 0.12 | 0.975 | 250 |
| 严重冲突 | 300 | 450 | 0.10 | 0.980 | 360 |

容量口径：

```text
单星理论容量 = 200 / 10 = 20
星座理论总容量 = 30 * 20 = 600
目标/容量 = 目标数 / 600
```

## 快速开始

默认运行等价于正常冲突场景：

```bash
python main.py
```

运行单个正式配置：

```bash
python main.py --config configs/scenario_surplus_30sat_100tar.yaml --algorithm all --no-vizard
python main.py --config configs/scenario_normal_30sat_400tar.yaml --algorithm all --no-vizard
python main.py --config configs/scenario_severe_30sat_1000tar.yaml --algorithm all_no_ga --no-vizard
```

运行多 seed 正式实验：

```bash
python run_multiseed.py --config configs/scenario_surplus_30sat_100tar.yaml --algorithm all --seeds 1,2,3,4,5
python run_multiseed.py --config configs/scenario_normal_30sat_400tar.yaml --algorithm all --seeds 1,2,3,4,5
python run_multiseed.py --config configs/scenario_severe_30sat_1000tar.yaml --algorithm all_no_ga --seeds 1,2,3,4,5
python run_multiseed.py --config configs/scenario_severe_30sat_1000tar.yaml --algorithm genetic --seeds 1,2,3,4,5
```

批量运行三个正式配置：

```bash
python run_all_configs.py --algorithm all --no-show
```

## 算法选项

`--algorithm` 可选：

- `random`：随机基线
- `ewf`：最早窗口优先
- `greedy`：改进贪心
- `sa`：模拟退火
- `genetic`：遗传算法
- `both`：改进贪心与遗传算法
- `all`：五类算法全部运行
- `all_no_ga`：除遗传算法外的四类算法

严重冲突场景建议先运行 `all_no_ga`，再单独运行 `genetic`，便于分段管理长时间任务；两条命令仍采用相同的 `1,2,3,4,5` 种子。

## 输出结果

单次运行输出：

```text
res/runs/<config_name>_<timestamp>/
```

多 seed 汇总输出：

```text
res/multiseed/<config_name>_<timestamp>/
```

典型文件：

- `metrics_summary.json`
- `run_summary.txt`
- `all_runs.csv`
- `summary.csv`
- `summary.md`
- `manifest.json`

## 论文材料

- `reports/reference/CONFIGS_SUMMARY.md`：正式配置摘要
- `reports/ch4/EXPERIMENT_PLAN.md`：第四章执行方案
- `reports/ch4/EXECUTION_LOG.md`：正式实验执行记录
- `reports/ch4/RESULTS_INDEX.md`：正式结果索引
- `reports/ch4/assets/legacy_20260424/`：旧版图表与表格归档

新实验结果完成后，再运行 `reports/ch4/tools/generate_artifacts.py` 生成新的第四章表格、图和 `artifact_manifest.json`。

## 旧材料

旧配置保留在：

```text
configs/legacy/
```

旧实验结果仍保留在：

```text
res/
reports/history/
reports/ch4/assets/legacy_20260424/
```

这些材料只用于追溯，不再作为当前论文正式主结论依据。
