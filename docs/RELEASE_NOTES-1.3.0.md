# GraphGen 1.3.0 release notes

- Distribution: `graphg` 1.3.0
- Base: fork `pms/main` `fb7e39297eceefcd0202ac61b16f3bf64c6e1420`（1.2.x 发布线顶端）× upstream `main` `7174d9d`（#195 squash 后顶端，含 #193 `11dcd91`、#194 `5689674`）；上游同步线经 `45e39ab` 汇聚后由 `36eb948` 合入发布线
- 发布线：`release-v1.3.0` → 推送 `pms/main`；upstream `origin`（InternScience/GraphGen）不修改
- 性质：MINOR——上游 squash 合并线全量吸收（三个已合并 PR + 维护者评审修复）+ #194 评审 nit + 1.2.x 兼容契约保留；PMS 生产 pin 暂不切换（见文末）

## 背景

PR #193/#194/#195 于 2026-11-08 全部被维护者 APPROVED 并 squash 合入 upstream main（`11dcd91`→`5689674`→`7174d9d`）。维护者在其 squash 中自行完成：移除未接线的 `support.py`、`require_same_anchor` 默认 True→False、build_event_kg 冗余 `event_member` 注入清理、新增 `examples/generate/generate_event_qa/`，并确立 pylint 10.00 为 CI 必过基线——fork 发布线（≈9.97）由此在上游 CI 持续 fail，即 11 月上旬 CI 失败邮件风暴的根因。1.3.0 = 发布线与上游的语义级合并，从根上消除该噪声并承接上游全部演进。

## 行为变更

| 变更 | 说明 | 来源 |
|---|---|---|
| `require_same_anchor` 默认 False | event_join 分区不再强制同锚点；生产配置显式 `true` 的行为不变（batch0005 两配置均显式声明，已核实） | 维护者 squash（#195） |
| event_entity 建图接线 | `EventEntityKGBuilder` 正式接入 BuildKGService（`kg_method: event_entity` + `event_profile` 显式引用，无隐式默认）；事件-实体星型图管线成为官方能力 | #195 |
| `parse_extraction_response` 签名 | 上游收紧为 `entity_types` 必填；**fork 侧恢复 1.2.x 可选默认 + 全策略参数省略时的 legacy PMS 回退**（builder 路径全显式传参不受影响；PMS 契约测试锁定该兼容） | #195 + fork 兼容缓冲 |
| `event_node_name` legacy 默认 | 上游默认 False；**fork 恢复默认 True**（锚点前缀 ID），builder 始终显式传 profile 值，上游行为不变 | #195 + fork 兼容缓冲 |
| prefill 重试归一化 | 续写式后端响应不以 `{` 开头时补 `{` 再解析 | #194 评审 nit（PR #197 内容吸收） |
| `example.v1` 补 `masked_fill_in_blank.json` | 官方评审指出的模板覆盖缺口 | #194 评审 nit（PR #197 内容吸收） |
| kuzu `write_losses` 显式覆盖 | 沿用基类 fail-closed（NotImplementedError），替代隐式继承以满足上游 pylint 语义（W0223） | 合并适配 |
| `_version.py` 1.3.0 | 并入 `d34fcb6`（test 更新同提交） | 版本提升 |

## fork 生产资产保留清单（合并冲突逐文件语义裁决）

- support 引用链：atomic/multi_hop 生成器 `parse_support` → GenerateService 生成视图 + `validate_support` 校验 → base_generator QA_pairs `support` 透传（`graphgen/models/generator/support.py` 保留于 fork 安装面）
- 三个 PMS 输出门：`pms_project_anchor` / `pms_contract_anchor` / `pms_contract_challenge` + 上游新增 `non_empty_answer`，注册表机制不变
- 中文事件描述模板（`：`冒号、锚点/事件参与者字符串）与 `prompt.zh.txt` event profiles
- `openai_client.py` PMS_PATCHES #11 畸形响应容忍（content=None/空 choices）
- `max_communities` loss 选题（#15）、kg reload 有界重试（#16）、`llm_concurrency` 生成并发上限（#194 内容）、env 门控 LLM 客户端

## 兼容性

- 默认 LightRAG + ECE + dfs/atomic 官方默认路径不变（真实管线 smoke 复核，见 manifest）
- `pms_policy.v2/v3` prompt 模板保持已发布字节（wheel 内 SHA256 实测一致）
- PMS 直连调用方（`event_contract` 契约测试）在 1.3.0 上全绿
- 生产 pin 维持 `ffa16b8`（1.2.1）不切换：运行中 pilot 窗口内不做 re-pin，待 pilot 结束窗口评估；届时需关注 `require_same_anchor` 显式值与 `parse_extraction_response` 新签名（PMS 侧唯一调用方为契约测试，已适配验证）

发布门禁与构建证据见 `docs/RELEASE_MANIFEST-1.3.0.md`。
