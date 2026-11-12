---
name: "structure-prediction-analysis"
description: "蛋白质结构预测批量部署与结果分析技巧集（Mol-1/Protenix v2/OpenDDE；AF3 已退役为保险丝）。覆盖多卡部署、MSA 预计算+批量推理两阶段模式（本地 MMseqs2 server）、传输瘦身、以及大规模结果双轴四象限分析（有/无目标 epitope 两种模式）。Invoke when 用户要做结构预测批量推理、多卡部署、MSA 预计算、结果筛选分析（ipTM/姿态聚类/epitope 覆盖）时。"
---

# 结构预测与分析 (Structure Prediction & Analysis)

本 skill 固化 2026-09 MC2R/MC4R VNAR 设计项目实证 + **2026-11-05 主引擎 AF3→Mol-1 迁移**（13 体系切换验证: r(Mol-1,AF3) ipTM=-0.21 标度不兼容, Mol-1 四基准全面更强且 Apache-2.0 可商用, AF3 CC-BY-NC 退役为保险丝）。
所有命令与参数均有本机实证依据，标注 ⚠️ 的项使用前需再核对；标注 **[待校准]** 的项是 AF3→Mol-1 迁移后失效需重定的阈值。

## 0. 何时使用

- 需要对大量候选（几十~几百个 binder 序列）做结构预测批量推理
- 需要多卡并行部署 Mol-1 / Protenix / OpenDDE
- 需要分析大规模预测结果：置信度过筛、姿态收敛聚类、目标 epitope 覆盖筛选

## 1. 总体工作流：两阶段模式

```
阶段一 特征先行 (MSA/featurization)          阶段二 批量推理
┌─────────────────────────────┐        ┌──────────────────────────────┐
│ 同靶点候选共享 MSA/模板      │        │ 每 GPU 一个 runner 进程       │
│ 一次性算好, 嵌入输入 json    │  ───>  │ round-robin 分 job, 互不抢占  │
│ (binder 设计链用空 MSA)      │        │ XLA/TRiton 编译缓存复用       │
└─────────────────────────────┘        └──────────────────────────────┘
                    │
                    v  统一后处理 (第 4 节): 置信度 x 姿态 x epitope 三维判定
```

核心思想：**MSA 是同靶候选间的公共开销**——把 MSA/模板算一次复用到所有候选 json，
推理阶段每卡独立进程跑批量 job；编译产物（jax_cache 等）跨 job 复用。

## 2. Mol-1 批量推理（2026-11-05 起主引擎）

### 2.1 部署快照（已就绪）

| 项 | 值 |
|---|---|
| 仓库/环境 | `<WORKSPACE_ROOT>/Mol-1` + conda env `mol1` (py3.12, torch2.13+cu130) |
| 启动包装 | `bash <WORKSPACE_ROOT>/Mol-1/run_mol.sh <cmd>`（内置 MOL_ROOT_DIR/PATH/CUDA_HOME=12.8/本地 MSA API） |
| 权重 | `data/checkpoint/mol-1-base.pt` (2.3G, Apache-2.0 可商用) |
| 本地 MSA | `msa_server/` ColabFold 协议 MMseqs2 server（uniref30_2202 + colabfold_envdb_202108，共 615G 索引），127.0.0.1:8080/api，cron 守护自愈；`MOL_COLABFOLD_API` 注释掉即回退线上 |
| 诊断 | `bash run_mol.sh doctor` |

### 2.2 输入 JSON（mol dialect）与 MSA 策略

```json
[{"name": "cand_0001", "modelSeeds": [101, 202, "..."],
  "sequences": [
    {"proteinChain": {"id": ["A"], "count": 1, "sequence": "<binder>",
                      "unpairedMsaPath": "<query-only.a3m>"}},
    {"proteinChain": {"id": ["B"], "count": 1, "sequence": "<受体>",
                      "unpairedMsaPath": "<受体a3m>"}}]}]
```
- **MSA 语义与 OD/Protenix 系完全同源**（同代码）：任一链缺 MSA 路径（或不存在）→ 整 job 全链重搜；**binder 空 MSA 链必须给 query-only a3m**（`>query\n{seq}`，深度 1）实现静态使用；链 `id` 必须 list[str] 且 len==count
- 同靶候选**共享受体 MSA 文件路径**（不内嵌），binder 链 query-only——延续两阶段模式"特征先行"
- PDB/CIF → 输入 json：`mol json --input <cif> --out_dir <dir>`

### 2.3 批量推理命令（多卡每卡单进程）

```bash
CUDA_VISIBLE_DEVICES=<g> bash <WORKSPACE_ROOT>/Mol-1/run_mol.sh pred \
    -i <job_list.json> -o <outdir> \
    --use_template false --use_seeds_in_json true --use_msa true --sample 1
```
- ⚠️ **`--use_seeds_in_json true` 必带**：默认 seeds=101 忽略 JSON modelSeeds（2026-11-04 踩坑）
- **`--sample 1`**：sample 伪重复 ICC 实证（统计单位=seed，同预算 seeds×1.8-2）
- `--use_msa`：输入已带全 MSA 路径时无影响；binder 库批量建议显式 false + 预置 a3m（本地 server 免排队）
- 性能（4090 实测）：175tok ~62s/seed、644tok ~150s/seed；峰值显存 4.6-13GB，24G 卡单卡可并行 1-3 job

### 2.4 输出布局（mol layout，后处理按此解析）

