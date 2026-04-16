# MySQL 表结构设计 PRD（工程造价数据归集）

## 1. 文档目的

基于当前提供的结构说明（覆盖 **5.2.7 ~ 5.2.15**，即表7~表15），输出一版可直接落库的 MySQL 表结构设计方案，用于支撑：

* 工程造价数据导入/归集
* 分层级数据存储（单项工程 → 单位工程 → 分部分项 → 清单项 → 子目组价 → 工料机含量）
* 后续查询、校验、导出、与标准文件一一映射
* 预留附加信息扩展能力，避免频繁改表

---

## 2. 当前设计范围

本次仅基于你提供的片段设计以下对象：

1. 单项工程基本信息表
2. 单项工程概况信息表
3. 单项工程附加信息表
4. 单位工程基本信息表
5. 单位工程附加信息表
6. 分部分项信息表
7. 分部分项工程量清单与计价表
8. 分部分项工程量清单项目子目组价表
9. 工料机含量表

同时，为了满足实际系统落库需求，补充两个必要基础表：

* **导入批次表**：记录一次数据文件/一次上报任务
* **工料机汇总表（占位版）**：因你当前片段里“工料机含量表”引用了“工料机表中的工料机ID”，但该表定义未提供，因此这里先补一版占位结构，后续可再细化

> 说明：如果你后面把表1~表6也补给我，我可以继续把整套库补全成完整版。

---

## 3. 设计原则

### 3.1 分层建模

采用树状主从关系建模：

* 导入批次

  * 单项工程

    * 单项工程概况
    * 单项工程附加信息
    * 单位工程

      * 单位工程附加信息
      * 分部分项

        * 清单与计价项

          * 子目组价

            * 工料机含量

### 3.2 标准字段与业务字段分离

所有业务实体统一增加以下标准字段：

* `id`：主键
* `batch_id`：归属导入批次
* `created_at` / `updated_at`
* `is_deleted`：逻辑删除

### 3.3 编码字段保留原值

虽然部分规范里写的是 Integer，但凡是 **分类编码、项目编码、单位工程编码、指标编码**，建议统一用 `varchar` 存储，原因：

* 便于保留前导 0
* 兼容未来编码规则变化
* 与外部标准文件对接更稳

### 3.4 金额与数量精度分开

建议：

* 金额、单价、合价：`decimal(18,2)`
* 工程量、数量、系数、含量：`decimal(18,6)`

### 3.5 预留扩展能力

概况、附加信息采用 **KV 表** 设计，避免频繁 DDL 变更。

### 3.6 导入优先策略（按方案 A 落地）

为优先跑通 XML 主链路导入，本版将字段分为两类：

* **入库必填字段**：XML 中稳定出现、且用于建立层级关系或核心业务记录的字段，保留 `NOT NULL`
* **增强字段**：标准中要求但 XML 样例中不稳定出现、可后续补齐的字段，统一先改为 **可空**

本版先改为可空的字段包括：

* `cost_single_project.construction_scale_unit`
* `cost_single_project.single_project_category_code`
* `cost_unit_project.level3_metric_code`
* `cost_unit_project.professional_type_code`
* `cost_division.level4_metric_code`
* `cost_boq_item.level5_metric_code`

这类字段在导入时允许为空，后续可通过字典映射、规则补全或二次治理任务完善。

---

## 4. 逻辑关系图

```text
cost_import_batch
  └── cost_single_project
        ├── cost_single_project_profile
        ├── cost_single_project_extra
        └── cost_unit_project
              ├── cost_unit_project_extra
              └── cost_division
                    └── cost_boq_item
                          └── cost_boq_item_quota
                                └── cost_quota_resource_usage
                                      └── cost_resource_summary
```

---

## 5. 表清单

| 表名                            | 说明               |
| ----------------------------- | ---------------- |
| `cost_import_batch`           | 导入批次表            |
| `cost_single_project`         | 单项工程基本信息表        |
| `cost_single_project_profile` | 单项工程概况信息表        |
| `cost_single_project_extra`   | 单项工程附加信息表        |
| `cost_unit_project`           | 单位工程基本信息表        |
| `cost_unit_project_extra`     | 单位工程附加信息表        |
| `cost_division`               | 分部分项信息表          |
| `cost_boq_item`               | 分部分项工程量清单与计价表    |
| `cost_boq_item_quota`         | 分部分项工程量清单项目子目组价表 |
| `cost_resource_summary`       | 工料机汇总表（占位）       |
| `cost_quota_resource_usage`   | 工料机含量表           |

