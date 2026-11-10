CREATE TABLE IF NOT EXISTS leavers(
  id TEXT PRIMARY KEY, name TEXT, engagement TEXT, role TEXT, site TEXT,
  leave_type TEXT, last_day_step INTEGER, manager TEXT);
CREATE TABLE IF NOT EXISTS issued_assets(
  id TEXT PRIMARY KEY, person TEXT, asset_class TEXT, serial TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS access_grants(
  id TEXT PRIMARY KEY, person TEXT, system TEXT, status TEXT, revoked_step INTEGER);
CREATE TABLE IF NOT EXISTS payroll_entries(
  id TEXT PRIMARY KEY, person TEXT, band TEXT, status TEXT, close_step INTEGER);
CREATE TABLE IF NOT EXISTS delegations(
  id TEXT PRIMARY KEY, holder TEXT, scope TEXT, status TEXT, reassigned_to TEXT);
CREATE TABLE IF NOT EXISTS open_cases(
  id TEXT PRIMARY KEY, owner TEXT, subject TEXT, status TEXT, reassigned_to TEXT);
CREATE TABLE IF NOT EXISTS asset_returns(
  id TEXT PRIMARY KEY, person TEXT, asset_class TEXT, serial TEXT, received_step INTEGER);
