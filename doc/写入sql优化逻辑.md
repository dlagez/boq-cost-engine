# 写入 SQL 优化逻辑

## 目标

在不改变当前表结构和业务结果的前提下，降低 XML 导入写入 MySQL 的总耗时。

当前导入链路为：

1. 插入导入批次 `cost_import_batch`
2. 插入工料机汇总 `cost_resource_summary`
3. 逐层插入：
   - 单项工程 `cost_single_project`
   - 单项工程概况 `cost_single_project_profile`
   - 单位工程 `cost_unit_project`
   - 单位工程附加信息 `cost_unit_project_extra`
   - 分部分项 `cost_division`
   - 清单项 `cost_boq_item`
   - 子目组价 `cost_boq_item_quota`
   - 工料机含量 `cost_quota_resource_usage`

## 当前性能瓶颈

瓶颈不在 XML 解析，主要在数据库写入往返次数过多。

其中最明显的问题是：

- `cost_quota_resource_usage` 虽然用了 `executemany`
- 但调用粒度是“每个 quota 一次”
- 当前样例文件有 2266 个 `quota`
- 对应会触发大量小批量 SQL

这会导致：

- MySQL 网络往返次数过多
- 事务中存在大量小批量写入
- 单条写入成本在远端数据库场景下被放大

## 优化方案

### 第一阶段

先做最稳的一步，不改变主键生成和父子写入顺序：

- 保留 `single_project / unit_project / division / boq_item / quota` 的逐行插入
- 只优化 `cost_quota_resource_usage`
- 从“每个 quota 单独 executemany”
- 改成“全局缓冲，达到阈值后统一批量 flush”

### 实现方式

在导入过程里维护一个全局 `resource_usage_buffer`：

- 遍历每个 quota 的 `工料机含量表`
- 先追加到内存 buffer
- 当 buffer 行数达到阈值时，执行一次 `executemany`
- 导入结束后，再把剩余 buffer 做最后一次 flush

当前实现阈值：

- `RESOURCE_USAGE_BATCH_SIZE = 2000`

## 已落地实现

已在 `src/xml_importer_lib/service.py` 实现第一阶段优化。

关键调整：

- 新增 `RESOURCE_USAGE_BATCH_SIZE = 2000`
- 新增 `flush_resource_usages(cursor, rows)` 辅助函数
- `resource_usage` 不再按每个 quota 单独写库
- 改为：
  - 全局累计
  - 达到 2000 行批量写一次
  - 最后再 flush 一次剩余数据

## 为什么先只做这一项

因为这项收益高、风险低。

它不需要改变：

- 主键生成方式
- 父子层级依赖
- 唯一键约束逻辑
- 现有 SQL 结构

但能显著减少 `cost_quota_resource_usage` 的 SQL 调用次数。

## 后续可继续做的优化

### 第二阶段

把以下表也改成分块批量插入：

- `cost_boq_item_quota`
- `cost_boq_item`
- `cost_division`

### 第三阶段

如果要继续压缩时间，可以进一步考虑：

- 应用侧生成主键，摆脱对 `lastrowid` 的依赖
- 先批量插入，再按业务唯一键回查 ID
- staging table + merge
- 更细的批量阈值压测

## 结论

当前已经实现的优化是：

- `cost_quota_resource_usage` 全局分块批量写入

这是第一步优化，目标是先减少最显著的数据库写入往返次数，再决定是否继续做更大范围的批量化改造。
