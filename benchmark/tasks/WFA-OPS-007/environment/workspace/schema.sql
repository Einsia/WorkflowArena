CREATE TABLE IF NOT EXISTS joiners(
  id TEXT PRIMARY KEY, name TEXT, engagement TEXT, role TEXT, site TEXT,
  start_step INTEGER, clearance TEXT, prior_record TEXT);
CREATE TABLE IF NOT EXISTS hr_records(
  id TEXT PRIMARY KEY, joiner TEXT, status TEXT, engagement TEXT, site TEXT);
CREATE TABLE IF NOT EXISTS payroll_entries(
  id TEXT PRIMARY KEY, joiner TEXT, band TEXT, effective_step INTEGER);
CREATE TABLE IF NOT EXISTS access_grants(
  id TEXT PRIMARY KEY, joiner TEXT, system TEXT, granted_step INTEGER);
CREATE TABLE IF NOT EXISTS asset_issues(
  id TEXT PRIMARY KEY, joiner TEXT, asset_class TEXT, serial TEXT);
CREATE TABLE IF NOT EXISTS asset_stock(
  id TEXT PRIMARY KEY, asset_class TEXT, available INTEGER);
