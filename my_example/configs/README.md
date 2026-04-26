# 实验配置目录

当前正式实验只使用三类任务压力配置：

| 场景 | 配置文件 | 卫星 | 目标 | 单星容量 | 总容量 | 目标/容量 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 资源富余 | `scenario_surplus_30sat_100tar.yaml` | 30 | 100 | 20 | 600 | 0.167 |
| 正常冲突 | `scenario_normal_30sat_400tar.yaml` | 30 | 400 | 20 | 600 | 0.667 |
| 严重冲突 | `scenario_severe_30sat_1000tar.yaml` | 30 | 1000 | 20 | 600 | 1.667 |

固定容量口径：

```text
单星理论容量 = 200 Mbits / 10 Mbits = 20 个目标/天
星座理论总容量 = 30 * 20 = 600 个目标/天
```

正式优化算法参数：

| 场景 | GA population | GA generations | GA mutation | SA initial T | SA final T | SA cooling | SA iter/T |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 资源富余 | 120 | 200 | 0.15 | auto | 0.05 | 0.970 | 60 |
| 正常冲突 | 220 | 350 | 0.12 | auto | 0.05 | 0.975 | 250 |
| 严重冲突 | 300 | 450 | 0.10 | auto | 0.05 | 0.980 | 360 |

正式多 seed 口径：

```text
所有正式统计均使用 seeds = 1,2,3,4,5。
严重冲突场景可拆成 all_no_ga 与 genetic 两次运行，但 seed 集合保持一致。
```

`legacy/` 中保留旧版 `small/default/medium/large/ablation_*` 配置，仅用于追溯历史实验，不再作为论文正式实验配置。
