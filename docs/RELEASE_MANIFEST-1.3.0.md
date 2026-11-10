# GraphGen 1.3.0 release manifest

Status: released（tag 已推送 fork）；PMS 生产 pin 维持 1.2.1 不切换（pilot 窗口内不 re-pin）。

## Source identity

- Distribution: `graphg` 1.3.0
- Tag: `graphgen-fork-v1.3.0` → 发布线顶端（`release-v1.3.0` 推送为 `pms/main`）
- Merge 结构：fork 发布线 `fb7e392`（1.2.1 之后无代码演进）× 上游同步线 `45e39ab`（其父：`fb7e392` + upstream `7174d9d`）；合入提交 `36eb948`，31 处冲突逐文件语义裁决
- 上游 squash 线：#193 `11dcd91`（分区器集成测试修复）→ #194 `5689674`（版本化 prompt profile/输出门/并发上限/env 门控）→ #195 `7174d9d`（event_entity KG builder + event_join 分区器 + 事件抽取 profiles + 维护者评审修复）+ #194 评审 nit（PR #197 `7050883`/`ebfb176`）
- 版本线提交：`36eb948`（上游合并）→ `6a8da58`（#194 nits）→ `d34fcb6`（测试语义更新 + `_version.py` 1.3.0）→ `a5dbd91`（角色合并回归适配）→ `9ed54f6`（kuzu write_losses 显式覆盖）→ `ee34e7d`（1.2.x 直连兼容契约）
- Publication remote: `fork`（https://github.com/Leon-Algo/GraphGen.git）；upstream `origin`（InternScience/GraphGen）未修改；tag `graphgen-fork-v1.3.0` 发布前本地+远端均无占用（实测）
- PMS 生产 prompt 真源在 PMS 仓库 `configs/graphgen_profiles/`；fork 内置 `pms_policy.v2/v3` 与 1.2.1 树逐字节一致（4 文件 SHA256 实测全同）

## 合并裁决要点（60 files, +1508/−313）

- taken-theirs（上游重构）：MANIFEST.in、init_llm、schema_guided_extractor、event_join_partitioner、build_event_kg(+service)、event_contract 骨架、event_profile_loader、8 个生成器、llm_concurrency、prompt_profiles
- taken-ours / fork 资产回植：`support.py`（`：`显示修复）、setup.py（fork 身份）、generic_event.v1 prompt.zh.txt、openai_client（PMS_PATCHES #11）、partition_service（require_same_anchor 读取）
- 语义裁决：gates.py = 上游结构 + 3 个 PMS 门回植 + `non_empty_answer`；generate_service.py = fork `process()`（生成视图 + support 校验）+ 上游 `_GENERATOR_SPECS` 注册表；event_entity_kg_builder.py = 上游 builder + 中文字符串回植；base_generator.py = 上游 + support 透传；test_log.py = 双侧测试 union

## Test and smoke evidence

环境：隔离 release worktree（Python 3.12 依赖由 `workspace/graphgen_env/.venv` site-packages 提供；LLM 经 magpie 中转站 `group/cheap-first`）。

