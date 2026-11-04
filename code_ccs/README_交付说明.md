# F28P55 v16 — MBD 与 NPU 最终部署工程

交付日期：2026-11-03。入口模型：`buck_ADRC_MBD_NPU_24b.slx`。运行版本标识：`buck_npu_io_revision = 16`。

本目录只保留最终 v16 的应用源码、MBD 模型、配套 H15 模型资产、本次生成代码与固件，以及编译核验记录。原工程、旧版本实验目录和旧 CCS 工作区不作为依赖。

本次交付已在本目录完成**全量 MBD 生成编译与普通重复编译**。新增注释的 C/H 文件经词法单元比较，执行代码与原最终版一致；生成 HEX 与原最终 v16 的 SHA-256 相同。模型保存只更新本地依赖路径、视图状态和版本元数据，没有改算法与参数。未执行新的 DSP 下载或带载实验。

## 1. 编译与下载入口

在安装了相同依赖的 MATLAB R2025b 中，以本目录为当前文件夹执行：

```matlab
% 不要同时打开其他目录下的同名模型。
cd('C:\Users\34109\Desktop\delivery_file\F28P55_v16');
build_buck_npu
```

也可打开模型后点击“编译”；模型 InitFcn 和 PostCodeGenCommand 会加入依赖和后台服务，无需手改生成文件。构建为 Build，不自动下载或运行 DSP。

| 交付项 | 用途 |
|---|---|
| `buck_ADRC_MBD_NPU_24b.slx` | 唯一 MBD 模型入口 |
| `buck_ADRC_MBD_NPU_24b.out` | CCS 加载固件和符号的入口 |
| 同名 `.elf` | 与 `.out` 内容相同 |
| 同名 `.hex` | 本次生成的 Intel HEX 镜像 |
| `buck_ADRC_MBD_NPU_24b_ert_rtw/` | 本次生成 C/H、链接图、Makefile、优化对象等；需要时可从 MBD 重新生成 |
| 生成目录内 `CCS_Project/*.projectspec` | 当前机器环境的 CCS 工程描述；移动目录后先在新目录重新生成 |
| `buck_v16_observer_expressions.txt` | CCS Expressions 导入文件 |
| `NPU_build_log.txt` | 本次完整编译日志 |
| `verification/` | 重复编译日志、源码一致性、内存及产物校验记录 |

CCS 调试时加载本目录新 `.out` 及其符号，不要使用另一个工作区的旧镜像或旧地址。下载会复位 DSP；保持原有断功率、关闭栅极驱动的下载流程。

## 2. 工具链与路径

| 组件 | 本次编译环境 |
|---|---|
| MATLAB / Simulink / Embedded Coder | R2025b，`D:\Program Files\MATLAB\R2025b` |
| TI C2000 支持包 | 当前 R2025b 安装中的 `toolbox/c2b` |
| C2000Ware | `D:\ti\c2000\C2000Ware_26_02_00_00` |
| MBD 生成代码、链接器与 strict IO 编译器 | `D:\ti\ti-cgt-c2000_22.6.0.LTS` |
| 三个关键 C 文件的独立 O2 编译器 | `D:\ti\ccs1281\ccs\tools\compiler\ti-cgt-c2000_22.6.1.LTS` |
| CCS | 12.8.1，C2000 EABI |
| 模型库编译来源 | TI NNC 2.1.2，已编译 H15 `mod.a`，详见 `model_evidence/compilation_report.json` |

当前构建使用 `E:` 映射 MATLAB 安装目录，避开原工具链对带空格路径的处理问题。映射不复制 MATLAB，重启/登录上下文变化后可能失效。

在 MATLAB 命令行先执行 `system('subst')` 查看映射。如果 E: 已映射到当前 MATLAB 且 `isfile('E:\bin\matlab.exe')` 为真，不要重复创建。如果 E: 确认未被物理盘、网络盘或其他映射占用，再执行：

```matlab
[status,msg] = system('subst E: "D:\Program Files\MATLAB\R2025b"');
disp(msg);
assert(status==0 && isfile('E:\bin\matlab.exe'), 'MATLAB映射未建立');
```

`buck_npu_build_environment.m` 会核对映射版本。换电脑时需安装对应依赖，核对 E: 用途，并修改构建脚本中的 SDK/编译器安装位置；不可覆盖用途不明的驱动器。模型自身的源码/库路径会按模型所在目录自动更新。工具链和 MATLAB 软件本体不随包分发。

普通桌面仿真不会执行 C 层 NPU 推理；验证部署推理需使用板端金标和实际运行诊断。

## 3. 控制算法与接入位置

控制采样频率 30 kHz，1 tick ≈ 33.33 us。四相电流内环、PWM/ADC 配置和一阶 LADRC 电压外环保持最终版设置：参考 12 V，`wc=5000`，`wo=14000`，`b0=20000`，最终单相电流给定限幅 ±40 A。

控制中断主要流程：

