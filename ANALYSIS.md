# Comparative Analysis: Academic Research Task With and Without MCP

## Setup

**Prompt given to the agent:**
> Find the first journal paper by Ante Kapetanovic and extract all references from that paper.

**Agent:** Claude Code (Opus 4.6), 200k context window

**Ground truth:** RIS file exported directly from Springer, containing 68 references.

**Paper found (both runs):** Kapetanovic, A., Susnjara, A. & Poljak, D. "Stochastic analysis of the electromagnetic induction effect on a neuron's action potential dynamics." *Nonlinear Dynamics*, 105, 3585-3602 (2021). DOI: 10.1007/s11071-021-06762-z

---

## Results

| Metric | Without MCP | With MCP |
|---|---|---|
| **Recall** | 85.3% (58/68) | **100.0% (68/68)** |
| **Precision** | 100.0% | 100.0% |
| **Missing references** | 10 | **0** |
| **Tool calls (total)** | 40 | **14** |
| **Tool calls (failed)** | 30 | **6** |
| **Tool success rate** | 25.0% | **57.1%** |
| **Distinct failure types** | 12 | **3** |
| **Assistant turns** | 30 | **10** |
| **Message tokens** | 44,600 | 67,200* |
| **Side effects on environment** | 3 | **0** |

\* The with-MCP token count includes the comparison phase where the agent read the 816-line RIS ground truth file, the 135-line without-MCP report, and wrote this analysis. The reference extraction task alone consumed fewer tokens, but the exact split is not separately measurable.

---

## What Happened Without MCP

The agent had access to WebSearch, WebFetch, Bash, and Read. No domain-specific tools were available.

Finding the author took 5 turns of web searching and cross-referencing results. Identifying the first journal paper required 2 more turns of manual filtering through unstructured HTML.

Then the real trouble started. The agent tried to retrieve references through 17 consecutive failed attempts:

- Springer returned HTTP 303 redirects (5 times)
- ResearchGate returned HTTP 403
- Google Scholar returned raw JavaScript instead of content
- The Semantic Scholar REST API blocked the references field at the publisher's request
- A downloaded "PDF" turned out to be HTML
- The agent installed `pypdf` into the project's virtual environment to parse it
- Python environment issues consumed 4 more attempts (wrong venv, missing pip, module not found)

The approach that finally worked was downloading Springer's raw HTML with `curl` using a browser User-Agent header, then parsing it with Python regex. This extracted 58 of 68 references. The last 10 were hidden behind Springer's lazy-loading and never reached the parser.

**75% of all tool calls failed.** The agent encountered 12 distinct failure types. It left behind an installed pip package and two temporary files.

## What Happened With MCP

The agent had access to WebSearch, WebFetch, Read, and the Semantic Scholar MCP server (14 tools for searching papers, authors, citations, references, and recommendations).

Finding the author took 1 turn. Two parallel `search_authors` calls returned structured records with paper counts, h-indices, and DBLP aliases. The agent immediately spotted that there were multiple profiles for the same person.

Identifying the first journal paper took 1 more turn. Two parallel `get_author_details` calls returned complete publication lists with venue types, publication dates, and journal metadata. The agent picked the earliest entry marked as a journal article.

Reference retrieval hit the same publisher restriction. Springer blocks the `references` field in the Semantic Scholar API for this paper. The agent tried 3 variations of `get_paper_references` and confirmed the block. It then tried WebFetch on the Springer page (same 303 redirects as before). Within 2 more turns it reached the Crossref API via WebFetch, which returned all 68 references as structured JSON with full metadata.

No packages were installed. No temporary files were created. No environment was modified.

---

## Why the MCP Approach Worked Better

### 1. Structured discovery replaced guesswork

Without MCP, finding an author means searching the web, following links, and parsing unstructured HTML. With MCP, `search_authors` returns structured records. The agent gets paper counts, citation metrics, and cross-database identifiers in one call. It can spot duplicate profiles and choose the right one without guessing.

### 2. Fewer tools means fewer ways to fail

The without-MCP agent encountered 12 distinct failure types: HTTP errors, environment issues, hallucinated URLs, format mismatches, and more. The MCP agent encountered 3 failure types, all caused by a single root problem (Springer's data restriction). When your tools are purpose-built, there are fewer things that can go wrong.

### 3. Fast failure leads to faster recovery

Both approaches eventually needed to leave the Semantic Scholar ecosystem because of the publisher block. The MCP approach diagnosed this in 3 calls and pivoted. The without-MCP approach spent 17 turns on the same dead ends before finding a workaround. And that workaround (HTML regex scraping) was lossy, missing the last 10 references.

### 4. No collateral damage

The without-MCP agent installed `pypdf` into the project's virtual environment and left two temporary files on disk. The MCP agent left no trace. For a research workflow that runs repeatedly, zero side effects matter.

---

## Limitations

Both approaches share the same fundamental constraint: Springer blocks reference data from the Semantic Scholar API. The MCP cannot override this. In both cases, the Crossref API served as the successful fallback.

The token comparison is not strictly apples-to-apples. The with-MCP session included the comparison analysis phase (reading ground truth files and writing the report), inflating its token count. The without-MCP measurement was taken before any comparison work.

The MCP tools show 0 tokens in the `/context` output because MCP tool definitions are loaded separately from the message context. Their cost is real but not reflected in the message token count.

---

## Conclusion

The Semantic Scholar MCP turned a 30-turn, 40-call task with 85% recall into a 10-turn, 14-call task with 100% recall. It reduced failed tool calls by 80% and eliminated all side effects on the development environment.

The MCP did not solve every problem. The same publisher restriction blocked both approaches. But it gave the agent structured, domain-specific tools that fail fast and fail cleanly. Instead of spending most of its effort fighting web infrastructure, the agent spent its effort on the actual research task.

For researchers who work with coding agents, this is what an MCP server provides: less time debugging HTTP errors and parsing HTML, more time doing research.