```
<out>/<job>/seed_<s>/predictions/
    <job>_sample_<k>.cif                          # 结构, 样本按 ranking_score 降序 (sample_0 最优)
    <job>_summary_confidence_sample_<k>.json      # iptm/ptm/ranking_score/chain_plddt/has_clash...
```
⚠️ [待校准/待实证] ① summary 的 chain_pair_iptm 字段有无待确认（S3 三元 gate 依赖，无则从 full_data PAE 算）；② 链序是否 A=binder B=受体（AF3 实证 A=binder，Mol-1 未验）；③ 输出是否含近接触假象（AF3 无弛豫 2.0-2.5Å 近接触，Mol-1 待测——clash 硬剔 <1.5Å 沿用，<2.5Å 剔除判据 [待校准]）

### 2.5 部署坑（全部实踩）

| 坑 | 规避 |
|---|---|
| nvcc 版本 | 系统 /usr/local/cuda→11.5 不可用；CUDA_HOME=/usr/local/cuda-12.8（run_mol.sh 已封装） |
| ninja PATH | torch 扩展编译 subprocess 找 PATH 里的 ninja；用绝对路径调 mol 时 envs/mol1/bin 须在 PATH（run_mol.sh 已封装） |
| sm_89 警告 | doctor 报 RTX4090 "NOT SUPPORTED"——实为 sm_86 二进制兼容可跑，已实证 |
| 进程清理 | 本机存在外部进程清理（setsid 也被杀，无 OOM 痕迹）；长任务用工具托管后台或 nohup 前台快返回 + 30s 后 `nvidia-smi --query-compute-apps=pid` 验证上 GPU |
| MSA server 冷启动 | 重启后首查询慢（page cache 预热）属正常；跑一条热身序列 |

### 2.6 AF3 归档段（已退役→保险丝，触发条件见 workflow §7.5）

历史部署：官方源码版无 `--num_seeds`（seeds 全写 JSON modelSeeds）；`--num_diffusion_samples=1` 必带；权重 `/data1/PRODB3/models`；XLA jax_cache 复用。历史输出布局 `aneo100s`（§5 后处理仍支持，用于分析 AF3 存量数据）：`{out_root}/{target}_100s_c{NNNN}/seed-{s}_sample-{k}/` 下 `model.cif` + `summary_confidences.json`；顶层巨型 `{cand}_confidences.json` 传输时排除（151 候选 28GB→3.9GB）。AF3 标度历史判据锚点：聚类池下限 ipTM≥0.40 / 轴二高置信门 0.65 / S0.5 弃置线 0.4 复核线 0.65——**Mol-1 上全部 [待校准]**。

## 3. Protenix v2

本项目 Protenix 以两种形态使用：
1. **AnewOmni 管线内 cofold 验证**：候选生成后由 protenix 子进程做复合物预测验证，
   `--gpu_ids` 指定显卡；protenix server 冷启动显存低（按需加载）属正常启动序列
2. **独立预测**：用 `protenix-v2`（9/4 已验证跨模型续跑安全）
   ⚠️ 独立批量部署参数（MSA 预计算入口/多卡分发）以官方 `protenix --help` 与 docs 为准，本 skill 暂未固化

## 4. OpenDDE v1.1.1（<OPENDDE_DIR>）

Aureka 开源 Drug Design Engine（AF3 系扩散模型，Python 3.11-3.13，本地 venv 已装好）。

- **CLI 子命令**（`runner/cli.py` + `runner/batch_inference.py`）：
  - `doctor`：环境自检（先跑这个）
  - `msa` / `mt` / `prep`：**MSA/模板/预处理先行**（对应"先跑 MSA"阶段；需 HMMER/Kalign、数据库与网络，勿假设本机现成）
  - `pred` / `json`：批量推理（对应"再批量推理"阶段）
- **点分配置键**：`--model.N_cycle 4`、`--sample_diffusion.N_step 20`；
  列表参数逗号分隔 `--seeds 101,102`；布尔用小写 `true/false`
- **精度选择（2026-09-17 实测 A/B，VNAR+MC4R 378-token 复合体, RTX 4090）**：
  生产批量推理**用 `--dtype bf16`**（官方 CLI 参数，默认 fp32 需显式开启）。
  同 seed 下 bf16 vs fp32：全局全原子 RMSD 仅 0.352 Å（链内 0.17/0.39 Å），ΔipTM=0.003；
  而 fp32 换 seed 的采样噪声为 16.1 Å / ΔipTM=0.043 —— **精度偏移比采样噪声小 46 倍，可忽略**。
  收益：前向 47.4s→29.4s（**1.62x 加速**），显存峰值 8.28→7.90 GB（省 ~5%；短体系省得少，
  权重仍 fp32 驻留，O(N²) 激活随序列变长占比升高，长体系收益更大）。
  fp16/fp8 **不支持**（`INFERENCE_DTYPE_CHOICES=("bf16","fp32")`）；CC 7.x 显卡会强制回退 fp32
- **输出布局**：`<out>/<job_name>/seed_<seed>/predictions/` 下
  `*_sample_0.cif` + `*_summary_confidence_sample_0.json`（plddt/gpde/ptm/iptm/chain_*/ranking_score/has_clash）+ `*_full_data_*.json`