```text
ADC 实际电压与四相电流
  → buck_npu_begin：负载观测、边沿确认、读取预约值
  → Voltage_ADRC：更新原 ESO / 计算原电流给定
  → buck_npu_apply_prediction：计算本周期前馈电流
  → 原给定 + 前馈 → 最终电流限幅
  → buck_npu_commit：保存真实给定与同周期 ESO 状态
  → 四路电流 PI → PWM CMPA 写入 → GPIO22 拉低
```

NPU 接入位于电压外环电流给定计算内部、最终限幅之前，不直接加到占空比。补偿输出是**每相电流 A**。实际 `data` 是相邻预测端点的扰动变化 `df`（V/s），不是归一化网络输出，也不是当前总扰动，不能再直接采用旧的 `(data-z2)/b0` 加法。

背景主循环调用 `buck_npu_service()`：复制历史窗口、标准化、启动 NPU、层推进、完成处理、时间配对。控制中断不调用 `tvmgen_default_run()` 或等待 NPU。CPU 仍承担预处理、驱动、观测和补偿计算，“硬件推理”不意味着 CPU 零开销。

## 4. 网络输入输出与时间契约

H15 输入为连续 8 个控制采样时刻、9 个物理通道：

`Vo, I1, I2, I3, I4, Vref, IREF, z2, Vin`。

电压单位 V，电流单位 A，z2 单位 V/s；IREF 为最终限幅后的每相给定，不乘四。归一化后按 NCHW `[1,12,8,1]` 排列，后三通道补零。网络输出接口为 `[1,4,1,1]`，应用使用第 0 通道，金标自检检查全部通道。

`ndp_model_io.c` 用均值 hi/lo 拆分及预存缩放倒数完成 FPU32 归一化，必须独立 `--fp_mode=strict` 编译。归一化残差恢复后，与**来源时刻**的 z2 相加，形成目标时刻总扰动预测。

H15 的目标始终为 `source_tick+15`，即 0.5 ms 后；不是完成时间后 15 tick，也不是 15 个负载周期。下一负载周期回放允许推理晚于预测目标本身完成，但必须赶上下一次预约交付截止，且 epoch/相位代次/端点一致。

`mod.a`、`tvmgen_default.h`、归一化和金标数据必须成套保留。模型权重未重训、未替换。预编译库方案不应再加入另一套生成的 `lib0.c/lib1.c`，以免重复定义。

## 5. 负载观测、相位与补偿交还

输出有效电容为 **180 µF**。观测器利用 `Iload = ΣIL - Cout*dVo/dt`，采用对齐的四点差分/电流均值及三点中值滤波；稳定平台学习、阈值穿越和连续确认抑制噪声。确认后回推物理边沿时刻，不能直接把确认时刻当作真实边沿。

上升和下降分别识别周期；标称支持 20–200 Hz（1500–150 tick），保留 ±12 tick 测时容差。未锁定时不补偿；学习不会因一帧尖峰反复重置有效事务。极窄占空比仍受最小边沿间隔、平台学习和端点距离限制，不能把频率范围理解为任意占空比都已验证。

每个极性保留独立事务。默认取真实边沿前 6 tick 与后 24 tick 的预测，求 `df=post-pre`，安排下一同类边沿。默认提前量 1 tick、平滑建立 2 tick，因此从预计边沿前 3 tick 开始建立。已锁存事务要先交付或作废，才能被下一事务替换；背景学习继续。

前馈初始值为 `clip(-alpha*df/b0, ±1 A)`。到预计边沿后，利用 ESO 相对边沿前状态的变化估计接管比例，经过滤波和单调约束减小前馈权重，避免 ESO 振铃使补偿重复增加。达到交还阈值归零。**最终 v16 不含固定 2 ms 或固定 20% 周期清零**，也不保持一个绝对预测值持续与当前 z2 相减。

## 6. 源码导航与注释

| 文件 | 重点说明 |
|---|---|
| `buck_npu.c/.h` | 中断与 main 分工、采样窗口、异步缓冲区所有权、时间戳、预测发布与自检 |
| `buck_load_observer.c/.h` | KCL 观测、滤波、平台学习、边沿回推和 20–200 Hz 周期识别 |
| `buck_npu_schedule_impl.h` / `buck_npu_schedule.h` | 上升/下降事务、端点配对、不可覆盖的预约交付；实现头在 buck_npu.c 内编译 |
| `buck_npu_compensation.c/.h` | 事件前馈幅值、合法性检查、smoothstep 建立与 ESO 交还 |
| `buck_npu_platform.c/.h` | 时钟、共享 RAM 权限、中断初始化和 Timer2 诊断 |
| `buck_npu_sdk_port.c` | 短 NPU ISR / 后台层推进分离、C28x 字寻址搬运；保留原 TI 许可 |
| `ndp_model_io.c/.h` | 输入布局、strict FP 标准化、输出恢复 |
| `buck_npu_sections.cmd` | 补充 Flash/GS RAM 分段；不能代替基准链接文件 |
| `buck_npu_timing.h` | 控制频率和周期准入范围 |
| `buck_npu_phase*.h` | 保留的相位诊断接口与实现，不应误删编译依赖 |
| `buck_npu_mbd_bridge.h` | 原给定/最终给定及实际补偿诊断接口 |
| `buck_NPU_MBD_workspace.mat` | 模型工作区定义及固件初值 |
| `NPU_v15.m`、`Voltage_ADRC_v15.m` | 当前模型 MATLAB Function 代码的可读副本；实际生成使用 `.slx` 内代码 |
| `buck_npu_post_codegen.m` | 自动补后台 main 服务、模拟引脚恢复、依赖去重与生成代码检查 |
| `buck_npu_compile_v15_objects.m` | 当前三个 C 文件独立 O2 编译，防止普通编译再生成重复对象 |

