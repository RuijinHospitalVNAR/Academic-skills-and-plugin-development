---
name: "structure-prediction-analysis"
description: "蛋白质结构预测批量部署与结果分析技巧集（AF3/Protenix v2/OpenDDE）。覆盖多卡部署、MSA 预计算+批量推理两阶段模式、传输瘦身、以及 AF3 大规模结果双轴四象限分析（有/无目标 epitope 两种模式）。Invoke when 用户要做结构预测批量推理、多卡部署、MSA 预计算、AF3 结果筛选分析（ipTM/姿态聚类/epitope 覆盖）时。"
---

# 结构预测与分析 (Structure Prediction & Analysis)

本 skill 固化 2026-09 MC2R/MC4R VNAR 设计项目中实证过的结构预测批量部署与结果分析经验。
所有命令与参数均有本机实证依据，标注 ⚠️ 的项使用前需再核对。

## 0. 何时使用

- 需要对大量候选（几十~几百个 binder 序列）做结构预测批量推理
- 需要多卡并行部署 AF3 / Protenix / OpenDDE
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

## 2. AF3（官方源码版）批量推理

### 2.1 输入 JSON 规范（实测有效格式）

```json
{
  "name": "mc2r_100s_c0001",
  "modelSeeds": [87231, 87232, "...共 100 个"],
  "sequences": [
    {"protein": {"id": "A", "sequence": "<binder设计链>",
                 "unpairedMsa": "", "pairedMsa": "", "templates": []}},
    {"protein": {"id": "B", "sequence": "<受体>",
                 "unpairedMsa": "<5MB a3m>", "pairedMsa": "<20MB>", "templates": [...]}},
  ],
  "dialect": "alphafold3", "version": 1
}
```

- **官方源码版没有 `--num_seeds` flag** → 多 seed 全部写进 json 的 `modelSeeds` 列表（本项目用 87231..87330 共 100 个，seed 根沿用 2025 年 VANR_BH3 项目约定）
- `--num_diffusion_samples` 官方默认 5，**必须显式 =1**（否则磁盘与耗时 x5）
- binder 设计链（如 VNAR）**用空 MSA**（设计序列无同源，且省 25MB/条）；受体链 MSA/模板整段复用
- 权重路径 `--model_dir`（本项目 `<MODEL_DIR>`）
- 批量生成脚本参考：`scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)build_af3_aneo_100seed_all.py`（binder 从 model.pdb H 链提取、cofold-验证 gate=model.cif 存在、同靶序列去重、manifest.csv 台账）

### 2.2 传输瘦身（同靶批量场景必备）

同靶 N 份 json 中 unpairedMsa(4.8MB)+pairedMsa(20.5MB)+templates 全部重复 → 151 份 json 724MB。
做法（`build_af3_aneo_100seed_slim.py`）：三大字段拆成 6 个 blob 文件 + assemble.py，
slim 包仅 9.7MB，传到远端后由 assemble.py 重组还原。**传输量降 75 倍**。

### 2.3 多卡部署（round-robin 每卡单进程）

```bash
# 每卡一个 runner 脚本, job 均分 (7 卡: 22/22/22/22/21/21/21)
CUDA_VISIBLE_DEVICES=<GPU-UUID> python run_alphafold.py \
  --json_path=<job>.json --output_dir=2-outdir/ \
  --num_diffusion_samples=1 --model_dir=<MODEL_DIR> \
  > 3-logdir/batch_gpu$g.log 2>&1 &
```

- **用 UUID 而非编号绑卡**（编号会因掉卡重排；UUID 稳定）：
  `0=41a8314d, 2=8277e634, 4=cef1d233, 5=8d7c07fc(bc403), 6=8cac1199, 7=2c5fe720`
- ⚠️ 本机 GPU1(64c9e760)/GPU3(2efb78fa) 已物理移除/永久禁用；**GPU5 为 MD 任务专用勿占**
- 用卡前先 `nvidia-smi -L` 自检目标 UUID 存在

