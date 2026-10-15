"""Builder script for Machine_Learning/notebooks/02_heart_disease.ipynb.

Demonstrates end-to-end Heart Disease model development:
1. Reusable preprocessing and clinical feature engineering
2. Baseline & candidate model comparison
3. Validation fold selection
4. Held-out test evaluation & confusion matrix
5. ROC and Precision-Recall curve visualizations
6. Clinical limitations and sample size discussion
"""

from pathlib import Path
import nbformat as nbf

def generate_notebook(notebook_path: Path):
    nb = nbf.v4.new_notebook()
    cells = []

    # Cell 1: Markdown Title & Scope
    cells.append(nbf.v4.new_markdown_cell("""# 02 - Heart Disease Risk Model Development
## Coronary Artery Disease (CAD) Classification (UCI Dataset)

> **Clinical Decision-Support Prototype Note**:
> This notebook documents the complete model development lifecycle for the UCI Heart Disease prediction task:
> 1. Target definition and clinical task framing (Angiographic CAD presence: `num > 0`).
> 2. Leakage-free preprocessing and clinical feature engineering.
> 3. Comparative evaluation of baseline and candidate classifiers on the validation fold.
> 4. Final unbiased evaluation on held-out test data.
> 5. ROC / Precision-Recall curve visualization and confusion matrix analysis.
> 6. Discussion of sample size, class balance, and clinical limitations.
"""))

    # Cell 2: Code Imports & Setup
    cells.append(nbf.v4.new_code_cell("""import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix, ConfusionMatrixDisplay

PROJECT_ROOT = Path('.').resolve().parent.parent if Path('.').resolve().name == 'notebooks' else Path('.').resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Machine_Learning.src.data_loader import load_heart_disease_data
from Machine_Learning.src.preprocessing import (
    prepare_heart_disease_splits,
    preprocess_inference_input,
    HEART_DISEASE_RAW_FEATURES,
)
from Machine_Learning.src.train_heart_disease import get_candidate_models, train_and_select_best_model
from Machine_Learning.src.evaluate import evaluate_binary_classifier, print_evaluation_summary

sns.set_theme(style='whitegrid', palette='muted')
print('Environment initialized successfully. Project root:', PROJECT_ROOT)
"""))

    # Cell 3: Markdown - Data Ingestion and Target Verification
    cells.append(nbf.v4.new_markdown_cell("""## 1. Data Ingestion & Target Definition Verification
The target `num` represents angiographic coronary stenosis severity:
- `num == 0`: Absence of angiographic CAD (<50% diameter stenosis in major vessels).
- `num >= 1`: Presence of angiographic CAD (>=50% stenosis across 1 to 4 vessels).
Here we train binary screening classifiers to predict CAD presence (`CAD_Status = (num > 0).astype(int)`).
"""))

    # Cell 4: Code - Data Splits
    cells.append(nbf.v4.new_code_cell("""df_raw = load_heart_disease_data()
splits = prepare_heart_disease_splits(
    df_raw, test_size=0.2, val_size=0.1, random_state=42, target_mode='binary'
)

print(f'Total Dataset Records: {len(df_raw)}')
print(f'Training fold       : {splits.X_train.shape[0]} samples ({round(splits.X_train.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Validation fold     : {splits.X_val.shape[0]} samples ({round(splits.X_val.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Held-out Test fold  : {splits.X_test.shape[0]} samples ({round(splits.X_test.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Transformed Features: {splits.X_train.shape[1]}')
print(f'CAD Positive Prevalence in Train: {np.mean(splits.y_train):.3f}, Test: {np.mean(splits.y_test):.3f}')
"""))

    # Cell 5: Markdown - Candidate Model Evaluation
    cells.append(nbf.v4.new_markdown_cell("""## 2. Baseline & Candidate Model Comparison
We evaluate five diverse classifiers on the validation fold without touching the held-out test set:
1. **Dummy (Stratified)**: Random chance baseline matching class prior.
2. **Logistic Regression (Balanced)**: Linear baseline with L2 regularization and inverse class frequency weighting.
3. **Random Forest**: Non-linear ensemble (150 trees, max depth 6).
4. **Gradient Boosting**: Sequential boosting model (120 estimators, learning rate 0.05).
5. **Support Vector Classifier (RBF)**: Non-linear kernel boundary with probability estimates.
"""))

    # Cell 6: Code - Candidate Comparison
    cells.append(nbf.v4.new_code_cell("""best_name, best_model, val_results = train_and_select_best_model(splits, random_state=42)

val_summary = []
for name, res in val_results.items():
    val_summary.append({
        'Model': name,
        'Val Accuracy': res['accuracy'],
        'Val Balanced Acc': res['balanced_accuracy'],
        'Val Sensitivity (Recall)': res['recall_sensitivity'],
        'Val Specificity': res['specificity'],
        'Val Precision': res['precision'],
        'Val F1': res['f1_score'],
        'Val ROC-AUC': res.get('roc_auc'),
        'Val Brier': res.get('brier_score')
    })

val_df = pd.DataFrame(val_summary).sort_values(by='Val ROC-AUC', ascending=False)
print('Candidate Model Validation Comparison:')
print(val_df.to_string(index=False))
"""))

    # Cell 7: Markdown - Final Test Evaluation
    cells.append(nbf.v4.new_markdown_cell("""## 3. Final Evaluation on Held-Out Test Data
The top-performing model selected from validation is evaluated on the completely unseen Test fold (184 patients).
"""))

    # Cell 8: Code - Test Metrics
    cells.append(nbf.v4.new_code_cell("""y_test_pred = best_model.predict(splits.X_test)
y_test_prob = best_model.predict_proba(splits.X_test)[:, 1]

test_metrics = evaluate_binary_classifier(splits.y_test, y_test_pred, y_test_prob)
print_evaluation_summary(test_metrics, f'HELD-OUT TEST SET ({best_name})')
"""))

    # Cell 9: Markdown - Diagnostic Visualizations
    cells.append(nbf.v4.new_markdown_cell("""## 4. Diagnostic Performance Visualizations
Generating Confusion Matrix, ROC Curve, and Precision-Recall Curve on the held-out test set.
"""))

    # Cell 10: Code - Visualizations
    cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 1. Confusion Matrix
