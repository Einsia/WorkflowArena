CREATE TABLE IF NOT EXISTS dsar_requests(
  id TEXT PRIMARY KEY, subject TEXT, subject_name TEXT, request_type TEXT,
  received_step INTEGER, prior_response_step INTEGER, id_evidence TEXT, channel TEXT);
CREATE TABLE IF NOT EXISTS records_index(
  id TEXT PRIMARY KEY, subject TEXT, holding_system TEXT, record_ref TEXT, sensitivity TEXT);
CREATE TABLE IF NOT EXISTS exemptions(
  id TEXT PRIMARY KEY, record TEXT, ground TEXT, status TEXT, registered_step INTEGER);
CREATE TABLE IF NOT EXISTS identity_checks(
  id TEXT PRIMARY KEY, request TEXT, method TEXT, outcome TEXT, checked_step INTEGER);
CREATE TABLE IF NOT EXISTS redaction_log(
  id TEXT PRIMARY KEY, record TEXT, redacted_fields TEXT, logged_step INTEGER);
CREATE TABLE IF NOT EXISTS disclosure_packs(
  id TEXT PRIMARY KEY, request TEXT, record TEXT, released_step INTEGER, redaction_ref TEXT);
CREATE TABLE IF NOT EXISTS case_outcomes(
  id TEXT PRIMARY KEY, request TEXT, disposition TEXT, closed_step INTEGER);