- 资产/权重：`$OPENDDE_ROOT_DIR`（checkpoint 在其下 `checkpoint/`）
- **远端服务器部署（2026-09-18 实证，CentOS 7 + 8×3090, rcdb@<REMOTE_HOST>）**：
  - 原生安装被 **glibc 2.17** 硬阻断（torch 2.7.1 只发 manylinux_2_28 轮子；conda-forge 的 libcudss/libcusolver 亦要求 `__glibc >=2.28`）→ 唯一路径是容器
  - **自建镜像**（官方 `aurekaresearch/opendde:v1` 在国内镜像站均不在白名单拉不到）：
    `nvidia/cuda:12.6.3-runtime-ubuntu24.04` 底座 + `pip install opendde[gpu]==1.1.1`（容器内 PyPI 快）→ 8.65GB
  - **驱动 550 (CUDA 12.4) 跑 CUDA 12.6 镜像**需 `-e NVIDIA_DISABLE_REQUIRE=1`（官方逃生门；
    torch cu126 轮子自带全套 CUDA 运行时库，实际只要求驱动 ≥525）
  - CentOS 7 已 EOL：yum base 源 404 须切 tuna `centos-vault/7.9.2009`；tuna 的 docker-ce.repo 实际指向官方站须改写 baseurl；nvidia repo 关 `repo_gpgcheck`
  - 运行时资产 3.1GB：checkpoint 从 hf-mirror 直下（`huggingface.co/aurekaresearch/OpenDDE/resolve/<revision>/...`，远端可达 2.4MB/s+）；common/ 4 文件同源（**不是 S3**，S3 直链 403）；SHA-256 对 `opendde/config/dependency_url.py` 的 ManagedAsset manifest 校验
  - 标准命令：`docker run --rm --gpus all --shm-size=4g -e OPENDDE_ROOT_DIR=/opendde_data -v <资产>:/opendde_data -v <out>:/output opendde:local2 opendde pred ...`
  - ⚠️ **GPU 注入三坑（2026-09-18 远端 3090 实踩，逐个排查才能全通）**：
    1. `--runtime nvidia` + `-e NVIDIA_VISIBLE_DEVICES=<idx|UUID>` 会注入设备但**不挂驱动用户态库**到预期路径——
       底座镜像自带的 compat 库 `/usr/local/cuda-12.6/compat/libcuda.so.560` 在 ldconfig 里排在宿主库前面，
       torch 拾取 compat 库 → GeForce 报 `Error 804: forward compatibility was attempted on non supported HW`
       （compat 仅支持数据中心卡）。`device_count()=1 但 is_available()=False` 是典型信号（NVML 路径能见卡、CUDA init 失败）
    2. **修复 = `--gpus "device=<UUID>"` + `-e LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:...`**
       （LD_LIBRARY_PATH 优先于 ldconfig 缓存，强制 dlopen 拾取宿主 libcuda 550）。
       `--runtime nvidia` 路径修不动，别再试。
       **变体（2026-09-21 远端B 实踩）**: 若注入目录里**同时**存在宿主 libcuda.so.550 与
       compat 副本 libcuda.so.560（两版本同目录），LD_LIBRARY_PATH 无法消歧 →
       **`-e LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libcuda.so.550.135` 钉死具体库**。
       新机判别法: 容器内 `find / -name "libcuda.so*"` 看注入目录里有几个版本
    3. runtime 底座**缺 gcc/g++/python3-dev** → Triton JIT 编译 `Failed to find C compiler` → 补装后又有
       Python.h 缺失编译失败 → 必须 `apt-get install gcc g++ python3-dev` 后 `docker commit` 成补丁镜像。
       诊断口诀：**先看 `output/ERR/{job}.txt`**；log 里 "Seed X completed in 2.1s" 全是秒失败假象
       （真实速率 399-token 复合体 3090 bf16 ≈ 54s/seed，首轮含 Triton 编译 ~2.5min）
  - 冒烟基准：9aa `--dtype bf16 --step 200 --cycle 10` 单样本 44.8s，plddt 93.1, has_clash=0
    ⚠️ 事后复盘：该冒烟实际可能跑在 CPU 上（9aa 太小未暴露 804），**冒烟必须用真实尺寸复合体并先验证 `torch.cuda.is_available()=True`**
- 输入 JSON 格式见 `docs/infer_json_format.md`（job list, entities: proteinChain/dnaSequence/rnaSequence/ligand/ion + covalent_bonds）；
  PDB/CIF → 输入 json 用官方子命令 `opendde json -i <cif> -o <dir>`（实测可用，转换后自行补 `modelSeeds`）
- **MSA 语义（源码 `runner/msa_search.py` 实证）**：`--use_msa true` 时 `need_msa_search` 只要发现**任一
  proteinChain 缺 pairedMsaPath/unpairedMsaPath（或路径不存在）→ `update_seq_msa` 把该 job 全部链的 MSA
  推翻重搜**（走 ColabFold 协议 MMseqs2 服务，连带把已提供路径的链一起重搜）。**空 MSA 链（如设计 binder）
  必须给 query-only a3m（深度 1，`>query\n{seq}`，msa_service_client 认可为合法 self MSA）**，
  使所有链路径齐备 → 日志出现 `do not need to update msa result, so return itself` 即静态使用成功
  （featurization 日志 `N_msa` 应等于受体 MSA 深度）。链 `id` 必须 **list[str] 且 len(id)==count**
  （`json_to_feature.build_full_atom_array` 校验），AF3 的字符串 id "A" 要包成 ["A"]
- **featurizer 字段兼容**：`opendde/data/msa/msa_featurizer.py` 同时支持内嵌 `unpairedMsa`（AF3 同名字段）与
  `unpairedMsaPath`；summary 字段 iptm/ptm/ranking_score/chain_pair_iptm 与 AF3 同名可直接复用管线
  （has_clash 是 bool，disorder≈AF3 fraction_disordered）
