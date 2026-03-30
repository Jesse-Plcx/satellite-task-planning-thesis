# 关键公式（my_example）

本文档汇总 `my_example` 当前代码中的主要公式，统一按“公式、变量、用途”整理，便于论文和答辩直接引用。

## 1. 可见性约束

### 1.1 最小仰角

$$e \ge e_{\min}$$

来源：`my_example/common/simulator.py`

| 符号 | 含义 |
| --- | --- |
| $e$ | 当前仰角 |
| $e_{\min}$ | 最小仰角阈值，当前为 `15°` |

用途：在 `setup_simulation()` 中设置 `groundTarget.minimumElevation`，访问窗口只基于最小仰角判定。

## 2. 采样设置

### 2.1 采样间隔

$$\Delta t_{\text{sample}}=\max(1.0,\ t_{\text{imaging}}-1.0)$$

### 2.2 采样点数

$$N=\left\lfloor \frac{T}{\Delta t_{\text{sample}}}\right\rfloor$$

来源：`my_example/common/simulator.py`

| 符号 | 含义 |
| --- | --- |
| $\Delta t_{\text{sample}}$ | 采样间隔（秒） |
| $t_{\text{imaging}}$ | 成像时间（秒） |
| $N$ | 采样点数 |
| $T$ | 仿真总时长（秒） |

用途：保证采样间隔小于成像时间，避免有效窗口被采样点跳过。

## 3. 改进贪心价值函数

### 3.1 窗口位置系数

$$\phi=\max\!\left(0,\ 1-\left(\frac{t_{\text{mid}}-t_{\text{peak}}}{t_{\text{hw}}}\right)^{2}\right)$$

其中：

$$t_{\text{mid}}=t_{\text{start}}+\tfrac{t_{\text{imaging}}}{2}$$

$$t_{\text{start}}=\max(t_{\text{winStart}},\ t_{\text{lastEnd}}+t_{\text{slew}})$$

$$t_{\text{peak}}=\frac{t_{\text{winStart}}+t_{\text{winEnd}}}{2},\quad
t_{\text{hw}}=\frac{t_{\text{winEnd}}-t_{\text{winStart}}}{2}$$

### 3.2 成像中点估算仰角

$$\hat{e}=e_{\min}+\left(e_{\max}-e_{\min}\right)\phi$$

### 3.3 仰角因子

$$f_{\text{el}}=1+\min\!\left(\frac{\hat{e}_{\deg}}{90},\ 1\right)$$

### 3.4 时间半衰期

$$t_{1/2}=1800\ \text{s}$$

### 3.5 价值函数

$$V=\frac{p+\alpha\left(f_{\text{el}}-1\right)}{1+\dfrac{\Delta t_{\text{start}}}{t_{1/2}}},\quad \alpha=0.3$$

来源：`my_example/algorithms/greedy.py`

| 符号 | 含义 |
| --- | --- |
| $\phi$ | 窗口位置系数 |
| $t_{\text{start}}$ | 实际成像开始时刻 |
| $t_{\text{mid}}$ | 成像中点时刻 |
| $t_{\text{peak}}$ | 窗口中点时刻 |
| $t_{\text{hw}}$ | 窗口半宽 |
| $\hat{e}$ | 成像中点估算仰角 |
| $e_{\max}$ | 窗口峰值仰角 |
| $f_{\text{el}}$ | 仰角因子 |
| $p$ | 目标优先级 |
| $\Delta t_{\text{start}}$ | 距离可开始成像的等待时间 |
| $V$ | 贪心价值 |

用途：在 `greedy_task_planning()` 中对候选任务评分，综合考虑优先级、观测质量和等待代价。

## 4. 任务可行性时间约束

$$t_{\text{earliest}}=t_{\text{lastEnd}}+t_{\text{slew}}$$

$$t_{\text{start}}=\max(t_{\text{winStart}},\ t_{\text{earliest}})$$

$$t_{\text{end}}=t_{\text{start}}+t_{\text{imaging}}$$

