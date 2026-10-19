-- Connector usage by conversation, not by IP. claude.ai calls all arrive from Anthropic's servers, so the IP hash
-- (caller_hash) counted server addresses, not people. session_hash is a salted hash of the Mcp-Session-Id the
-- connector now issues; is_owner marks calls through the owner's own connector URL (?k=MCP_OWNER_KEY).
ALTER TABLE mcp_call_log ADD COLUMN IF NOT EXISTS session_hash VARCHAR(16);
ALTER TABLE mcp_call_log ADD COLUMN IF NOT EXISTS is_owner BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_mcp_call_log_session ON mcp_call_log (session_hash);