- 运行时安全项：`LAYERNORM_TYPE=torch` 默认；triangle kernel `auto/cuequivariance/torch` 保留 torch 回退
- 多卡：⚠️ 与 AF3 相同的"按卡分进程"模式可行，具体并发参数以 `docs/` inference 文档为准（未在本机固化验证）
- ⚠️ **部署坑（2026-09-17 实踩）**：本机 agent 沙箱的**后台执行会丢失 GPU 设备访问**，
  torch 静默回退 CPU——症状：进程 3700% CPU、`nvidia-smi` 无该进程、输出目录只有空 `ERR/`、跑数小时不出结果。
  **规避**：长推理任务用前台快返回方式拉起（`nohup ... > log 2>&1 & echo $!`），子进程继承前台环境的 GPU 访问；
  启动 30s 后用 `nvidia-smi --query-compute-apps=pid,used_memory` 验证进程已上 GPU，不在 GPU 上立即杀掉重来

## 5. 大规模结果分析：双轴四象限管线

主脚本 `<WORKSPACE_ROOT>/scripts/af3_dualaxis_postprocess.py`（配套 `build_region_cache.py`、`validate_epitope_side.py`）。**⚠️ 2026-11-05 迁移：主引擎改 Mol-1，脚本需加 `mol` 布局适配（待办）；判据体系中 AF3 标度绝对值对 Mol-1 失效，标 [待校准]**。

### 5.1 标准模式（无目标 epitope）

```bash
python3 af3_dualaxis_postprocess.py --target mc4r \
  --out-root <预测输出根> --input-dir <输入json目录> \
  --out <结果目录> --layout {mol,boltzgen,odesign,aneo100s,opendde} --workers 8
```

五种布局对应输入目录命名约定：
- **`mol`（Mol-1，2026-11-05 起主引擎）**：`{out_root}/{job}/seed_<s>/predictions/{job}_sample_<k>.cif + {job}_summary_confidence_sample_<k>.json`（seed 下划线 + predictions 子层、summary 复数带 sample 后缀）⚠️ 脚本适配待做（见 handoff-Mol-1.md）
- `boltzgen`：`{out_root}/boltzgen_{target}_boltzgen_{target}_{N}_100seed/seed-*_sample-*/`
- `odesign`：`{out_root}/{target}/{target}_odesign_{N}/seed-*_sample-*/`
- `aneo100s`：`{out_root}/{target}_100s_c{NNNN}/seed-{s}_sample-{k}/`——**seed 级文件名无前缀**
  （`model.cif`/`summary_confidences.json`），glob 用 `*summary_confidences.json` 兼容。
  ⚠️ 远端 AF3 输出顶层候选目录还有巨型 `{cand}_confidences.json`（全 PAE 矩阵，~1.4MB/候选×100 seeds≈21GB/151候选），
  瘦身传输时排除之，只取 seed 级 cif+summary 与顶层 `*_summary_confidences.json`（151 候选 28GB→3.9GB）
- `opendde`：`{out_root}/{name}/seed_{seed}/predictions/{name}_sample_0.cif + {name}_summary_confidence_sample_0.json`
  （seed 目录用下划线、summary 单数 confidence、cif 带任务名前缀——三处都和 AF3 不同）；
  输入 json 是 job list（转换脚本 `af3_to_opendde_json.py` 产出，binder 空 MSA 链自动生成 query-only a3m），
  后处理已适配双格式（list→proteinChain，dict→protein）
- **双引擎交叉比较**：`<WORKSPACE_ROOT>/scripts/cross_compare_af3_opendde.py`（⚠️ 迁移后 = Mol-1 结果目录 vs OD 结果目录）
  `--af3-dir <Mol-1结果目录> --od-dir <OpenDDE结果目录> --targets mc2r,mc4r --out <比较目录>`
  ——L1 seed 级配对 ipTM（两引擎同 seeds）+ L2 候选级 iptm_max/posdom_lb 相关性与 rank 漂移 + L3 象限交叉表 + 引擎分歧清单；自比较（两 dir 相同）必须输出全对角线 ρ=1.0 作管线自检。⚠️ samples/units/summary 三表 candidate 列格式不一（`mc2r_0056`/`0056`/`mc2r_100s_c0056`），脚本内已按 `{target}_{NNNN}` 归一化；Mol-1 布局需同样适配。**背景（2026-11-04 三方实测）**: r(Mol-1,AF3)=-0.21、r(Mol-1,OD)=+0.32、r(OD,AF3)≈0——跨引擎绝对 ipTM 不可比，交叉层只用相关性/rank/象限（相对量）

判据体系（实证校准；**[待校准] 项为 AF3 标度，Mol-1 迁移后须用首批候选库分布+已知对照重定**）：
- **统一聚类池** = ipTM≥0.40（观察带下限）**[待校准——Mol-1 实测 ipTM 均值偏低 ~0.28，沿用会把池掏空]** 且立体化学合格（min_dist≥1.5Å 硬剔沿用）的全部样本
  （姿态指纹是几何量与 ipTM 无关，勿按高置信先拆分支——会导致 B 类证据被静默丢弃）
- **聚类单元 = seed 级**：同 seed 多 sample 共享扩散噪声起点不独立，每 seed 取 ranking_score 最优者（Mol-1 sample 已降为 1，单元天然=seed）
- **姿态聚类**：site 指纹=受体界面残基集（重原子≤4.5Å）、pose 指纹=(binder,受体)接触对集；
  Jaccard 距离层次聚类（average linkage, 阈值 0.5）——**几何量，引擎无关，原样保留**
- **双轴**：轴一 = 主导簇占比的 Wilson 95% 下界 ≥0.5 判收敛（小样本自动降级：2/2→lb 0.34 不达标）——**保留**；
  轴二 = 主导簇内 ipTM≥0.65 单元占比 ≥0.5 判高置信 **[待校准——0.65 为 AF3 标度]**
