CREATE TABLE IF NOT EXISTS applicants(
  id TEXT PRIMARY KEY, supplier_name TEXT, legal_form TEXT, category TEXT,
  expected_annual_value REAL, insurance_expiry_step INTEGER,
  bank_account_holder TEXT, existing_master_id TEXT);
CREATE TABLE IF NOT EXISTS sanctions_register(
  id TEXT PRIMARY KEY, listed_name TEXT, listing_type TEXT);
CREATE TABLE IF NOT EXISTS supplier_master(
  id TEXT PRIMARY KEY, applicant TEXT, supplier_name TEXT, status TEXT, category TEXT);
CREATE TABLE IF NOT EXISTS due_diligence(
  id TEXT PRIMARY KEY, applicant TEXT, check_type TEXT, outcome TEXT, checked_step INTEGER);
CREATE TABLE IF NOT EXISTS bank_details(
  id TEXT PRIMARY KEY, applicant TEXT, account_holder TEXT, verified_step INTEGER);
CREATE TABLE IF NOT EXISTS spend_ceilings(
  id TEXT PRIMARY KEY, applicant TEXT, ceiling_value REAL);