---

## 6. 表结构设计

## 6.1 导入批次表 `cost_import_batch`

### 设计目的

用于记录一次完整的数据归集任务，方便区分不同招标/投标文件、版本、来源文件。

### 建议字段

| 字段               | 类型           | 说明                       |
| ---------------- | ------------ | ------------------------ |
| id               | bigint       | 主键                       |
| batch_no         | varchar(64)  | 批次号，业务唯一                 |
| project_name     | varchar(255) | 项目名称/任务名称                |
| source_type      | varchar(32)  | 来源类型，如 tender/bid/manual |
| source_file_name | varchar(255) | 源文件名                     |
| import_status    | varchar(32)  | 导入状态                     |
| remark           | varchar(500) | 备注                       |
| created_at       | datetime     | 创建时间                     |
| updated_at       | datetime     | 更新时间                     |
| is_deleted       | tinyint(1)   | 逻辑删除                     |

---

## 6.2 单项工程基本信息表 `cost_single_project`

### 设计说明

对应标准里的“表7 单项工程基本信息表”。

### 唯一约束建议

* 同一批次下 `seq_no` 唯一

### 建议字段

| 字段                           | 类型            | 说明                    |
| ---------------------------- | ------------- | --------------------- |
| id                           | bigint        | 主键                    |
| batch_id                     | bigint        | 归属批次                  |
| seq_no                       | int           | 序号                    |
| single_project_name          | varchar(255)  | 单项工程名称                |
| single_project_cost          | decimal(18,2) | 单项工程造价                |
| division_amount              | decimal(18,2) | 分部分项合计                |
| measure_amount               | decimal(18,2) | 措施项目合计                |
| other_amount                 | decimal(18,2) | 其他项目合计                |
| regulation_amount            | decimal(18,2) | 规费合计                  |
| fee_amount                   | decimal(18,2) | 费用合计                  |
| tax_amount                   | decimal(18,2) | 税金合计                  |
| total_measure_amount         | decimal(18,2) | 总价措施项目合计              |
| safe_civilized_amount        | decimal(18,2) | 安全文明施工费合计             |
| provisional_sum_amount       | decimal(18,2) | 暂列金额合计                |
| material_provisional_amount  | decimal(18,2) | 材料暂估价合计               |
| specialty_provisional_amount | decimal(18,2) | 专业工程暂估价合计             |
| labor_amount                 | decimal(18,2) | 人工费合计                 |
| material_amount              | decimal(18,2) | 材料费合计                 |
| machine_amount               | decimal(18,2) | 机械费合计                 |
| equipment_amount             | decimal(18,2) | 设备费合计                 |
| management_amount            | decimal(18,2) | 管理费合计                 |
| profit_amount                | decimal(18,2) | 利润合计                  |
| risk_amount                  | decimal(18,2) | 风险费合计                 |
| construction_scale           | decimal(18,6) | 建设规模                  |
| construction_scale_unit      | varchar(32)   | 建设规模单位（可空，导入阶段允许缺失）   |
| single_project_category_code | varchar(32)   | 单项工程分类编码（可空，导入阶段允许缺失） |
| remark                       | varchar(500)  | 备注                    |
| created_at                   | datetime      | 创建时间                  |
| updated_at                   | datetime      | 更新时间                  |
| is_deleted                   | tinyint(1)    | 逻辑删除                  |

---

## 6.3 单项工程概况信息表 `cost_single_project_profile`

### 设计说明

对应“表8 单项工程概况信息表”，适合做 KV 扩展表。

| 字段                | 类型           | 说明     |
| ----------------- | ------------ | ------ |
| id                | bigint       | 主键     |
| single_project_id | bigint       | 单项工程ID |
| attr_name         | varchar(128) | 名称     |
| attr_value        | text         | 内容     |
| sort_no           | int          | 排序号    |
| created_at        | datetime     | 创建时间   |
| updated_at        | datetime     | 更新时间   |
| is_deleted        | tinyint(1)   | 逻辑删除   |

### 唯一约束建议

* `uk_single_profile(single_project_id, attr_name)`

---

## 6.4 单项工程附加信息表 `cost_single_project_extra`