- **四象限**：A=收敛且高置信(可用) / B=分散 / C=收敛但置信不足(序列优化对象) / D=池空
- **[待校准] 校准路径**：**按 S0.0 靶点校准面板执行**（protein-design-workflow §7.6，每换靶点/引擎/协议必做，~1-1.5h：阳性+阴性对照+候选库背景快照 → 本靶点阈值表）；C 类（收敛但置信不足→序列优化）对轴二门最敏感，校准前先出无门版报告再补门

### 5.2 targeted 模式（已知目标 epitope，`--epitope`）

```bash
python3 af3_dualaxis_postprocess.py --target mc2r \
  --out-root ... --input-dir ... --out ... --epitope ortho --workers 8
```

- E 集合规格：`ortho`（正构口袋）/ `accessible`（全胞外）/ 缓存段名（Extracellular/TM3…）/
  `u:a-b`（UniProt 区段自动映射构建体）/ `c:a-b`，逗号组合
- **先过滤后聚类**（filter-then-cluster）：每样本 gate **v2 = (epi_n=|R∩E|≥3 且 epi_frac=|R∩E|/|R|≥0.5) 或 (epi_n ≥ ceil(0.84·|E|))**——第二支为深插入逃生支
  （epi_recall 仅注记）；v1 纯 frac 门对深插姿态有足迹稀释偏见：宽骨架（VHH ~2500 Å²）塞入漏斗时非口袋接触随深度涨而分子|E|固定 → frac 天然贴 0.5；MC4R |E|=19 逃生阈 16、MC2R |E|=37 阈 32；实证 19/19 全覆盖样本 frac 仅 0.475 被 v1 误杀（gate v2 后 mc4r_3893 升双引擎 A）。过滤后池变小 → Wilson 下界自动惩罚小样本
- D 类拆分 `d_reason`：no_pool=池空 / no_epitope=有样本但无一覆盖目标 epitope
- `dom_epi_frac` 列 = 主导簇内过 gate 单元占比（标准模式下防"收敛在别处+少数打 epitope"被误读）

### 5.3 必备坑清单（每条都真踩过）

| 坑 | 教训 |
|---|---|
| **胞内假象** | AF3 无膜环境：GPCR 靶点高分样本可全打在 G 蛋白（胞内）位点。必须做膜侧几何判定（TM 段 PCA 法向 + 天然配体定胞外方向 + Kabsch 叠合投影 binder 质心，`validate_epitope_side.py`）；若普遍出现，要在**输入端**加环境约束重跑，而非只改后处理 |
| UniProt ID | MC4R=P32245 勿用 P33032(=MC5R)；拓扑标签用官方 `Topological domain`，勿按 TM 序号自推（ECL/ICL 会标反）；构建体非连续时须全局比对映射（`build_region_cache.py`） |
| 链序 | AF3 输出 A=binder、B=receptor（与序列长度无关，已实测）；⚠️ Mol-1 链序待实证（迁移后首批验证，见 §2.4） |
| clash 判据 | <2.5Å 对 AF3 无区分度（无物理弛豫）；只硬剔 <1.5Å |
| 聚类分支 | 勿按 ipTM 0.65 先拆互斥分支再聚类（B/C 证据错位）；用统一池+双轴解耦 |
| 输出目录 | rep_poses 按靶分子子目录（两靶共用 --out 时防互删） |
| Kabsch | 行向量约定 `M=U@D@Vt`, `t=qc-pc@M`（P@M+t≈Q）；实现后必须用受控测试验证残差 ~1e-14。**最低限度自检：同一文件对比 RMSD 必须为 0**（2026-09-17 实踩：diff 里重复加质心 yc，自检竟得 2.2 Å，排错半天；无自检的 RMSD 数字不可信） |
| **OD rep 姿态必须拉回本地实体** | OD 与 AF3 结构不同，交叉核验/效能分析需双引擎姿态；所有 OD 选出的 rep cif 一律 tar 流式拉回（远端打包→本地解压，软链目标 <REMOTE_MIRROR_DIR> 本机同路径落实体；远端A(<REMOTE_HOST>) 走 -p <REMOTE_PORT>+<DEPLOY_KEY_PATH>，远端B(<REMOTE_HOST2>) 同 key 直连），交付前 `ls -L` 验证（2026-10-15 用户规则，一次性清零 361 断链） |
| **BW/残基编号身份校验** | 跨编号体系取残基（构建体 vs UniProt vs BW）时**必须校验氨基酸身份**：同号残基常是不同残基（实测构建体147=ILE 被 UniProt R147 误用、构建体258=GLU 被当 W258，S1 微开关整表作废教训）；正确做法 = c2u 映射候选 + `get_resname()==期望值` 双重校验，都不符返回 None（region_cache 的 c2u 是桥接权威） |
| **CDR3 范围界定（⚠️ 用户长期规则）** | CDR3 边界必须**双法互检**：①锚定法——FR3 保守锚 YYC(A) 类起、FR4 锚 (W)G(GGG)/EGGG 类前止（VNAR 常见 YSCAQ/YYCAR 起、WGQ/WGE 前止）；②ANARCII 法——`<HOME>/anaconda3/bin/anarcii -t vnar`（transformer, v2.0.5, 本地 base env），IMGT 编号下 **CDR3 = 105–117**（含 111.x/112.x 插入码），118 起 FR4。Python API：`Anarcii(seq_type="vnar").number([seq])` 返回 dict（键 'Sequence 1'，含 numbering/score/chain_type），**方法名是 `number` 不是 `run`**；无 GPU 加 `-c/--cpu`；两法不一致以 ANARCII 为准并人工核对锚点。勿用传统 ANARCI（HMM 无鲨鱼 germline，识别不了 VNAR） |

