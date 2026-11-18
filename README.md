# Central Bank Mood Tracker

An AI that reads central bank speeches, measures how central bankers sound, and tests whether that tone helps forecast the economy.

It extends the method in the BIS paper [*Large language models: a primer for economists*](https://www.bis.org/publ/qtrpdf/r_qt2412b.htm) (Kwon, Park, Perez-Cruz and Rungcharoenkitkul, 2024). The paper's [sample code](https://github.com/bis-med-it/LLM_Primer_for_Economists) shows the pipeline on arXiv abstracts with placeholder sentiment. This project runs it on real economic text, with real LLM scoring, and evaluates the result against macro data.

## How it works

1. **Speeches.** The BIS archive of central bankers' speeches: about 21,000 speeches from 1996 onwards, matched to their central bank and country.
2. **Sentiment.** An LLM rates each paragraph on monetary-policy stance (hawkish/dovish) and growth outlook. By default it runs locally through [Ollama](https://ollama.com); an API backend is optional.
3. **Topics.** BERTopic groups paragraphs into themes such as inflation, labour markets and financial stability.
4. **Mood index.** Paragraph scores are aggregated into a monthly index per country by a COBOL batch job, the way bank back-office systems still process records.
5. **Forecast test.** In R, the standard econometrics language at central banks: does the index improve forecasts of GDP growth and policy-rate changes beyond standard benchmarks?
6. **Dashboard.** Explore the index by country and topic, and score a speech of your own.

## Languages

| Language | Used for | Why |
| --- | --- | --- |
| Python | Data loading, LLM scoring, topics | The BIS paper's own toolchain |
| COBOL | Monthly mood index batch job | Still runs core banking batch processing |
| R | Forecast evaluation | Standard for applied econometrics at central banks |

## Status

| Step | Status |
| --- | --- |
| Speech loader | done |
| LLM sentiment scoring | built; accuracy check needs hand labels |
| Topic modelling | planned |
| Monthly mood index | planned |
| Macro data and forecast test | planned |
| Dashboard | planned |

## Run it locally

Requires Python 3.10+.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m mood_tracker.download        # fetches the BIS archive (~130 MB) into data/raw/
python -m mood_tracker.load_speeches   # writes data/processed/*.parquet
```

### Score sentiment

Install [Ollama](https://ollama.com) and pull the default model with `ollama pull llama3.2:3b`. On a laptop CPU it labels a paragraph in about 5-8 seconds, so scoring works on a sample per country and month:

```bash
# pilot: US and Kenya, 2 paragraphs per month since 2023
python -m mood_tracker.score --countries US KE --start 2023 --per-month 2
```

Runs are resumable: stop with Ctrl+C and the same command carries on. To use Claude instead, `pip install anthropic`, sign in with an API key, and add `--backend claude`.

### Check accuracy

```bash
python -m mood_tracker.validate export --n 200     # writes a sheet to label by hand
python -m mood_tracker.validate evaluate           # compares the model with your labels
```

## Data

Speeches come from the [BIS central bankers' speeches](https://www.bis.org/cbspeeches/) archive and remain subject to the BIS terms of use. Downloaded data is not committed to this repository.