与概况信息表同结构，用于预留扩展字段。

| 字段                | 类型           | 说明     |
| ----------------- | ------------ | ------ |
| id                | bigint       | 主键     |
| single_project_id | bigint       | 单项工程ID |
| attr_name         | varchar(128) | 名称     |
| attr_value        | text         | 内容     |
| sort_no           | int          | 排序号    |
| created_at        | datetime     | 创建时间   |
| updated_at        | datetime     | 更新时间   |
| is_deleted        | tinyint(1)   | 逻辑删除   |

---

## 6.5 单位工程基本信息表 `cost_unit_project`

### 设计说明

对应“表10 单位工程基本信息表”。

### 唯一约束建议

* 同一单项工程下 `unit_project_code` 唯一

### 建议字段

| 字段                           | 类型            | 说明                    |
| ---------------------------- | ------------- | --------------------- |
| id                           | bigint        | 主键                    |
| single_project_id            | bigint        | 单项工程ID                |
| unit_project_code            | varchar(64)   | 单位工程编码                |
| unit_project_name            | varchar(255)  | 单位工程名称                |
| unit_project_cost            | decimal(18,2) | 单位工程造价                |
| specialty_category           | varchar(64)   | 专业类别                  |
| level3_metric_code           | varchar(32)   | 三级指标分类编码（可空，导入阶段允许缺失） |
| division_amount              | decimal(18,2) | 分部分项合计                |
| measure_amount               | decimal(18,2) | 措施项目合计                |
| other_amount                 | decimal(18,2) | 其他项目合计                |
| safe_civilized_amount        | decimal(18,2) | 安全文明施工费合计             |
| regulation_amount            | decimal(18,2) | 规费合计                  |
| fee_amount                   | decimal(18,2) | 费用合计                  |
| tax_amount                   | decimal(18,2) | 税金合计                  |
| total_measure_amount         | decimal(18,2) | 总价措施项目合计              |
| provisional_sum_amount       | decimal(18,2) | 暂列金额合计                |
| material_provisional_amount  | decimal(18,2) | 材料暂估价合计               |
| specialty_provisional_amount | decimal(18,2) | 专业工程暂估价合计             |
| labor_amount                 | decimal(18,2) | 人工费合计                 |
| material_amount              | decimal(18,2) | 材料费合计                 |
| machine_amount               | decimal(18,2) | 机械费合计                 |
| equipment_amount             | decimal(18,2) | 设备费合计                 |
| management_amount            | decimal(18,2) | 管理费合计                 |
| profit_amount                | decimal(18,2) | 利润合计                  |
| risk_amount                  | decimal(18,2) | 风险费合计                 |
| professional_type_code       | varchar(32)   | 专业类型编码（可空，导入阶段允许缺失）   |
| remark                       | varchar(500)  | 备注                    |
| created_at                   | datetime      | 创建时间                  |
| updated_at                   | datetime      | 更新时间                  |
| is_deleted                   | tinyint(1)    | 逻辑删除                  |

---

## 6.6 单位工程附加信息表 `cost_unit_project_extra`

| 字段              | 类型           | 说明     |
| --------------- | ------------ | ------ |
| id              | bigint       | 主键     |
| unit_project_id | bigint       | 单位工程ID |
| attr_name       | varchar(128) | 名称     |
| attr_value      | text         | 内容     |
| sort_no         | int          | 排序号    |
| created_at      | datetime     | 创建时间   |
| updated_at      | datetime     | 更新时间   |
| is_deleted      | tinyint(1)   | 逻辑删除   |

---

## 6.7 分部分项信息表 `cost_division`

### 设计说明

对应“表12 分部分项信息表”。

| 字段                    | 类型            | 说明                    |
| --------------------- | ------------- | --------------------- |
| id                    | bigint        | 主键                    |
| unit_project_id       | bigint        | 单位工程ID                |
| division_code         | varchar(64)   | 分部工程编号                |
| division_name         | varchar(255)  | 分部工程名称                |
| level4_metric_code    | varchar(32)   | 四级指标分类编码（可空，导入阶段允许缺失） |
| division_total_amount | decimal(18,2) | 分部工程合计                |
| provisional_amount    | decimal(18,2) | 暂估价合计                 |
| created_at            | datetime      | 创建时间                  |
| updated_at            | datetime      | 更新时间                  |
| is_deleted            | tinyint(1)    | 逻辑删除                  |