cm = confusion_matrix(splits.y_test, y_test_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['No CAD', 'CAD Present'])
disp.plot(ax=axes[0], cmap='Blues', colorbar=False)
axes[0].set_title(f'Confusion Matrix\\n({best_name})')
axes[0].grid(False)

# 2. ROC Curve
fpr, tpr, _ = roc_curve(splits.y_test, y_test_prob)
axes[1].plot(fpr, tpr, color='crimson', lw=2, label=f'ROC-AUC = {test_metrics[\"roc_auc\"]:.3f}')
axes[1].plot([0, 1], [0, 1], color='gray', linestyle='--')
axes[1].set_title('Receiver Operating Characteristic (ROC)')
axes[1].set_xlabel('False Positive Rate (1 - Specificity)')
axes[1].set_ylabel('True Positive Rate (Sensitivity)')
axes[1].legend(loc='lower right')

# 3. Precision-Recall Curve
prec, rec, _ = precision_recall_curve(splits.y_test, y_test_prob)
baseline_prevalence = np.mean(splits.y_test)
axes[2].plot(rec, prec, color='teal', lw=2, label=f'PR-AUC = {test_metrics[\"pr_auc\"]:.3f}')
axes[2].axhline(baseline_prevalence, color='gray', linestyle='--', label=f'Baseline ({baseline_prevalence:.2f})')
axes[2].set_title('Precision-Recall Curve')
axes[2].set_xlabel('Recall (Sensitivity)')
axes[2].set_ylabel('Precision (Positive Predictive Value)')
axes[2].legend(loc='lower left')

plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hd_model_performance.png', dpi=150)
plt.close()
print('Saved diagnostic plot: hd_model_performance.png')
"""))

    # Cell 11: Markdown - Sample Size and Clinical Limitations
    cells.append(nbf.v4.new_markdown_cell("""## 5. Sample Size Limitations & Clinical Interpretability
1. **Sample Size Constraints**: The total dataset comprises 920 patients across four historical centers (Cleveland, Hungary, Switzerland, Long Beach). While adequate for prototype benchmarking, prospective clinical deployment requires validation across contemporary multi-center cohorts.
2. **Missing Secondary Tests**: Fluoroscopy (`ca`) and nuclear scans (`thal`) were missing in over 50% of records due to site ordering protocols. The median imputation strategy allows graceful degradation when secondary diagnostics have not been conducted.
3. **Research Prototype Notice**: This model is a research and educational prototype. Model scores reflect statistical correlations and do not constitute clinical diagnostic proof. Emergency clinical safety rules operate independently of model scores.
"""))

    nb.cells = cells
    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)
    print(f'Successfully generated {notebook_path} with {len(cells)} cells.')

if __name__ == '__main__':
    target = Path(__file__).resolve().parent / '02_heart_disease.ipynb'
    generate_notebook(target)
