CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY,
  email text UNIQUE NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz
);

CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES users(id),
  target_product text,
  target_brief text NOT NULL,
  competitor_names jsonb NOT NULL DEFAULT '[]'::jsonb,
  dimensions jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS task_runs (
  id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'pending',
  retry_count integer NOT NULL DEFAULT 0,
  langgraph_thread_id text,
  checkpoint_id text,
  error_summary jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  cancelled_at timestamptz
);

CREATE TABLE IF NOT EXISTS agent_traces (
  id uuid PRIMARY KEY,
  task_run_id uuid NOT NULL REFERENCES task_runs(id) ON DELETE CASCADE,
  sequence_no integer NOT NULL,
  agent_name text NOT NULL,
  node_name text NOT NULL,
  status text NOT NULL,
  prompt text NOT NULL,
  input_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  tokens_in integer NOT NULL DEFAULT 0,
  tokens_out integer NOT NULL DEFAULT 0,
  cost_usd numeric NOT NULL DEFAULT 0,
  latency_ms integer NOT NULL DEFAULT 0,
  langsmith_run_id text,
  decision_meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (task_run_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS source_citations (
  id text PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  type text NOT NULL,
  category text NOT NULL DEFAULT 'unknown',
  url text,
  title text NOT NULL,
  snippet text NOT NULL,
  raw_content text,
  provider text NOT NULL,
  valid boolean NOT NULL DEFAULT true,
  embedding vector(1536),
  fetched_at timestamptz NOT NULL DEFAULT now(),
  fetched_by_agent text
);

CREATE TABLE IF NOT EXISTS competitor_profiles (
  id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  competitor_name text NOT NULL,
  feature_tree jsonb NOT NULL DEFAULT '{}'::jsonb,
  pricing jsonb NOT NULL DEFAULT '{}'::jsonb,
  user_personas jsonb NOT NULL DEFAULT '[]'::jsonb,
  swot jsonb NOT NULL DEFAULT '{}'::jsonb,
  review_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cross_analyses (
  id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  feature_matrix jsonb NOT NULL DEFAULT '{}'::jsonb,
  pricing_comparison jsonb NOT NULL DEFAULT '{}'::jsonb,
  positioning_map jsonb NOT NULL DEFAULT '{}'::jsonb,
  differentiation_summary text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reports (
  id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  structured_content jsonb NOT NULL DEFAULT '{}'::jsonb,
  markdown_content text NOT NULL,
  language text NOT NULL DEFAULT 'zh',
  source_report_id uuid REFERENCES reports(id),
  version integer NOT NULL DEFAULT 1,
  qa_status text NOT NULL DEFAULT 'issues',
  qa_issues jsonb NOT NULL DEFAULT '[]'::jsonb,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  embedding vector(1536),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_claims (
  id uuid PRIMARY KEY,
  report_id uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  claim_path text NOT NULL,
  claim_text text NOT NULL,
  layer text NOT NULL,
  field_type text NOT NULL,
  source_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  generating_agent text NOT NULL,
  qa_status text NOT NULL DEFAULT 'pass',
  source_support text NOT NULL DEFAULT 'unchecked',
  validity text NOT NULL DEFAULT 'unknown',
  edit_status text NOT NULL DEFAULT 'untouched',
  review_status text NOT NULL DEFAULT 'unreviewed',
  correction_type text,
  embedding vector(1536),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS manual_corrections (
  id uuid PRIMARY KEY,
  report_id uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  claim_id uuid REFERENCES report_claims(id) ON DELETE SET NULL,
  field_path text NOT NULL,
  old_value jsonb,
  new_value jsonb NOT NULL,
  correction_type text NOT NULL,
  triggered_rerun boolean NOT NULL DEFAULT false,
  user_id uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS survey_uploads (
  id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  kind text NOT NULL,
  filename text NOT NULL,
  original_size integer NOT NULL,
  redacted_content jsonb NOT NULL DEFAULT '{}'::jsonb,
  parsed_evidence_count integer NOT NULL DEFAULT 0,
  uploaded_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_traces_run_sequence ON agent_traces(task_run_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_tasks_user_created ON tasks(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_task_created ON reports(task_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_report_claims_report ON report_claims(report_id);
