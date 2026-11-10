CREATE TABLE IF NOT EXISTS complaints(
  id TEXT PRIMARY KEY, complainant TEXT, subject TEXT, received_step INTEGER, channel TEXT);
CREATE TABLE IF NOT EXISTS crm_accounts(
  id TEXT PRIMARY KEY, account_name TEXT, tier INTEGER, contract TEXT,
  vulnerability TEXT, sector TEXT);
CREATE TABLE IF NOT EXISTS cases(
  id TEXT PRIMARY KEY, account TEXT, subject TEXT, status TEXT, complaints TEXT,
  opened_step INTEGER);
CREATE TABLE IF NOT EXISTS sla_clocks(
  id TEXT PRIMARY KEY, case_ref TEXT, queue TEXT, due_step INTEGER);
CREATE TABLE IF NOT EXISTS regulatory_referrals(
  id TEXT PRIMARY KEY, case_ref TEXT, account TEXT, scheme TEXT);
CREATE TABLE IF NOT EXISTS compensation_payments(
  id TEXT PRIMARY KEY, account TEXT, case_ref TEXT, amount REAL);