## 6. 配套资产索引

| 资产 | 路径 | 作用 |
|---|---|---|
| **Mol-1 主引擎部署** | `<WORKSPACE_ROOT>/Mol-1`（入口 `run_mol.sh`；交接 `handoff-Mol-1.md`） | 2026-11-05 起主引擎（部署/坑/基准全记录） |
| **Mol-1 本地 MSA server** | `<WORKSPACE_ROOT>/Mol-1/msa_server/`（start_server.sh + ensure_server.sh cron 守护） | ColabFold 协议 MMseqs2（uniref30+envdb 615G 本地索引） |
| 双轴四象限分析 | `<WORKSPACE_ROOT>/scripts/af3_dualaxis_postprocess.py` | 标准模式 + targeted 模式主分析（⚠️ mol 布局适配待做） |
| 双引擎交叉 | `<WORKSPACE_ROOT>/scripts/cross_compare_af3_opendde.py` | Mol-1×OD L1-L3 交叉+分歧清单（⚠️ mol 布局适配待做） |
| 区域/正构口袋缓存 | `<WORKSPACE_ROOT>/scripts/build_region_cache.py` → `results/af3_dualaxis/region_cache_*.json` | 实验结构+UniProt 实证的正构口袋/可及残基 |
| 膜侧几何判定 | `<WORKSPACE_ROOT>/scripts/validate_epitope_side.py` | 参考系构建 + binder 胞外/膜/胞内投影 |
| 100-seed 批量输入 | `<WORKSPACE_ROOT>/scripts/build_af3_aneo_100seed_all.py` | 候选枚举→json 批量生成（AF3 dialect；Mol-1 需转换，bench_switch/build_inputs.py 可参考） |
| 传输瘦身 | `<WORKSPACE_ROOT>/scripts/build_af3_aneo_100seed_slim.py` | MSA/模板拆包 75x 压缩（Mol-1 用文件路径共享天然免瘦身） |
| OpenDDE 仓库 | `<OPENDDE_DIR>`（venv 已装, CLI: `.venv/bin/opendde`） | S1 正交 + S3 三元正交 |
| ~~AF3~~（退役保险丝） | `<AF3_DIR>` + 权重 `<AF3_WEIGHTS>` | 仅 workflow §7.5 触发条件时使用 |
| 引擎切换验证数据 | `<WORKSPACE_ROOT>/Mol-1/bench_switch/`（13 体系 Mol-1/OD/Prot-v1/AF3 四方对照 + reseed） | 阈值校准的实证底账 |

## 7. 交付包五道审核防线（⚠️ 2026-10-13 固化，筛选收官→人工核验前必过）

实战教训链：手抄象限笔误×2 + fasta 计数把注释行算入 + 交付集漏新晋 A + 代表结构断软链 + 新晋候选漏能量。**全部防线程序化，禁止目检代替**：

1. **序列层**：fasta 逐条对**设计输入 json 原文**比对（源头核对，不对中间汇总）；查重复 ID/序列
2. **标签层**：象限/lb/iptm **程序化直出自 dualaxis CSV**，禁止手抄进 fasta/报告；报告-CSV 交叉抽查，内部矛盾=笔误信号
3. **结构层**：结构内 binder 链序列 == fasta 逐条验证；交付前 `ls -L` 全软链实体化（指向远端的软链必断：远端A = `ssh -p <REMOTE_PORT> -i <DEPLOY_KEY_PATH> rcdb@<REMOTE_HOST>`，远端B = 同 key 直连 `rcdb@<REMOTE_HOST2>`）
4. **覆盖层**：gate/阈值变更后**所有批次同版本重跑**（漏批=旧指标混入，boltzgen 批漏 v2 致 3893 AF3 lb 低报 0.29）；交付集 vs 引擎全集数量对账；fasta 计数用 `startswith('>')` 勿用 `count('>')`
5. **能量层**：新晋候选立即同协议补能量（PyRosetta env 用 AnewOmni py3.10；Schrodinger 数值在 out.csv 第 2 行）；rank 全量重排；双前缀归一化 `'mc4r_'+m.split('mc4r_')[-1]` 防 mc2r 混入
6. **对照链身份层（⚠️ 2026-10-20 增，8QJ2 事故）**：从参考结构取链必须**坐标核验**——在原始沉积坐标中测该链到各伙伴最小距 + 对照 RCSB entity 注释（身份=位置+注释双确认）；**禁止文件名/长度/链字母启发式**。实例：8QJ2 链 N(138aa VHH 长度) 实为 Nb35(Gs 稳定体, 坐标坐 Gα/Gβ 3.1/2.5Å)，真 pN162=链 D(SEQRES 117aa, 坐标坐口袋 2.7Å)——按长度取链导致全部 "pN162 对照" 污染一周后才被发现。同族教训：S1 残基编号身份校验（构建体 147≠BW147）；**一切"身份"假设必须核验**

**交付包标准结构**：`shortlist_structures/` = `candidates.fasta`（header：ID+组名+各引擎象限(lb,iptm)+len+dG+rank+mMG+注记，**排序=实验优先级**）+ `od_rep/`+`af3_rep/`（一一对应平铺命名）+ `relaxed_pdb/`；全指标总表（档/骨架/双引擎/双能量/口袋特征）入 handoff。

