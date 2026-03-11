"""
ml/train_model.py — Trains an XGBoost classifier for fraud detection.

Reads the synthetic training data, trains a 4-class model, evaluates it,
and saves the trained model + metadata for use in the pipeline.

Usage:
    cd backend
    python -m ml.train_model                    # default settings
    python -m ml.train_model --estimators 200   # more trees
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from ml.generate_training_data import FEATURE_COLS, LABELS

# Reverse label map for display
LABEL_NAMES = {v: k for k, v in LABELS.items()}


def train(
    data_path: str | None = None,
    n_estimators: int = 150,
    max_depth: int = 5,
    learning_rate: float = 0.1,
    test_size: float = 0.2,
    seed: int = 42,
) -> dict:
    """
    Train XGBoost fraud classifier.

    Args:
        data_path: path to training_data.csv (default: ml/data/training_data.csv)
        n_estimators: number of boosting rounds
        max_depth: max tree depth
        learning_rate: step size shrinkage
        test_size: fraction held out for evaluation
        seed: random seed

    Returns:
        dict with model path, accuracy, and classification report
    """
    # ── Load data ──────────────────────────────────────────────────────────
    if data_path is None:
        data_path = Path(__file__).parent / "data" / "training_data.csv"
    else:
        data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(
            f"Training data not found at {data_path}.\n"
            f"Run: python -m ml.generate_training_data"
        )

    df = pd.read_csv(data_path)
    print(f"📂 Loaded {len(df)} samples from {data_path.name}")

    X = df[FEATURE_COLS].values
    y = df["label_encoded"].values

    # ── Split ──────────────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    print(f"   Train: {len(X_train)}, Test: {len(X_test)}")

    # ── Train ──────────────────────────────────────────────────────────────
    print(f"\n🏋️ Training XGBoost (n_estimators={n_estimators}, max_depth={max_depth})...")
    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        objective="multi:softprob",
        num_class=len(LABELS),
        eval_metric="mlogloss",
        random_state=seed,
        use_label_encoder=False,
        verbosity=0,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── Evaluate ───────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    target_names = [LABEL_NAMES[i] for i in sorted(LABELS.values())]
    report = classification_report(y_test, y_pred, target_names=target_names)
    cm = confusion_matrix(y_test, y_pred)

    print(f"\n✅ Test Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"\n📊 Classification Report:\n{report}")
    print(f"📋 Confusion Matrix:")
    print(f"   Labels: {target_names}")
    print(cm)

    # ── Feature importance ─────────────────────────────────────────────────
    importances = model.feature_importances_
    feat_imp = sorted(
        zip(FEATURE_COLS, importances), key=lambda x: x[1], reverse=True
    )
    print(f"\n🔑 Feature Importance (top 10):")
    for fname, imp in feat_imp[:10]:
        bar = "█" * int(imp * 50)
        print(f"   {fname:30s} {imp:.4f} {bar}")

    # ── Save model ─────────────────────────────────────────────────────────
    model_dir = Path(__file__).parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "fraud_model.json"
    model.save_model(str(model_path))
    print(f"\n💾 Model saved to {model_path}")

    # Save metadata alongside model
    metadata = {
        "accuracy": round(accuracy, 4),
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "learning_rate": learning_rate,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "feature_columns": FEATURE_COLS,
        "label_map": LABELS,
        "feature_importance": {name: round(float(imp), 4) for name, imp in feat_imp},
    }
    metadata_path = model_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"📄 Metadata saved to {metadata_path}")

    return {
        "model_path": str(model_path),
        "accuracy": accuracy,
        "report": report,
    }


def main():
    parser = argparse.ArgumentParser(description="Train fraud detection model")
    parser.add_argument("--data", type=str, default=None, help="Path to training CSV")
    parser.add_argument("--estimators", type=int, default=150, help="Number of trees")
    parser.add_argument("--depth", type=int, default=5, help="Max tree depth")
    parser.add_argument("--lr", type=float, default=0.1, help="Learning rate")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    train(
        data_path=args.data,
        n_estimators=args.estimators,
        max_depth=args.depth,
        learning_rate=args.lr,
        test_size=args.test_size,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
