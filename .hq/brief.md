# Brief

there is a tech_competition_prompt.md

## Note from manager
The referenced file now lives at `.hq/brief-source.md`. It is the full requirements document and the
source of truth. That file is gitignored on purpose: it names client/employer organisations that the
public-release audit must remove. Read it locally, but never copy those organisation names
into any committed file (spec, tasks, reviews, code, tests, site, launch copy). Refer to them only as
"the denylist in .hq/brief-source.md". The audit script should read its denylist from an
uncommitted local file or env var, not from a hard-coded list.