### 唯一约束建议

* `uk_unit_division_code(unit_project_id, division_code)`

---

## 6.8 分部分项工程量清单与计价表 `cost_boq_item`

### 设计说明

对应“表13 分部分项工程量清单与计价表”。

### 设计要点

* `seq_no` 保留源文件行序
* `labor_unit_price_desc` 使用 `text`，因为原始格式可能是多个人工单价拼接

### 建议字段

| 字段                       | 类型            | 说明                    |
| ------------------------ | ------------- | --------------------- |
| id                       | bigint        | 主键                    |
| division_id              | bigint        | 分部分项ID                |
| seq_no                   | int           | 序号                    |
| item_code                | varchar(64)   | 项目编码                  |
| item_name                | varchar(255)  | 项目名称                  |
| item_feature_desc        | text          | 项目特征描述                |
| measure_unit             | varchar(32)   | 计量单位                  |
| quantity                 | decimal(18,6) | 工程量                   |
| composite_unit_price     | decimal(18,2) | 综合单价                  |
| composite_amount         | decimal(18,2) | 综合合价                  |
| labor_unit_price         | decimal(18,2) | 人工费单价                 |
| material_unit_price      | decimal(18,2) | 材料费单价                 |
| machine_unit_price       | decimal(18,2) | 机械费单价                 |
| management_unit_price    | decimal(18,2) | 管理费单价                 |
| profit_unit_price        | decimal(18,2) | 利润单价                  |
| risk_unit_price          | decimal(18,2) | 风险费单价                 |
| total_measure_unit_price | decimal(18,2) | 总价措施单价                |
| regulation_unit_price    | decimal(18,2) | 规费单价                  |
| fee_unit_price           | decimal(18,2) | 费用单价                  |
| tax_unit_price           | decimal(18,2) | 税金单价                  |
| labor_amount             | decimal(18,2) | 人工费合价                 |
| material_amount          | decimal(18,2) | 材料费合价                 |
| machine_amount           | decimal(18,2) | 机械费合价                 |
| management_amount        | decimal(18,2) | 管理费合价                 |
| profit_amount            | decimal(18,2) | 利润合价                  |
| risk_amount              | decimal(18,2) | 风险费合价                 |
| total_measure_amount     | decimal(18,2) | 总价措施合价                |
| regulation_amount        | decimal(18,2) | 规费合价                  |
| fee_amount               | decimal(18,2) | 费用合价                  |
| tax_amount               | decimal(18,2) | 税金合价                  |
| professional_type_code   | varchar(32)   | 专业类型编码                |
| unpriced_material_amount | decimal(18,2) | 未计价材料合价               |
| labor_unit_price_desc    | text          | 人工单价描述                |
| provisional_amount       | decimal(18,2) | 暂估合价                  |
| level5_metric_code       | varchar(32)   | 五级指标分类编码（可空，导入阶段允许缺失） |
| remark                   | varchar(500)  | 备注                    |
| created_at               | datetime      | 创建时间                  |
| updated_at               | datetime      | 更新时间                  |
| is_deleted               | tinyint(1)    | 逻辑删除                  |

### 唯一约束建议

* `uk_division_seq_no(division_id, seq_no)`

---

## 6.9 子目组价表 `cost_boq_item_quota`

### 设计说明

对应“表14 分部分项工程量清单项目子目组价表”。

