-- Velocity Transactional Intelligence Engine
-- Snowflake foundation schema for file-first monthly intake.
--
-- Run this in the target database after selecting/creating the database:
--   USE DATABASE <database_name>;
--
-- This script is intentionally non-destructive. It creates schemas, an
-- internal landing stage, reusable file formats, raw file ledger tables,
-- contract registry tables, canonical core tables, marts, and output tables.

CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS out;

CREATE FILE FORMAT IF NOT EXISTS raw.csv_flexible
  TYPE = CSV
  FIELD_DELIMITER = ','
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 0
  NULL_IF = ('', 'NULL', 'NA', 'N/A')
  EMPTY_FIELD_AS_NULL = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
  TRIM_SPACE = TRUE;

CREATE FILE FORMAT IF NOT EXISTS raw.tsv_flexible
  TYPE = CSV
  FIELD_DELIMITER = '\t'
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 0
  NULL_IF = ('', 'NULL', 'NA', 'N/A')
  EMPTY_FIELD_AS_NULL = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
  TRIM_SPACE = TRUE;

CREATE STAGE IF NOT EXISTS raw.client_file_stage
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Internal landing stage for monthly client files before contract validation.';

CREATE TABLE IF NOT EXISTS config.client (
  client_id            STRING NOT NULL,
  client_name          STRING,
  institution_type     STRING,
  active_flag          BOOLEAN DEFAULT TRUE,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  updated_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS config.layout_contract (
  layout_contract_id   STRING NOT NULL,
  source_family        STRING NOT NULL,
  version              STRING NOT NULL,
  display_name         STRING,
  contract_body        VARIANT,
  active_flag          BOOLEAN DEFAULT TRUE,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  updated_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS config.layout_field_map (
  layout_contract_id   STRING NOT NULL,
  canonical_field      STRING NOT NULL,
  source_field         STRING,
  source_position      NUMBER,
  data_type            STRING,
  required_flag        BOOLEAN DEFAULT FALSE,
  transform_rule       STRING,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS config.validation_rule (
  validation_rule_id   STRING NOT NULL,
  layout_contract_id   STRING,
  source_family        STRING,
  rule_name            STRING NOT NULL,
  severity             STRING NOT NULL,
  rule_sql             STRING,
  threshold_value      STRING,
  active_flag          BOOLEAN DEFAULT TRUE,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS raw.file_batch (
  batch_id             STRING NOT NULL,
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  received_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  received_by          STRING,
  source_note          STRING,
  status               STRING DEFAULT 'received'
);

CREATE TABLE IF NOT EXISTS raw.file_object (
  file_id              STRING NOT NULL,
  batch_id             STRING,
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  source_family        STRING DEFAULT 'unknown',
  original_filename    STRING NOT NULL,
  storage_uri          STRING,
  content_hash         STRING,
  byte_size            NUMBER,
  row_count_raw        NUMBER,
  delimiter_guess      STRING,
  header_row_guess     NUMBER,
  layout_contract_id   STRING,
  load_status          STRING DEFAULT 'landed',
  status_reason        STRING,
  received_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  loaded_at            TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS raw.file_row_variant (
  file_id              STRING NOT NULL,
  row_number           NUMBER NOT NULL,
  raw_record           VARIANT,
  raw_text             STRING,
  loaded_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS raw.file_error (
  file_id              STRING NOT NULL,
  row_number           NUMBER,
  error_stage          STRING NOT NULL,
  severity             STRING NOT NULL,
  error_code           STRING,
  error_message        STRING,
  raw_record           VARIANT,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS stg.accounts (
  file_id              STRING,
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  account_id           STRING,
  customer_id          STRING,
  product_code         STRING,
  product_name         STRING,
  stat_code            STRING,
  business_flag        BOOLEAN,
  branch_id            STRING,
  date_opened          DATE,
  date_closed          DATE,
  avg_balance          NUMBER(18, 2),
  has_debit            BOOLEAN,
  reg_e_status         STRING,
  row_payload          VARIANT,
  loaded_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS stg.transactions (
  file_id              STRING,
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  transaction_date     DATE,
  account_id           STRING,
  transaction_type     STRING,
  amount_raw           STRING,
  amount_signed        NUMBER(18, 2),
  amount_abs           NUMBER(18, 2),
  direction            STRING,
  mcc_code             STRING,
  merchant_raw         STRING,
  terminal_location_1  STRING,
  terminal_location_2  STRING,
  terminal_id          STRING,
  merchant_id          STRING,
  institution          STRING,
  card_present         STRING,
  transaction_code     STRING,
  row_payload          VARIANT,
  loaded_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS core.accounts (
  client_id            STRING NOT NULL,
  account_id           STRING NOT NULL,
  customer_id          STRING,
  product_code         STRING,
  product_name         STRING,
  stat_code            STRING,
  business_flag        BOOLEAN,
  branch_id            STRING,
  date_opened          DATE,
  date_closed          DATE,
  avg_balance          NUMBER(18, 2),
  has_debit            BOOLEAN,
  reg_e_status         STRING,
  source_file_id       STRING,
  valid_from_period    STRING,
  valid_to_period      STRING,
  updated_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS core.transactions (
  client_id            STRING NOT NULL,
  transaction_id       STRING NOT NULL,
  account_id           STRING,
  transaction_date     DATE,
  amount_signed        NUMBER(18, 2),
  amount_abs           NUMBER(18, 2),
  direction            STRING,
  transaction_type     STRING,
  channel              STRING,
  mcc_code             STRING,
  merchant_raw         STRING,
  merchant_consolidated STRING,
  merchant_id          STRING,
  card_present         STRING,
  institution          STRING,
  transaction_code     STRING,
  source_file_id       STRING,
  loaded_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS mart.account_monthly (
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  account_id           STRING NOT NULL,
  spend                NUMBER(18, 2),
  swipes               NUMBER,
  active_flag          BOOLEAN,
  merchant_count       NUMBER,
  payroll_detected     BOOLEAN,
  external_financial_services_flag BOOLEAN,
  engagement_tier      STRING,
  balance_band         STRING,
  relationship_depth   NUMBER,
  updated_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS mart.merchant_monthly (
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  merchant_consolidated STRING NOT NULL,
  mcc_code             STRING,
  account_count        NUMBER,
  transaction_count    NUMBER,
  spend                NUMBER(18, 2),
  avg_ticket           NUMBER(18, 2),
  new_merchant_flag    BOOLEAN,
  competitor_category  STRING,
  updated_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS out.run (
  run_id               STRING NOT NULL,
  client_id            STRING NOT NULL,
  period               STRING NOT NULL,
  product              STRING,
  status               STRING,
  started_at           TIMESTAMP_NTZ,
  completed_at         TIMESTAMP_NTZ,
  source_batch_id      STRING,
  manifest_payload     VARIANT
);

CREATE TABLE IF NOT EXISTS out.section_result (
  run_id               STRING NOT NULL,
  section_id           STRING NOT NULL,
  status               STRING,
  result_payload       VARIANT,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS out.insight (
  insight_id           STRING NOT NULL,
  run_id               STRING NOT NULL,
  section_id           STRING,
  title                STRING,
  finding              STRING,
  opportunity_amount   NUMBER(18, 2),
  affected_accounts    NUMBER,
  confidence           STRING,
  recommended_action   STRING,
  evidence_payload     VARIANT,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS out.action_list (
  action_list_id       STRING NOT NULL,
  run_id               STRING NOT NULL,
  action_type          STRING,
  account_id           STRING,
  customer_id          STRING,
  priority_score       NUMBER(10, 4),
  reason               STRING,
  payload              VARIANT,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS out.artifact (
  artifact_id          STRING NOT NULL,
  run_id               STRING NOT NULL,
  artifact_type        STRING,
  artifact_uri         STRING,
  created_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
