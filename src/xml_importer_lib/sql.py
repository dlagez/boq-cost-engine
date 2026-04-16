INSERT_IMPORT_BATCH_SQL = """
INSERT INTO cost_import_batch (
    batch_no,
    project_name,
    source_type,
    source_file_name,
    import_status,
    remark
) VALUES (%s, %s, %s, %s, %s, %s)
"""

INSERT_SINGLE_PROJECT_SQL = """
INSERT INTO cost_single_project (
    batch_id,
    seq_no,
    single_project_name,
    single_project_cost,
    division_amount,
    measure_amount,
    other_amount,
    regulation_amount,
    fee_amount,
    tax_amount,
    total_measure_amount,
    safe_civilized_amount,
    provisional_sum_amount,
    material_provisional_amount,
    specialty_provisional_amount,
    labor_amount,
    material_amount,
    machine_amount,
    equipment_amount,
    management_amount,
    profit_amount,
    risk_amount,
    construction_scale,
    construction_scale_unit,
    single_project_category_code,
    remark
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

INSERT_SINGLE_PROJECT_PROFILE_SQL = """
INSERT INTO cost_single_project_profile (
    single_project_id,
    attr_name,
    attr_value,
    sort_no
) VALUES (%s, %s, %s, %s)
"""

INSERT_UNIT_PROJECT_SQL = """
INSERT INTO cost_unit_project (
    single_project_id,
    unit_project_code,
    unit_project_name,
    unit_project_cost,
    specialty_category,
    level3_metric_code,
    division_amount,
    measure_amount,
    other_amount,
    safe_civilized_amount,
    regulation_amount,
    fee_amount,
    tax_amount,
    total_measure_amount,
    provisional_sum_amount,
    material_provisional_amount,
    specialty_provisional_amount,
    labor_amount,
    material_amount,
    machine_amount,
    equipment_amount,
    management_amount,
    profit_amount,
    risk_amount,
    professional_type_code,
    remark
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

INSERT_UNIT_PROJECT_EXTRA_SQL = """
INSERT INTO cost_unit_project_extra (
    unit_project_id,
    attr_name,
    attr_value,
    sort_no
) VALUES (%s, %s, %s, %s)
"""

INSERT_DIVISION_SQL = """
INSERT INTO cost_division (
    unit_project_id,
    division_code,
    division_name,
    level4_metric_code,
    division_total_amount,
    provisional_amount
) VALUES (%s, %s, %s, %s, %s, %s)
"""

INSERT_BOQ_ITEM_SQL = """
INSERT INTO cost_boq_item (
    division_id,
    seq_no,
    item_code,
    item_name,
    item_feature_desc,
    measure_unit,
    quantity,
    composite_unit_price,
    composite_amount,
    labor_unit_price,
    material_unit_price,
    machine_unit_price,
    management_unit_price,
    profit_unit_price,
    risk_unit_price,
    total_measure_unit_price,
    regulation_unit_price,
    fee_unit_price,
    tax_unit_price,
    labor_amount,
    material_amount,
    machine_amount,
    management_amount,
    profit_amount,
    risk_amount,
    total_measure_amount,
    regulation_amount,
    fee_amount,
    tax_amount,
    professional_type_code,
    unpriced_material_amount,
    labor_unit_price_desc,
    provisional_amount,
    level5_metric_code,
    remark
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

INSERT_BOQ_ITEM_QUOTA_SQL = """
INSERT INTO cost_boq_item_quota (
    boq_item_id,
    quota_code,
    quota_name,
    quota_unit,
    quantity,
    labor_unit_price,
    material_unit_price,
    machine_unit_price,
    management_unit_price,
    profit_unit_price,
    risk_unit_price,
    total_measure_unit_price,
    regulation_unit_price,
    fee_unit_price,
    tax_unit_price,
    composite_unit_price,
    composite_amount,
    labor_amount,
    material_amount,
    machine_amount,
    management_amount,
    profit_amount,
    risk_amount,
    total_measure_amount,
    regulation_amount,
    fee_total_amount,
    tax_amount,
    unpriced_material_amount,
    provisional_unit_price,
    provisional_amount,
    professional_type_code,
    remark
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s
)
"""

INSERT_RESOURCE_SUMMARY_SQL = """
INSERT INTO cost_resource_summary (
    batch_id,
    resource_type,
    resource_code,
    resource_name,
    resource_unit,
    unit_price,
    remark
) VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

INSERT_RESOURCE_USAGE_SQL = """
INSERT INTO cost_quota_resource_usage (
    quota_id,
    resource_summary_id,
    consumption_quota_content,
    consumption_adjust_coef
) VALUES (%s, %s, %s, %s)
"""