- 发行门禁测试 **104 passed**：`tests/test_event_profiles.py tests/test_package_profiles.py tests/test_support_edge_citations.py tests/test_event_profile_loader_regressions.py tests/unit_tests/ tests/integration_tests/models/partitioner/`
- 兼容修复后定向复验：event/support/profile-loader/kg_builder **14 passed**；PMS 兼容套件（policy generation + pool llm，graphgen 解析至 1.3.0 worktree）**37 passed, 1 skipped**
- pylint **10.00/10**（含合并后 `gates.py`、`generate_service.py`、`event_contract.py` 等全 CI 面）
- `git diff --check` — passed
- **真实端到端 smoke A（1.2.1 manifest 记录的缺口项①）**：官方示例管线 `examples/generate/generate_event_qa/`（非 PMS 数据 csv_demo.csv，event_entity + generic_event.v1 → event_join(require_same_anchor=False 默认) → multi_hop 生成），真 LLM 全链：kuzu 图 87 节点 / **24 事件节点** / 77 边 → **event_join 10 communities** → 10 条 QA 落盘（`output/<run>/generate/*.jsonl`）；容错计数器在真实流量可见（`event_number_not_grounded`、`response_not_json`）。日志 `/tmp/gg-release-v130/smoke/cache/logs/`
- **真实端到端 smoke B（缺口项②，默认路径不变性）**：官方默认示例 `generate_atomic_qa/`（kg_method 缺省=LightRAG、partition dfs、generate atomic）同数据真 LLM 全链成功：dfs 分区 **181 communities** → **180 条 QA** 落盘（Alpaca 官方默认格式 instruction/input/output），`GraphGen completed successfully`。日志 `/tmp/gg-release-v130/smoke-default/cache/logs/`
- PMS 兼容 smoke：见上 PMS 兼容套件；PMS 生产端到端 smoke 不在本版执行（生产 pin 不切换，无消费面变化）

## Build and clean-install evidence

- `uv build --out-dir /tmp/gg-release-v130/dist`（隔离 worktree）：
  - `graphg-1.3.0-py3-none-any.whl` SHA256 `763323b0b63ae5259a3c2fb53b10b330119269f019b4f2f45a864a83213cb9ef`
  - `graphg-1.3.0.tar.gz` SHA256 `98815f9b36c7c05d295eab8754138f192a59b280144b3f5c56143a38dae662d0`
- wheel 清单实测（274 files）：`gates.py`（4 门）、`event_profile_loader` + event_profiles 三套（example/generic/pms v1，含 pms `legacy_event_id: true`）、`profiles/example.v1/masked_fill_in_blank.json`（#194 nit）、`profiles/pms_policy.v2|v3/{atomic,multi_hop}.json`、`support.py`、`event_contract.py`、`graph_units`、`operators/judge/judge_service.py`、`masked_fill_in_blank_generator.py`、`kuzu_storage.py`（write_losses 覆盖）、`openai_client.py`、`generate_event_qa/` 官方示例 —— 全在包
- 干净 venv 实测（uv venv + requirements.txt 全量依赖 + `--no-deps` 装 wheel，无任何 PYTHONPATH 遮蔽）：`version==1.3.0`、`graphgen.__file__` 指向干净 site-packages、event profiles 三套加载（legacy_event_id 值正确）、GATES ⊇ 4 门、`pms_policy.v3` 模板加载（atomic SHA256 `c9b3ff215012aba5077f690f6ec958c2805941ef1cfc810598a3a1d14f6fb615`）、`event_node_name` legacy 锚点前缀契约 + `parse_extraction_response` 1.2.x 兼容签名、judge/graph_units/kuzu/openai_client/masked_fill_in_blank 生成器导入 —— **ALL CLEAN-INSTALL CHECKS PASSED**

## PMS production pin（不切换）

- `workspace/graphgen_env/pyproject.toml` rev 维持 `ffa16b850c4fb958d4833b5fd6fb5ef0340edb05`（1.2.1）；`uv.lock` 不动
- 理由：运行中 pilot 窗口内不做 re-pin；1.3.0 对 PMS 的差异已全部验证兼容（PMS 契约测试 + 直连 API 检查在 1.3.0 worktree 全绿），切换属 pilot 结束窗口的独立决策
- 届时关注点：`require_same_anchor`（生产配置显式 true，不受默认翻转影响）、`parse_extraction_response`/`event_node_name` 兼容契约（已保留）、CI Pylint 噪声根除

## Known limitations

见 `docs/RELEASE_NOTES-1.3.0.md`「兼容性」；1.2.1 已知边界（协议外裸写者、跨 namespace KV、NFS flock、非 POSIX fail-closed）随 merge 继承，未新增放宽。