### 2.4 性能实测与编译缓存

- featurization（含 MSA 处理）：100 seeds ≈ 17min（~10s/seed）
- XLA 首次编译慢（gemm_fusion_dot 警告属正常），**配置 jax_cache 后续 job 走缓存**
- 粗估：单 job 100 seeds 2.5-5h（3090 级显卡），全量 151 job x 7 卡 ≈ 2.5-4.5 天

### 2.5 监控与输出布局

```bash
ssh -p <REMOTE_PORT> -i <deploy_key> user@<REMOTE_HOST> \   # 内网地址脱敏, 实机见本地 handoff
  'grep -c processing <logdir>/*_gpu0.log; ls <outdir>/ | wc -l; tail -3 <logdir>/*_gpu0.log'
```

输出布局（后处理按此解析）：
```
2-outdir/<候选>/<候选>.json 下:
  seed-<N>_sample-<M>/
    *_model.cif                    # 结构 (A=binder, B=receptor)
    *_summary_confidences.json     # iptm/ptm/ranking_score/has_clash/fraction_disordered/chain_pair_iptm
    *_confidences.json             # 全置信度矩阵
```

⚠️ 注意：AF3 **不做物理弛豫**，输出可直接含 2.0-2.5Å 近接触（连 ipTM 0.78 的好样本也有），
不能拿 <2.5Å 当剔除判据；仅 min_dist<1.5Å（物理互穿）才硬剔除。

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
- **远端服务器部署（2026-09-18 实证，CentOS 7 + 8×3090, user@<REMOTE_HOST>）**：
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
       `--runtime nvidia` 路径修不动，别再试
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

## 5. AF3 大规模结果分析：双轴四象限管线

主脚本 `scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)af3_dualaxis_postprocess.py`（配套 `build_region_cache.py`、`validate_epitope_side.py`）。

### 5.1 标准模式（无目标 epitope）

```bash
python3 af3_dualaxis_postprocess.py --target mc4r \
  --out-root <预测输出根> --input-dir <输入json目录> \
  --out <结果目录> --layout {boltzgen,odesign,aneo100s,opendde} --workers 8
```

四种布局对应输入目录命名约定（2026-09-18 实证）：
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
- **双引擎交叉比较**：`scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)cross_compare_af3_opendde.py --af3-dir <AF3结果目录> --od-dir <OpenDDE结果目录>
  --targets mc2r,mc4r --out <比较目录>`——L1 seed 级配对 ipTM（两引擎同 seeds）+ L2 候选级
  iptm_max/posdom_lb 相关性与 rank 漂移 + L3 象限交叉表 + 引擎分歧清单；自比较（af3-dir=od-dir）
  必须输出全对角线 ρ=1.0 作管线自检。⚠️ samples/units/summary 三表 candidate 列格式不一
  （`mc2r_0056`/`0056`/`mc2r_100s_c0056`），脚本内已按 `{target}_{NNNN}` 归一化

判据体系（全部实证校准过）：
- **统一聚类池** = ipTM≥0.40（观察带下限）且立体化学合格（min_dist≥1.5Å）的全部样本
  （姿态指纹是几何量与 ipTM 无关，勿按 0.65 先拆分支——会导致 B 类证据被静默丢弃）
- **聚类单元 = seed 级**：同 seed 多 sample 共享扩散噪声起点不独立，每 seed 取 ranking_score 最优者
- **姿态聚类**：site 指纹=受体界面残基集（重原子≤4.5Å）、pose 指纹=(binder,受体)接触对集；
  Jaccard 距离层次聚类（average linkage, 阈值 0.5）
- **双轴**：轴一 = 主导簇占比的 Wilson 95% 下界 ≥0.5 判收敛（小样本自动降级：2/2→lb 0.34 不达标）；
  轴二 = 主导簇内 ipTM≥0.65 单元占比 ≥0.5 判高置信