| 字段                       | 类型            | 说明      |
| ------------------------ | ------------- | ------- |
| id                       | bigint        | 主键      |
| boq_item_id              | bigint        | 清单项ID   |
| quota_code               | varchar(64)   | 定额编号    |
| quota_name               | varchar(255)  | 定额名称    |
| quota_unit               | varchar(32)   | 定额单位    |
| quantity                 | decimal(18,6) | 数量      |
| labor_unit_price         | decimal(18,2) | 人工费单价   |
| material_unit_price      | decimal(18,2) | 材料费单价   |
| machine_unit_price       | decimal(18,2) | 机械费单价   |
| management_unit_price    | decimal(18,2) | 管理费单价   |
| profit_unit_price        | decimal(18,2) | 利润单价    |
| risk_unit_price          | decimal(18,2) | 风险费单价   |
| total_measure_unit_price | decimal(18,2) | 总价措施单价  |
| regulation_unit_price    | decimal(18,2) | 规费单价    |
| fee_unit_price           | decimal(18,2) | 费用单价    |
| tax_unit_price           | decimal(18,2) | 税金单价    |
| composite_unit_price     | decimal(18,2) | 综合单价    |
| composite_amount         | decimal(18,2) | 综合合价    |
| labor_amount             | decimal(18,2) | 人工费合价   |
| material_amount          | decimal(18,2) | 材料费合价   |
| machine_amount           | decimal(18,2) | 机械费合价   |
| management_amount        | decimal(18,2) | 管理费合价   |
| profit_amount            | decimal(18,2) | 利润合价    |
| risk_amount              | decimal(18,2) | 风险费合价   |
| total_measure_amount     | decimal(18,2) | 总价措施合价  |
| regulation_amount        | decimal(18,2) | 规费合价    |
| fee_total_amount         | decimal(18,2) | 费用总价    |
| tax_amount               | decimal(18,2) | 税金合价    |
| unpriced_material_amount | decimal(18,2) | 未计价材料合价 |
| provisional_unit_price   | decimal(18,2) | 暂估单价    |
| provisional_amount       | decimal(18,2) | 暂估合价    |
| professional_type_code   | varchar(32)   | 专业类型编码  |
| remark                   | varchar(500)  | 备注      |
| created_at               | datetime      | 创建时间    |
| updated_at               | datetime      | 更新时间    |
| is_deleted               | tinyint(1)    | 逻辑删除    |

---

## 6.10 工料机汇总表（占位） `cost_resource_summary`

### 设计说明

你提供的“工料机含量表”里出现了“汇总材料ID”，并说明要关联到“工料机表中的工料机ID”，但该工料机表定义当前未给出。

为了能先把数据库结构串起来，这里先补一张基础占位表，后续拿到标准定义后再细化字段。

| 字段            | 类型            | 说明                                          |
| ------------- | ------------- | ------------------------------------------- |
| id            | bigint        | 主键                                          |
| batch_id      | bigint        | 批次ID                                        |
| resource_type | varchar(32)   | 资源类型：material/labor/machine/equipment/other |
| resource_code | varchar(64)   | 工料机编码                                       |
| resource_name | varchar(255)  | 工料机名称                                       |
| resource_unit | varchar(32)   | 单位                                          |
| unit_price    | decimal(18,2) | 单价（可选）                                      |
| remark        | varchar(500)  | 备注                                          |
| created_at    | datetime      | 创建时间                                        |
| updated_at    | datetime      | 更新时间                                        |
| is_deleted    | tinyint(1)    | 逻辑删除                                        |

---

## 6.11 工料机含量表 `cost_quota_resource_usage`

### 设计说明

对应“表15 工料机含量表”。

| 字段                        | 类型            | 说明           |
| ------------------------- | ------------- | ------------ |
| id                        | bigint        | 主键           |
| quota_id                  | bigint        | 子目组价ID       |
| resource_summary_id       | bigint        | 汇总材料ID/工料机ID |
| consumption_quota_content | decimal(18,6) | 消耗量定额含量      |
| consumption_adjust_coef   | decimal(18,6) | 消耗量定额含量调整系数  |
| created_at                | datetime      | 创建时间         |
| updated_at                | datetime      | 更新时间         |
| is_deleted                | tinyint(1)    | 逻辑删除         |

---

## 7. 索引设计建议

## 7.1 主外键索引

所有外键字段均建立普通索引：

* `batch_id`
* `single_project_id`
* `unit_project_id`
* `division_id`
* `boq_item_id`
* `quota_id`
* `resource_summary_id`

## 7.2 业务唯一索引

```text
cost_import_batch.uk_batch_no(batch_no)
cost_single_project.uk_batch_seq_no(batch_id, seq_no)
cost_single_project_profile.uk_single_profile(single_project_id, attr_name)
cost_single_project_extra.uk_single_extra(single_project_id, attr_name)
cost_unit_project.uk_single_unit_code(single_project_id, unit_project_code)
cost_unit_project_extra.uk_unit_extra(unit_project_id, attr_name)
cost_division.uk_unit_division_code(unit_project_id, division_code)
cost_boq_item.uk_division_seq_no(division_id, seq_no)
```

---

## 8. 推荐 MySQL DDL（首版）

