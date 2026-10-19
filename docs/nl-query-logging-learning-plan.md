# NL Query: How It Works + Learning from User Input

## Context
The NL search feature is live and working. This plan covers two things:
1. Explaining how the current system works end-to-end
2. Planning a feedback/learning mechanism to improve over time based on real user queries

---

## How the Current System Works (End-to-End)

### Flow: User types "Kohli vs spin in death overs in IPL"

```
[Frontend: NLQueryInput.jsx]
  User types query -> clicks Search (or hits Enter)
  -> POST /nl2query/parse { query: "..." }

[Backend: routers/nl2query.py]
  -> Rate limit check (10 req/min per IP)
  -> Calls parse_nl_query(query)

[Backend: services/nl2query.py]
  1. Check in-memory cache (24h TTL, keyed by lowercase query)
  2. If miss -> call OpenAI GPT-4o-mini:
     - System prompt: ~100 lines defining all valid filters, field names,
       team mappings, league aliases, phase ranges, rules
     - response_format=json_object forces structured JSON output
     - temperature=0.1 for deterministic results
  3. LLM returns: { filters: {...}, group_by: [...], explanation, confidence, suggestions }
  4. validate_filters() sanitizes the output:
     - Strips invalid enum values (bowl_style, leagues, etc.)
     - Clamps over ranges to 0-19
     - Passes through player/team names (can't validate without DB)
  5. Cache the result, return to router

[Backend -> Frontend]
  Response: { success: true, filters: { batters: ["V Kohli"], bowl_kind: ["spin bowler"],
              over_min: 15, over_max: 19, leagues: ["IPL"], min_balls: 20 },
              group_by: ["batter","bowl_kind","phase"], explanation: "...", confidence: "high" }

[Frontend: QueryBuilder.jsx -> handleNLFilters()]
  1. Reset all filters to defaults
  2. Merge NL-parsed filters on top
  3. Set groupBy state
  4. Update URL immediately (shareable link)
  5. Show explanation banner ("AI interpretation: ...")
  6. If confidence === "high" -> auto-execute query after 300ms delay
     If confidence === "medium"/"low" -> just populate filters, user reviews & clicks Execute

[Frontend: executeQuery()]
  -> GET /query/deliveries?batters=V+Kohli&bowl_kind=spin+bowler&over_min=15&...
  -> Results displayed in table, URL updated
```

### Key Design Decisions
- **GPT-4o-mini** -- cheap (~$0.0003/query), fast (~500ms), good enough for structured extraction
- **In-memory cache** -- same query text won't re-call the LLM for 24h
- **Validation layer** -- LLM output is never trusted directly; every field is checked against known valid values
- **Confidence routing** -- high confidence = auto-execute (seamless UX), medium/low = populate only (user reviews)
- **URL sync** -- filters are written to URL params immediately, so any NL query result is a shareable link

---

## Plan: Learning from User Queries

### Problem
Right now the system is stateless. The key learning opportunity is **implicit correction**: when a user types "Kohli vs spin in death overs", gets filters auto-populated, but then manually tweaks the filters (e.g. changes over_min from 15 to 16, adds a league filter, removes a group_by column) and re-executes -- that diff is a signal that the LLM got it partially wrong. We want to capture that signal and feed it back.

### Approach: Implicit correction loop

The idea is:
1. Log the NL query + the LLM's initial filter output
2. Detect when the user modifies those filters and re-executes (the "correction")
3. Store the diff -- original LLM filters vs what the user actually ran
4. Use corrections as few-shot examples in the system prompt, so the LLM learns the right mappings over time

### How it works in practice

```
User: "Kohli vs spin in death overs in IPL"

LLM returns:
  { batters: ["V Kohli"], bowl_kind: ["spin bowler"], over_min: 15, over_max: 19, leagues: ["IPL"] }
  group_by: ["batter", "bowl_kind", "phase"]

User sees filters populated, but tweaks:
  - Removes "phase" from group_by (doesn't want phase breakdown)
  - Adds min_balls: 50 (wants more statistical significance)
  - Clicks Execute

System detects: these filters came from NL query, but user modified them.
Logs a correction:
  query: "Kohli vs spin in death overs in IPL"
  llm_filters: { ... original ... }
  user_filters: { ... what they actually executed ... }
  diff: { removed_group_by: ["phase"], added: { min_balls: 50 } }
```

Over time, with enough corrections, we can:
- Add the most common corrections as few-shot examples in the system prompt
- Identify systematic errors (e.g. "LLM always forgets min_balls") and add rules
- Build a correction table the LLM can reference

### Implementation sketch (for future session)

**Frontend (QueryBuilder.jsx):**
- Track `nlQueryId` state -- set when NL filters are applied
- In `executeQuery()`, if `nlQueryId` is set AND filters differ from what NL returned, POST the correction to `/nl2query/correction`
- Clear `nlQueryId` after posting (only capture first correction per NL query)

**Backend (services/nl2query.py + routers/nl2query.py):**
- `nl_query_log` table: `id`, `query_text`, `llm_filters` (jsonb), `user_filters` (jsonb), `group_by_llm`, `group_by_user`, `created_at`
- `POST /nl2query/correction` endpoint -- accepts original `query_id` + the user's actual filters/group_by
- `GET /nl2query/corrections` -- returns recent corrections for prompt tuning

**Prompt improvement loop:**
- Periodically review corrections via the analytics endpoint
- Extract patterns (e.g. "users always add min_balls when the LLM doesn't")
- Add as few-shot examples or rules to `SYSTEM_PROMPT`
- Could eventually automate: fetch top 5 corrections and inject them as examples in the prompt
