"""Check the LLM's labels against hand labels.

Step 1, export a labelling sheet (open it in Excel, fill the stance and
outlook columns, save as CSV):

    python -m mood_tracker.validate export --n 200

Step 2, score the same paragraphs with a backend and report agreement:

    python -m mood_tracker.validate evaluate data/validation/to_label.csv

`evaluate` also saves the hand labels (ids and labels only, no speech text) to
validation/labels.csv, which is small enough to commit, so others can
re-run the check against the same ground truth.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mood_tracker.sampling import relevant_paragraphs
from mood_tracker.sentiment import OUTLOOK_LABELS, STANCE_LABELS, make_scorer

ROOT = Path(__file__).resolve().parents[1]
PARAGRAPHS = ROOT / "data" / "processed" / "paragraphs.parquet"
SHEET = ROOT / "data" / "validation" / "to_label.csv"
COMMITTED_LABELS = ROOT / "validation" / "labels.csv"
KEY = ["speech_id", "paragraph_no"]
DIMENSIONS = {"stance": STANCE_LABELS, "outlook": OUTLOOK_LABELS}


def export_sheet(n: int, seed: int) -> None:
    paragraphs = pd.read_parquet(PARAGRAPHS)
    pool = relevant_paragraphs(paragraphs[paragraphs["country"].notna()])
    # Spread the sheet across countries so no single central bank dominates it.
    per_country = max(1, n // pool["country"].nunique())
    shuffled = pool.sample(frac=1.0, random_state=seed)
    sheet = shuffled.groupby("country").head(per_country).head(n)
    sheet = sheet[KEY + ["country", "date", "paragraph"]].assign(stance="", outlook="")
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(SHEET, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(sheet)} paragraphs to {SHEET}")
    print("Fill in stance (" + "/".join(STANCE_LABELS) + ") and outlook ("
          + "/".join(OUTLOOK_LABELS) + "), then run `evaluate`.")


def agreement_report(truth: pd.Series, predicted: pd.Series, labels: tuple[str, ...]) -> str:
    accuracy = (truth == predicted).mean()
    f1_scores = []
    for label in labels:
        tp = ((truth == label) & (predicted == label)).sum()
        fp = ((truth != label) & (predicted == label)).sum()
        fn = ((truth == label) & (predicted != label)).sum()
        if tp + fp + fn:
            f1_scores.append(2 * tp / (2 * tp + fp + fn))
    macro_f1 = sum(f1_scores) / len(f1_scores)
    confusion = pd.crosstab(truth.rename("hand"), predicted.rename("model"))
    return f"accuracy {accuracy:.0%}, macro-F1 {macro_f1:.2f}\n{confusion.to_string()}"


def evaluate(sheet_path: Path, backend: str, model: str | None) -> None:
    sheet = pd.read_csv(sheet_path, encoding="utf-8-sig")
    for column, labels in DIMENSIONS.items():
        sheet[column] = sheet[column].astype(str).str.strip().str.lower()
        sheet = sheet[sheet[column].isin(labels)]
    if sheet.empty:
        raise SystemExit("No labelled rows found; fill in the stance and outlook columns first.")

    COMMITTED_LABELS.parent.mkdir(parents=True, exist_ok=True)
    # Optional `labeller` column records who made the reference labels (a person or a model).
    keep = KEY + ["country", "stance", "outlook"] + (["labeller"] if "labeller" in sheet else [])
    sheet[keep].to_csv(COMMITTED_LABELS, index=False)

    scorer = make_scorer(backend, model)
    predictions = [scorer.score(text) for text in sheet["paragraph"]]
    print(f"{scorer.backend} / {scorer.model} on {len(sheet)} reference-labelled paragraphs\n")
    for column, labels in DIMENSIONS.items():
        predicted = pd.Series([getattr(p, column) for p in predictions], index=sheet.index)
        print(f"{column}: {agreement_report(sheet[column], predicted, labels)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="write a labelling sheet")
    export.add_argument("--n", type=int, default=200)
    export.add_argument("--seed", type=int, default=42)
    check = commands.add_parser("evaluate", help="compare a backend with hand labels")
    check.add_argument("sheet", type=Path, nargs="?", default=SHEET)
    check.add_argument("--backend", choices=["ollama", "claude"], default="ollama")
    check.add_argument("--model")
    args = parser.parse_args()

    if args.command == "export":
        export_sheet(args.n, args.seed)
    else:
        evaluate(args.sheet, args.backend, args.model)


if __name__ == "__main__":
    main()