```sql
CREATE TABLE cost_import_batch (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    batch_no VARCHAR(64) NOT NULL,
    project_name VARCHAR(255) DEFAULT NULL,
    source_type VARCHAR(32) DEFAULT NULL,
    source_file_name VARCHAR(255) DEFAULT NULL,
    import_status VARCHAR(32) DEFAULT 'INIT',
    remark VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_batch_no (batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导入批次表';

CREATE TABLE cost_single_project (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    batch_id BIGINT NOT NULL,
    seq_no INT NOT NULL,
    single_project_name VARCHAR(255) NOT NULL,
    single_project_cost DECIMAL(18,2) NOT NULL DEFAULT 0,
    division_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    measure_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    other_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    regulation_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    fee_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_measure_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    safe_civilized_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    provisional_sum_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    specialty_provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    labor_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    machine_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    equipment_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    management_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    profit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    risk_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    construction_scale DECIMAL(18,6) NOT NULL DEFAULT 0,
    construction_scale_unit VARCHAR(32) DEFAULT NULL,
    single_project_category_code VARCHAR(32) DEFAULT NULL,
    remark VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_batch_seq_no (batch_id, seq_no),
    KEY idx_batch_id (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单项工程基本信息表';

CREATE TABLE cost_single_project_profile (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    single_project_id BIGINT NOT NULL,
    attr_name VARCHAR(128) NOT NULL,
    attr_value TEXT NOT NULL,
    sort_no INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_single_profile (single_project_id, attr_name),
    KEY idx_single_project_id (single_project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单项工程概况信息表';

CREATE TABLE cost_single_project_extra (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    single_project_id BIGINT NOT NULL,
    attr_name VARCHAR(128) NOT NULL,
    attr_value TEXT NOT NULL,
    sort_no INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_single_extra (single_project_id, attr_name),
    KEY idx_single_project_id (single_project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单项工程附加信息表';

CREATE TABLE cost_unit_project (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    single_project_id BIGINT NOT NULL,
    unit_project_code VARCHAR(64) NOT NULL,
    unit_project_name VARCHAR(255) NOT NULL,
    unit_project_cost DECIMAL(18,2) NOT NULL DEFAULT 0,
    specialty_category VARCHAR(64) NOT NULL,
    level3_metric_code VARCHAR(32) DEFAULT NULL,
    division_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    measure_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    other_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    safe_civilized_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    regulation_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    fee_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_measure_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    provisional_sum_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    specialty_provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    labor_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    machine_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    equipment_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    management_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    profit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    risk_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    professional_type_code VARCHAR(32) DEFAULT NULL,
    remark VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_single_unit_code (single_project_id, unit_project_code),
    KEY idx_single_project_id (single_project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单位工程基本信息表';

CREATE TABLE cost_unit_project_extra (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    unit_project_id BIGINT NOT NULL,
    attr_name VARCHAR(128) NOT NULL,
    attr_value TEXT NOT NULL,
    sort_no INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_unit_extra (unit_project_id, attr_name),
    KEY idx_unit_project_id (unit_project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单位工程附加信息表';

CREATE TABLE cost_division (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    unit_project_id BIGINT NOT NULL,
    division_code VARCHAR(64) NOT NULL,
    division_name VARCHAR(255) NOT NULL,
    level4_metric_code VARCHAR(32) DEFAULT NULL,
    division_total_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_unit_division_code (unit_project_id, division_code),
    KEY idx_unit_project_id (unit_project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分部分项信息表';

CREATE TABLE cost_boq_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    division_id BIGINT NOT NULL,
    seq_no INT NOT NULL,
    item_code VARCHAR(64) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    item_feature_desc TEXT NOT NULL,
    measure_unit VARCHAR(32) NOT NULL,
    quantity DECIMAL(18,6) NOT NULL DEFAULT 0,
    composite_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    composite_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    labor_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    machine_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    management_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    profit_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    risk_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_measure_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    regulation_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    fee_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    tax_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    labor_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    machine_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    management_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    profit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    risk_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_measure_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    regulation_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    fee_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    professional_type_code VARCHAR(32) NOT NULL,
    unpriced_material_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    labor_unit_price_desc TEXT NOT NULL,
    provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    level5_metric_code VARCHAR(32) DEFAULT NULL,
    remark VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_division_seq_no (division_id, seq_no),
    KEY idx_division_id (division_id),
    KEY idx_item_code (item_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分部分项工程量清单与计价表';

CREATE TABLE cost_boq_item_quota (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    boq_item_id BIGINT NOT NULL,
    quota_code VARCHAR(64) NOT NULL,
    quota_name VARCHAR(255) NOT NULL,
    quota_unit VARCHAR(32) NOT NULL,
    quantity DECIMAL(18,6) NOT NULL DEFAULT 0,
    labor_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    machine_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    management_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    profit_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    risk_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_measure_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    regulation_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    fee_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    tax_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    composite_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    composite_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    labor_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    material_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    machine_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    management_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    profit_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    risk_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    total_measure_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    regulation_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    fee_total_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    unpriced_material_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    provisional_unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    provisional_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
    professional_type_code VARCHAR(32) NOT NULL,
    remark VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    KEY idx_boq_item_id (boq_item_id),
    KEY idx_quota_code (quota_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分部分项工程量清单项目子目组价表';

CREATE TABLE cost_resource_summary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    batch_id BIGINT NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    resource_code VARCHAR(64) DEFAULT NULL,
    resource_name VARCHAR(255) NOT NULL,
    resource_unit VARCHAR(32) DEFAULT NULL,
    unit_price DECIMAL(18,2) DEFAULT NULL,
    remark VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    KEY idx_batch_id (batch_id),
    KEY idx_resource_code (resource_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工料机汇总表';

CREATE TABLE cost_quota_resource_usage (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    quota_id BIGINT NOT NULL,
    resource_summary_id BIGINT NOT NULL,
    consumption_quota_content DECIMAL(18,6) NOT NULL DEFAULT 0,
    consumption_adjust_coef DECIMAL(18,6) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    KEY idx_quota_id (quota_id),
    KEY idx_resource_summary_id (resource_summary_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工料机含量表';
```