## 8. GPCR 激动剂设计筛选管线 v4（⚠️ 2026-10-18 v3 对照实验校准 + 2026-11-05 Mol-1 迁移；完整版见 protein-design-workflow §7）

适用：设计 GPCR 功能性 binder（激动/拮抗）的全链路筛选。核心原则：**效价（激活/抑制）判定与亲和力判定分轨**——亲和看双轴置信，效价看三元 Gs 偶联，模板回声用消融排除。

### 8.1 级联结构（计算量从小到大，废候选早出局）— 2026-11-05 v4（主引擎 AF3→Mol-1，S0.5 OD→Mol-1；AF3 退役保险丝 workflow §7.5）

| 阶段 | 体系 | 引擎/seeds×samples | gate |
|---|---|---|---|
| **S0.0 靶点校准面板** | 阳性/阴性对照 + 背景快照 | Mol-1（定义见 protein-design-workflow §7.6，~1-1.5h） | 产出本靶点阈值表（本表全部 ipTM 门） |
| S0 生成 | **二元** (binder+受体) | boltzgen/AnewOmni | — |
| S0.5 triage | 二元 | **Mol-1 单引擎**，5s×1 | ipTM<弃置线弃；两线由 S0.0 阈值表给出（v3 的 0.4/0.65 系 OD 标度仅作分档结构参考） |
| S1 双轴 | 二元 | **Mol-1+OD 各 100s×1**（OD 免模板 AB 为主读数） | 姿态 dominant + gate v2（§5）⚠️ 聚类池下限与轴二门由 S0.0 阈值表给出 |
| S2 sanity | 二元 | — | 能量伪影只 flag 不排序（dG>+20 REU）；binder↔Gs 冲突预检 |
| S3 三元组装 | 5 链 (+Gα/Gβ/Gγ) | **Mol-1 ≥50s×1 主读（初期与 OD 20s×1 双读）** | **gate = 联合组装占比**（pair 门由对照面板给出；BC-only=伪影）+ 双引擎漂移名单互验 ⚠️ chain_pair_iptm 字段待确认 |
| S3.5 消融探查（可选） | 二元仅非活性模板 | 25s×1 | **单向 assay**：通过=强内在激活证据；失败不结论（α-MSH 也坍缩 0/125） |
| S4 能量+交接 | — | pyro+MMGBSA | 六道审核防线（§7，含对照链身份） |

#### 8.1.1 三元引擎使用细则（2026-10-21 真 pN162 平反后定稿；⚠️ 2026-11-05 迁移: AF3 行结论为历史参照，Mol-1 行待首批重验）

| 场景 | 引擎 | 状态 |
|---|---|---|
| 真实/已知序列（Nb35、天然 VHH、同源骨架） | **OD 三元完全可靠** | 真 pN162 5/5 摆口袋（1.8-2.0Å vs 实验 2.7Å）+ Nb35 5/5 摆 Gs 界面——两个已知先验场景全对 |
| de novo 设计候选主读数 | **AF3**（唯一可读 de novo binder 的引擎） | 但已知假阴性：真 pN162 判 0/20 → gate 对深插口袋型灵敏度不足，读数=协议内组装难易度（排序用），非激动检测器 |
| de novo 候选正交复核 | **OD 三元 20s×1** | 读数**必须配几何验证**（binder→各链实测距离）；漂移/纠缠名单与 AF3 互验（0094/0000 双引擎一致漂移=候选自身结合弱） |
| OD pair 读数 | ⚠️ chain_pair_iptm=姿态置信≠接触（源码级确认） | Nb35 AB 0.813 但距受体 16.6Å 实证；任何多链 pair 必须几何伴随 |
| 六链 (+Nb35 占位) | 可选未验证 | 4×24GB OOM（~1000 token 上限）；8 卡 CP 或 bf16 可重试 |

**seeds×samples 配置依据（2026-10-20 ICC 实证）**：sample 是伪重复（与 seed 共享 featurization+模型条件，仅重掷扩散噪声）——三元 RG pair ICC=0.993（组内 SD 0.018）、AB pair 组内 SD 0.010；二元 iptm/pairAB ICC=0.77-0.89（组内 SD 0.03）。**统计单位=seed**：sample 5→1 省 ~40-50%/seed（trunk 共享、diffusion 按 sample 计），同预算 seeds ×1.8-2。等预算模拟（p=0.4）：25s×1 的 CI 宽度 ≈ 5s×5 的一半。历史 5×5 批不重跑，按 seed 聚合即等价（sample 只贡献组内均值稳定性，P2-B seed 级 hard 投票口径不变）。

### 8.2 三元判读标尺（α-MSH 对照校准，2026-10-18 实测）

- **50% 高 pair = α-MSH 参考取值**（α-MSH 原生肽 SYSMEHFRWGKPV）——⚠️ 2026-10-20 降格：这是"指定协议下高置信联合组装预测的频率"，**不是生物学偶联概率，未校准 cAMP Emax/EC50**（AF3 官方明确区分结构置信度与生物学正确性）；判读措辞用"达到/未达 α-MSH 参考取值"，禁用"激动级/非激动"定性
- 判读档（探索性）：≥50% 达到天然肽参考 / 30-50% 接近 / <20% 远低（SHU 线性模拟地板，弱参照需注记）
- 高/低 pair 样本 TM6 差 ~1Å、corr(pair,S1)≈0.4-0.5 普适 → 构象选择信号真实（结构层面）；不外推为功能
- S1 复合分客观化：熵权法/CRITIC 定权 + simplex 扰动扫描（Kendall τ）+ 帕累托前沿双轨；cAMP≥12 点后切 logistic 回归