- **四象限**：A=收敛且高置信(可用) / B=分散 / C=收敛但置信不足(序列优化对象) / D=池空

### 5.2 targeted 模式（已知目标 epitope，`--epitope`）

```bash
python3 af3_dualaxis_postprocess.py --target mc2r \
  --out-root ... --input-dir ... --out ... --epitope ortho --workers 8
```

- E 集合规格：`ortho`（正构口袋）/ `accessible`（全胞外）/ 缓存段名（Extracellular/TM3…）/
  `u:a-b`（UniProt 区段自动映射构建体）/ `c:a-b`，逗号组合
- **先过滤后聚类**（filter-then-cluster）：每样本 gate = epi_n=|R∩E|≥3 且 epi_frac=|R∩E|/|R|≥0.5
  （epi_recall 仅注记）；过滤后池变小 → Wilson 下界自动惩罚小样本
- D 类拆分 `d_reason`：no_pool=池空 / no_epitope=有样本但无一覆盖目标 epitope
- `dom_epi_frac` 列 = 主导簇内过 gate 单元占比（标准模式下防"收敛在别处+少数打 epitope"被误读）

### 5.3 必备坑清单（每条都真踩过）

| 坑 | 教训 |
|---|---|
| **胞内假象** | AF3 无膜环境：GPCR 靶点高分样本可全打在 G 蛋白（胞内）位点。必须做膜侧几何判定（TM 段 PCA 法向 + 天然配体定胞外方向 + Kabsch 叠合投影 binder 质心，`validate_epitope_side.py`）；若普遍出现，要在**输入端**加环境约束重跑，而非只改后处理 |
| UniProt ID | MC4R=P32245 勿用 P33032(=MC5R)；拓扑标签用官方 `Topological domain`，勿按 TM 序号自推（ECL/ICL 会标反）；构建体非连续时须全局比对映射（`build_region_cache.py`） |
| 链序 | AF3 输出 A=binder、B=receptor（与序列长度无关，已实测） |
| clash 判据 | <2.5Å 对 AF3 无区分度（无物理弛豫）；只硬剔 <1.5Å |
| 聚类分支 | 勿按 ipTM 0.65 先拆互斥分支再聚类（B/C 证据错位）；用统一池+双轴解耦 |
| 输出目录 | rep_poses 按靶分子子目录（两靶共用 --out 时防互删） |
| Kabsch | 行向量约定 `M=U@D@Vt`, `t=qc-pc@M`（P@M+t≈Q）；实现后必须用受控测试验证残差 ~1e-14。**最低限度自检：同一文件对比 RMSD 必须为 0**（2026-09-17 实踩：diff 里重复加质心 yc，自检竟得 2.2 Å，排错半天；无自检的 RMSD 数字不可信） |

## 6. 配套资产索引

| 资产 | 路径 | 作用 |
|---|---|---|
| 双轴四象限分析 | `scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)af3_dualaxis_postprocess.py` | 标准模式 + targeted 模式主分析 |
| 区域/正构口袋缓存 | `scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)build_region_cache.py` → `results/af3_dualaxis/region_cache_*.json` | 实验结构+UniProt 实证的正构口袋/可及残基 |
| 膜侧几何判定 | `scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)validate_epitope_side.py` | 参考系构建 + binder 胞外/膜/胞内投影 |
| 100-seed 批量输入 | `scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)build_af3_aneo_100seed_all.py` | 候选枚举→json 批量生成 |
| 传输瘦身 | `scripts/ (插件仓库相对路径; 实机部署时替换为本机 scripts 目录)build_af3_aneo_100seed_slim.py` | MSA/模板拆包 75x 压缩 |
| OpenDDE 仓库 | `<OPENDDE_DIR>`（venv 已装, CLI: `.venv/bin/opendde`） | pred/msa/prep/doctor |