---

## 9. 关键校验规则建议

## 9.1 单项工程层

* 投标数据文件中的 `seq_no` 必须与招标文件一致
* 同一批次内不允许重复 `seq_no`

## 9.2 单位工程层

* `unit_project_code`、`unit_project_name` 应与招标数据一致
* 同一单项工程下 `unit_project_code` 不允许重复

## 9.3 分部分项层

* 必须有且仅有一级分部（这条更多属于业务校验，建议放应用层处理）

## 9.4 清单项层

* `labor_unit_price_desc` 应按标准格式校验
* 金额类字段不可为负数
* 编码类字段需校验是否符合标准字典

## 9.5 导入容错策略

* 对 `construction_scale_unit`、`single_project_category_code`、`level3_metric_code`、`professional_type_code`、`level4_metric_code`、`level5_metric_code` 允许空值入库
* 空值不视为导入失败，仅标记为“待补齐字段”
* 后续可通过标准字典、规则映射或补录流程进行完善

---

## 10. 我建议你下一步这样落地

### 方案 A：先按主链路可导入版本建库（本版采用）

适合你现在先开发 XML 导入、解析、查询接口的场景。

本版已按该方案处理：

* 主链路先跑通
* XML 中缺失但标准要求的增强字段改为可空
* 后续再通过字典表、治理任务或补录流程补齐

### 方案 B：再补一层标准字典表

如果后面要做更严格的数据治理，可以再补：

* 专业类型字典表
* 建设规模单位字典表
* 指标分类字典表（三级/四级/五级）
* 导入校验结果表

---

## 11. 待确认项

以下内容在你当前材料里还不完整，建议后续补充：

1. 表1~表6 的定义
2. “工料机表”正式字段
3. 专业类别、专业类型、指标分类是否有统一字典源
4. 是否需要区分招标版 / 投标版 / 对比版数据
5. 是否需要记录原始 Excel 行号、sheet 名称、来源文件版本

---

## 12. 结论

这版设计的核心思路是：

* **层级清晰**：符合你当前标准片段的结构
* **可落地**：DDL 可直接建表
* **可扩展**：概况/附加信息走 KV，不容易改崩
* **利于导入**：每层都有明确父子关系，适合解析后分批写入

如果要继续迭代，建议下一版直接补三部分：

1. 外键约束版 DDL
2. 标准字典表设计
3. 导入任务表 / 导入错误明细表 / 校验结果表