### 8.3 禁令（对照实验血泪换来的红线）

1. **混合活性/非活性模板的二元 S1 不得作效价结论**——受体构象跟随模板组成而非 binder（0094 实证：4 模板 S1 0.842，仅 6W25 时 0.324/TM6 9.0Å）。**消融（仅非活性模板）是单向 assay**：连 α-MSH 天然激动肽也坍缩（S1 0.308, TM6 8.7Å, 0/125）——二元无 Gs 时模板先验 >> 配体效应；消融失败不能证伪候选，仅"超出肽参照的激活尾巴"（如 0071 的 3/125, TM6 16.6Å vs α-MSH max 9.2Å）可作加分项
2. **多链预测接触数无区分力**——模型必须摆出所有链，"Gs 搭上去"是结构输出假象；读数用 chain_pair_iptm（模型对界面的自评），弱偶联体系的 binder-Gs 2-3Å"冲突"是链错位退化非真拮抗
3. **三元 S1 只记录不作 gate**——Gs 存在+活性模板把全员压到 0.77-0.80（基线 0.738）
4. 三元 Gs 链需配 MSA（当前裸序列压低绝对校准，相对比较不受影响）
5. 模拟肽对照须诚实注记：线性化丢环化/D-残基时，setmelo/shu 线性版仅差 1 残基，阴性对照弱；α-MSH 原生序列是唯一精确标尺；真肽用 CCD 编码
6. **结构现象不挂因果标签（2026-10-20 用户纠偏）**：pN162 二元不开 TM6 而 0094 开 ≠ "0094 独立稳定能力更强"——记为"结构观察（待实验解释）"；反模板下开启=特殊现象，非"强内在激活证据"；**跨构象叠合的重叠对数**（如 P2-A vs 6W25 的 <2.5Å 计数）内含受体 RMSD ~1.2Å 与构象差异，只作口袋占位指示，不作"真实稳定界面"证明（BSA 是预测复合物内部量，两指标分开报）；OD 三元失效不反证 AF3 功能判读可靠——引擎各自失效模式独立记录
7. **统计完善不补有效性缺口**：seed 级/CP 区间只压缩采样误差，模板/模型先验/构建体的系统偏差不可由此消除；δ=0.20 为惯例值无独立依据，非劣结论一律写"既定探索性界限下联合组装读数非劣；**功能待测**"；单一阳性对照（pN162）通过只证明"兼容该例"，不证明分类器特异性

### 8.4.1 停止规则与轮次完成标准（2026-10-20 用户定稿）

防"无限延长循环"（0/5 不能证无效 → 全部扩 seed → 区间仍重叠 → 再加对照再加指标）：**"未证实无效"≠"必须继续投入"**；筛选只需说明为何优先投入某些候选，不承担计算证明其余候选无效的义务。

- 冻结面板后**一轮汇总即收官**，不因区间仍宽自动追加 seeds/对照/指标
- 证据不足（CI 宽）的候选按"证据不足"记录并降优先级，而非补算
- **轮次完成标准（五条，达标即停）**：①候选身份与输入可追溯 ②主要结构伪影已检查（链错位/模板回声/跨构象叠合伪影）③已启动任务完成并汇总 ④实验面板冻结 ⑤所有功能结论保留为待验证假设
- v3 定位：**探索性结构分析工具**；功能定性（激动/拮抗）由实验回答（单独无 cAMP 响应≠拮抗剂；须同时看候选单独响应与对已知激动剂响应的调制）

### 8.4 协议细节

- 三元 5 链 json：binder(A)+受体(B, 复用二元 MSA/模板)+Gαs/Gβ/Gγ(C/D/E, 取自 7PIU 链 A/B/G)；顶层必须 dict + dialect alphafold3（list 会被判 Server 格式）
- 链级模板机制：templates 挂在 query 链下只约束该链，链间摆放靠模型先验
- 构造器 `build_ternary_inputs.py`（可 importlib 复用）；后处理 `ternary_postprocess.py`；对照 `build_ctrl_inputs.py`+`ctrl_postprocess.py`+`od_ctrl_postprocess.py`
- MC4R 模板集真相：7PIU(活性)+7F4D(MC1R+αMSH+Gs 活性)+6W25×2(非活性)

### 8.5 对照面板（靶点级一次性资产，非每批成本）

两级分离：**引擎级 QA**（跨靶点，MC4R 战役 2026-10-18/19 已定：OD 三元挤掉设计蛋白 binder、AF3 pair 有构象选择信号 corr≈0.45、多链接触数无区分力——结论永久复用，新靶点不重验）；**靶点级标尺**（每靶点一次性建立，~1-2h）：
- MC4R 版：α-MSH 三元（50% 高 pair 基准）+ SHU9119（阴性地板）+ pN162（蛋白激动剂，0.92 满格）+ 二元 TM6 基线（α-MSH/pN162 均不开 → 0094 型独家信号才有意义）
- 新靶点模板（如 GLP-1R）：天然激动肽（GLP-1(7-36)）定 pair 基准 + 经典拮抗肽（exendin(9-39)）定地板 + 二元 TM6 基线一次；无蛋白激动剂先例则该格缺位
- **重跑触发（仅此四项，日常批次零对照成本）**：①引擎/checkpoint 版本 ②seeds/samples 协议 ③MSA 策略（如补 Gs MSA 后须重定基准）④模板集/构建体变更。同协议同输入读数可复现（seed 控制），标尺不漂移
- **同型对照铁律**：肽对照不能定标蛋白 binder 的构象指标（本轮两次判读反转的根因）；肽线性化必须注记
