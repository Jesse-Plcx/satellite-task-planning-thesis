# TODO（my_example）

本文档仅记录当前正式实验口径下仍需闭环的事项。旧版 `small/default/medium/large/ablation_*` 实验已转入历史归档，不再作为论文正式结论依据。

## 1. 当前正式实验口径

固定条件：

- 卫星数：30
- 单星理论容量：20 个目标/天
- 星座理论总容量：600 个目标/天
- 仿真时长：1 天
- 统计种子：`1,2,3,4,5`
- 正式配置：`configs/scenario_surplus_30sat_100tar.yaml`、`configs/scenario_normal_30sat_400tar.yaml`、`configs/scenario_severe_30sat_1000tar.yaml`

## 2. 当前优先事项

| 优先级 | 事项 | 当前判断 | 下一步建议 |
| --- | --- | --- | --- |
| P0 | 三类场景多 seed 正式运行 | 配置已确定，旧结果不再复用 | 按资源富余、正常冲突、严重冲突顺序执行 |
| P0 | 严重冲突 GA 长任务管理 | 1000 目标下 GA 耗时较高但实验室资源充足 | 拆成 `all_no_ga` 和 `genetic`，均使用 5 seeds |
| P1 | 第四章图表重生成 | 旧图表已隔离为历史材料 | 新结果完成后重新生成 `reports/ch4/assets/` |
| P1 | 论文表述统一 | 旧 large/default 结论不再进入正文 | 统一改为三类任务压力对比 |
| P2 | 假设与局限整理 | 理论容量不等于实际可完成数 | 在第四章说明可见窗口和机动约束的影响 |

## 3. 推荐执行命令

```powershell
python run_multiseed.py --config configs/scenario_surplus_30sat_100tar.yaml --algorithm all --seeds 1,2,3,4,5
python run_multiseed.py --config configs/scenario_normal_30sat_400tar.yaml --algorithm all --seeds 1,2,3,4,5
python run_multiseed.py --config configs/scenario_severe_30sat_1000tar.yaml --algorithm all_no_ga --seeds 1,2,3,4,5
python run_multiseed.py --config configs/scenario_severe_30sat_1000tar.yaml --algorithm genetic --seeds 1,2,3,4,5
```

## 4. 旧材料处理

- 旧配置已保留在 `configs/legacy/`。
- 旧实验结果仍保留在 `res/`。
- 旧第四章图表和索引应只作为历史材料，不再支撑最终结论。