可行条件：

$$t_{\text{end}}\le t_{\text{winEnd}}$$

来源：`my_example/algorithms/greedy.py`，`my_example/algorithms/genetic.py`

| 符号 | 含义 |
| --- | --- |
| $t_{\text{earliest}}$ | 最早可开始时间 |
| $t_{\text{lastEnd}}$ | 上一任务结束时间 |
| $t_{\text{slew}}$ | 机动时间 |
| $t_{\text{start}}$ | 本任务开始时间 |
| $t_{\text{end}}$ | 本任务结束时间 |
| $t_{\text{winStart}}$ | 窗口开始时间 |
| $t_{\text{winEnd}}$ | 窗口结束时间 |

用途：判断任务是否能在访问窗口内完成，是 Greedy、SA、GA 共用的核心可行性逻辑。

## 5. 外部评估指标

本节 M1 至 M3 为统一报告指标，由 `evaluate_schedule()` 计算；它们不是算法内部优化目标。

### 5.1 M1 任务完成率

$$C=\frac{N_{\text{covered}}}{N_{\text{total}}}$$

### 5.2 M2 优先级总分

$$P=\sum_{j \in \text{scheduled}} p_j$$

### 5.3 M3 平均成像仰角

$$\bar{e}=\frac{1}{N_{\text{tasks}}}\sum \hat{e}_j$$

### 5.4 完成时间比例（信息项）

$$\eta_t=\frac{\bar t_{\text{end}}}{T}\times 100\%$$

| 指标 | 含义 |
| --- | --- |
| $C$ | 完成目标占比，反映数量 |
| $P$ | 已完成目标优先级总和，反映收益 |
| $\bar{e}$ | 平均成像仰角，反映几何质量 |
| $\eta_t$ | 平均完成时间占总时长比例 |

用途：作为报告和论文中的统一对比口径。

## 6. GA 适应度函数

### 6.1 内部完成率

$$C_{\text{int}}=\frac{N_{\text{covered}}}{N_{\text{total}}}$$

### 6.2 适应度

$$F=100\,C_{\text{int}}+0.5\left(\sum p_j+0.3\sum\left(f_{\text{el},j}-1\right)\right)$$

来源：`my_example/algorithms/genetic.py`

| 符号 | 含义 |
| --- | --- |
| $F$ | 适应度 |
| $C_{\text{int}}$ | 内部完成率 |
| $p_j$ | 任务优先级 |
| $f_{\text{el},j}$ | 基于实际成像中点仰角的仰角因子 |

用途：作为 GA 的内部优化目标。其组成和外部 M1/M2/M3 有关联，但不完全相同，论文中应单独说明。

## 7. GA 任务质量评分

$$q=p+0.3\left(f_{\text{el}}-1\right)$$

$$f_{\text{el}}=1+\min\left(\frac{e_{\deg}}{90},\ 1\right)$$

来源：`my_example/algorithms/genetic.py`

| 符号 | 含义 |
| --- | --- |
| $q$ | 任务质量评分 |
| $p$ | 目标优先级 |
| $f_{\text{el}}$ | 仰角因子 |
| $e_{\deg}$ | 估算仰角（度） |

用途：在初始化和变异时优先保留高收益、高质量任务。

## 8. SA 接受准则与邻域

SA 沿用 GA 的任务编码和适应度函数，即内部目标函数与第 6 节完全一致：

\[
F=100\,C_{\text{int}}+0.5\left(\sum p_j+0.3\sum\left(f_{\text{el},j}-1\right)\right)
\]

其中：

| 符号 | 含义 |
| --- | --- |
| $F$ | SA 内部适应度 |
| $C_{\text{int}}$ | 内部完成率 |
| $p_j$ | 已执行任务的优先级 |
| $f_{\text{el},j}$ | 基于实际成像中点仰角的仰角因子 |

说明：