文件名中的 `v15` 是已验证接口和构建入口的兼容名称，文件内容属于当前最终 v16，不是另放了一套旧工程。勿仅凭名称删除。关键 C/H 已补充中文注释，按 UTF-8 打开。

## 7. 调试初值与判读

固件初值为 `enable=1`（控制复位）、`alpha=0`、`buck_npu_run_enable=0`。CCS 在线调参不会自动写回固件初值。

| 变量 | 含义 |
|---|---|
| `enable` | 1 复位、0 运行 |
| `alpha` | 补偿比例；0 取消补偿，后台推理由 run_enable 独立控制 |
| `buck_npu_run_enable` | 1 允许背景推理；0 关闭并撤销补偿准入 |
| `buck_load_observer.locked/period_ticks` | 周期锁定及实测周期，约 `30000/负载频率` |
| `buck_npu_delivery_count[0/1]` | 上升/下降事务实际交付计数 |
| `buck_npu_comp_applied_delta_i_a` | 最终限幅后真正进入控制的补偿电流 |
| `buck_npu_schedule_missed/delivery_timeout/fault` | 预约迟到、超时和故障 |
| `buck_ctrl_interval_*_cycles` | 相邻控制入口间隔，150 MHz 下正常约 5000 cycles；不是环路执行时间 |
| `buck_ctrl_late_intervals` | 现有阈值为 7500 cycles，零计数不等于保证每次满足 33.33 us 截止 |

GPIO22 记录控制路径入口高、末尾低，结合示波器测宽度和周期间隔。CCS 分行刷新非原子快照，短前馈脉冲可能被低速刷新漏看；同时检查交付计数、实际补偿量、时序与输出电压，不能只看 completed 计数。

## 8. 本次核验与复现

- 从空的交付工程开始生成代码，未复制原项目的 slprj、slxc 或旧编译产物。
- 全量编译成功，再次普通 `slbuild` 成功；没有通过屏蔽警告改动控制参数。
- 原有 single 参数量化/数据类型替代提示保留。它们是精度提示，与编译错误不同。
- 7 个关键 C/H 文件仅新增注释，词法单元保持相同。模型内算法与参数未改变。
- 原权重、工作区、模型头文件及归一化参数保持一致。当前优化对象均重新编译且无重复链接。
- 核对调用顺序、main 后台服务唯一性、NPU 共享内存分段、对齐及容量。
- `.out` 与 `.elf` 一致；交付 HEX 与原最终 v16 镜像相同。
- 本次未连接、复位、下载或启动 DSP，也未重新宣称带载性能。

标准库 Python 可执行只读核验：

```text
python verification/verify_delivery.py
```

`verification/release_checks.json` 保存本次结果；`verification/source_equivalence.json` 保存原源码和注释版哈希。`SHA256SUMS.txt` 是交付文件清单与完整性校验。清理缓存后首次编译会重新生成 slprj/slxc，属于正常行为。

## 9. 开源提交范围与第三方组件

本包提供最终部署应用 C/H 源码、MBD 模型、构建脚本、量化 ONNX、输入输出契约和固件，可供审阅及在相同依赖下重新编译部署程序。`model_evidence/` 的编译/量化报告来自模型交接时的原始记录，内含训练机器路径及当时的验证状态；不是本次交付编译的路径或板端测试结论。

**本包不等同于“训练—量化—编译全流程开源”。** 当前收到的最终 H15 模型交付资料没有训练脚本、训练权重 checkpoint 和 NNC 导出的完整模型 C 源码；模型计算以 `mod.a` 库提供。若组委会要求全程源码复现，仍需由训练方补齐与该 ONNX/库对应的最终源码、训练配置及必要数据获取说明，不能以旧 H1 或其他实验代码替代。

TI 文件保留原版权和许可声明。MATLAB、TI SDK/编译器及 NNC 按各自许可安装/使用；本包不替第三方授予许可证，也不擅自为团队代码指定开源许可证。对外发布时由团队确定授权及第三方可再分发范围。

## 10. 压缩包范围

同级 `F28P55_v16_最终交付.zip` 为正式提交包，排除 `slprj/`、`.slxc` 编译缓存和空日志。展开后的工程源码与本机通过编译的工程相同。桌面工程目录仍保留本次编译缓存；这些不是旧版本源码。`SHA256SUMS.txt` 对应压缩包内的文件（清单自身除外）。
