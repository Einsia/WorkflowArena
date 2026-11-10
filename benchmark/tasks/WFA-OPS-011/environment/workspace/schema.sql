CREATE TABLE IF NOT EXISTS contracts(
  id TEXT PRIMARY KEY, counterparty TEXT, current_value REAL, index_series TEXT,
  notice_state TEXT, renewed_through TEXT, term_end_step INTEGER);
CREATE TABLE IF NOT EXISTS price_indices(
  id TEXT PRIMARY KEY, series TEXT, period TEXT, factor_bp INTEGER);
CREATE TABLE IF NOT EXISTS legal_reviews(
  id TEXT PRIMARY KEY, contract TEXT, period TEXT, outcome TEXT, reviewer TEXT);
CREATE TABLE IF NOT EXISTS signatories(
  id TEXT PRIMARY KEY, name TEXT, authority_limit REAL, status TEXT);
CREATE TABLE IF NOT EXISTS crm_opportunities(
  id TEXT PRIMARY KEY, contract TEXT, counterparty TEXT, stage TEXT, value REAL);
CREATE TABLE IF NOT EXISTS finance_schedules(
  id TEXT PRIMARY KEY, contract TEXT, annual_value REAL, start_step INTEGER, signatory TEXT);