- SA 当前并不是直接优化外部报告指标 M1、M2、M3
- SA 对观测质量的偏好来自 $0.3(f_{\mathrm{el}}-1)$ 这一仰角奖励项

若候选邻域解的适应度为 \(F_{\text{cand}}\)，当前解的适应度为 \(F_{\text{curr}}\)，则：

\[
\Delta F = F_{\text{cand}} - F_{\text{curr}}
\]

接受准则为：

\[
\Delta F \ge 0 \Rightarrow \text{直接接受}
\]

\[
\Delta F < 0 \Rightarrow P_{\text{accept}} = \exp\left(\frac{\Delta F}{T}\right)
\]

其中 \(T\) 为当前温度。随着迭代进行，温度按指数退火方式衰减：

\[
T_{k+1} = \rho T_k
\]

当前实现中的默认参数为：

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `initialTemperature` | 初始温度 \(T_0\) | 自动标定 |
| `finalTemperature` | 终止温度 | 0.05 |
| `coolingRate` | 降温系数 \(\rho\) | 0.97 |
| `iterationsPerTemp` | 每个温度的邻域迭代次数 | 40 |

当未显式指定 `initialTemperature` 时，代码会先从初始解附近采样若干个邻域解，统计其中“变差解”的典型适应度下降幅度，并令初始接受率接近 \(p_0=0.7\)。设采样得到的平均下降幅度为 \(\overline{\Delta F^-}\)，则：

\[
T_0 = \frac{\overline{\Delta F^-}}{-\ln p_0}, \qquad p_0 = 0.7
\]

其中：

\[
\overline{\Delta F^-}=\frac{1}{N}\sum_{i=1}^{N} |\Delta F_i|,\quad \Delta F_i<0
\]

该做法的目的，是让初始温度与当前适应度函数的真实量级对齐，避免在不同场景规模下出现“温度过高导致搜索过于随机”或“温度过低导致搜索过早冻结”的问题。

初始解不是完全随机生成，而是先按任务质量从高到低排序，再选取前 \(N_{\text{init}}\) 个候选任务作为初始基因：

\[
N_{\text{init}} = \min \left( \max \left( \left\lfloor \frac{N_{\text{targets}}}{3} \right\rfloor,\ 5N_{\text{sats}} \right),\ |taskPool| \right)
\]

邻域生成采用与遥感任务调度更贴近的 5 类操作：

| 邻域操作 | 作用 | 选择概率 |
| --- | --- | --- |
| `replace` | 用高质量候选替换当前任务 | 0.35 |
| `add` | 向当前解中加入高质量候选任务 | 0.25 |
| `remove` | 删除当前解中的低质量任务 | 0.15 |
| `swap_window` | 对同一卫星-目标切换不同访问窗口 | 0.15 |
| `swap_satellite` | 对同一目标切换执行卫星 | 0.10 |

该设计的含义是：SA 不是盲目交换基因顺序，而是围绕“替换差任务、补充优任务、切换成像窗口、切换执行卫星”来搜索更优的可行调度方案，更符合本课题的多约束成像调度场景。对于可被多颗卫星观测的同一目标，`swap_satellite` 可以重新分配执行者，从而释放原卫星的时间窗口给其他任务。

## 9. 配置层指标

### 9.1 总存储可成像上限

$$C_{\text{store}}=N_{\text{sats}}\cdot\left(\frac{S}{I}\right)$$

### 9.2 超订比

$$R_{\text{over}}=\frac{N_{\text{targets}}}{C_{\text{store}}}$$

来源：`my_example/configs/medium.yaml`，`my_example/configs/small.yaml`

| 符号 | 含义 |
| --- | --- |
| $C_{\text{store}}$ | 总存储折算的可成像数量上限 |
| $N_{\text{sats}}$ | 卫星数量 |
| $S$ | 单星存储容量 |
| $I$ | 单张图像大小 |
| $R_{\text{over}}$ | 超订比 |
| $N_{\text{targets}}$ | 目标数量 |

用途：用于描述场景压力大小，不直接参与调度求解。
