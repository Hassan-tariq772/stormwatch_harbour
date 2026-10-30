# Stormwatch Harbour — CGD-460 Assignment 2

Hassan Tariq (232925) · BS Computer Games Development · CGD-460 Agentic Artificial Intelligence

A small harbour-management simulation with a Lookout, Quartermaster, ten
Dockworkers and an LLM Harbour Master whose replies are validated before use.

## Run

```bash
pip install -r requirements.txt     # only matplotlib (for the chart)
python run.py                       # everything: seeds 11-13, extra 11-15, safety cases
```

Python 3.9+. Results are written to `results/`.

Optional — use a real LLM instead of the offline mock (any OpenAI-compatible API,
e.g. OpenAI, Groq, OpenRouter, local Ollama):

```bash
export LLM_API_KEY=...            # your key
export LLM_BASE_URL=https://api.groq.com/openai/v1   # default: OpenAI
export LLM_MODEL=llama-3.1-8b-instant                # default: gpt-4o-mini
python run.py --llm real
```

## Files

| Path | What it is |
|---|---|
| `run.py` | Runs all experiments, writes tables, chart and safety results |
| `sim/config.py` | Fixed settings (grid, berths, storms, seeds …) |
| `sim/world.py` | Harbour environment, tick loop, text report, action executor |
| `sim/agents.py` | Lookout, Quartermaster, Dockworker (baseline + model-based) |
| `sim/harbour_master.py` | LLM Harbour Master, strict validator, model-based fallback |
| `sim/llm_client.py` | Mock LLM (seeded, makes deliberate mistakes) and real-LLM client |
| `sim/safety.py` | The four safety cases, approval gate, grounded ship answers |
| `results/summary.md` | All result tables |
| `results/runs.csv` | Per-run results, seeds 11-13 |
| `results/runs_seeds_11_15.csv` | Extra evaluation on seeds 11-15 |
| `results/limitation_test.csv` | LLM that is always well-formed but never warns |
| `results/safety_results.csv` | Safety case outcomes |
| `results/hm_decision_log.txt` | Every Harbour Master decision, rejection and fallback |
| `results/chart.png` | Results chart |

## Map (24 × 16, x = column 0-23 west→east, y = row 0-15 north→south)

* Berths on the north edge: B1 (3,0), B2 (9,0), B3 (15,0), B4 (21,0)
* Warehouse: (0,15), south-west corner
* Danger zone during a storm: rows 0-2 within 2 columns of B1 or B4

## Reproducibility

Every non-LLM run uses one `random.Random(seed)` for storms, ship arrivals and
worker order, so the same seed always gives the same result. The mock LLM has its
own generator (`seed + 1000`) so its mistakes never change the world itself.
