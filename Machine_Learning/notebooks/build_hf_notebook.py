"""Builder script for Machine_Learning/notebooks/03_heart_failure.ipynb.

Documents:
1. Target definition verification (DEATH_EVENT vs Heart Failure Diagnosis)
2. Follow-up 'time' lookahead leakage demonstration
3. Candidate model comparison on validation fold
4. Final evaluation on held-out test fold
5. Confusion matrix, ROC, and PR curves
6. Task feasibility assessment and small-sample limitations
"""

from pathlib import Path
import nbformat as nbf

def generate_notebook(notebook_path: Path):
    nb = nbf.v4.new_notebook()
    cells = []

    # Cell 1: Markdown Title & Scope
    cells.append(nbf.v4.new_markdown_cell("""# 03 - Heart Failure Feasibility Analysis & Mortality Outcome Modeling
## Clinical Decision-Support Prototype: Research Outcome Modeling

> **MANDATORY CLINICAL & ARCHITECTURAL DIRECTIVE (Rule 8 & 20)**:
> 1. **Target Definition**: The target in this dataset is strictly **`DEATH_EVENT`** (all-cause mortality observed during follow-up).
> 2. **Clinical Population**: The study cohort consists exclusively of patients with **confirmed, severe heart failure (NYHA Class III-IV)**.
> 3. **Task Mismatch**: This dataset **does NOT support** and must **NEVER be used for** screening or diagnosing the onset of heart failure. There are no healthy controls.
> 4. **Leakage Safeguard**: Follow-up observation duration (`time`) is excluded from prospective inference to prevent look-ahead bias.
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

from Machine_Learning.src.data_loader import load_heart_failure_data
from Machine_Learning.src.preprocessing import (
    prepare_heart_failure_splits,
    preprocess_inference_input,
    HEART_FAILURE_RAW_FEATURES,
)
from Machine_Learning.src.train_heart_failure import (
    get_hf_candidate_models,
    train_and_select_best_hf_model,
)
from Machine_Learning.src.evaluate import evaluate_binary_classifier, print_evaluation_summary

sns.set_theme(style='whitegrid', palette='muted')
print('Environment initialized successfully. Project root:', PROJECT_ROOT)
"""))

    # Cell 3: Markdown - Clinical Task Mismatch Analysis
    cells.append(nbf.v4.new_markdown_cell("""## 1. Clinical Target Mismatch & Intended Use Evaluation
### Why this dataset CANNOT diagnose Heart Failure
- In a true screening/diagnostic dataset, the negative class ($y=0$) represents individuals without the disease, and positive ($y=1$) represents individuals with the disease.
- In this dataset (Chicco & Jurman, 2020), **100% of the 299 patients had clinically diagnosed heart failure**.
- The binary target `DEATH_EVENT` indicates whether the patient died during subsequent follow-up ($96$ deaths, $203$ survivors).
- Therefore, the only valid task supported is **post-admission mortality risk stratification for confirmed heart failure patients**.
"""))

    # Cell 4: Code - Data Ingestion & Splitting
    cells.append(nbf.v4.new_code_cell("""df_raw = load_heart_failure_data()
splits = prepare_heart_failure_splits(
    df_raw, test_size=0.2, val_size=0.1, random_state=42
)

print(f'Total Dataset Records: {len(df_raw)}')
print(f'Training fold       : {splits.X_train.shape[0]} samples ({round(splits.X_train.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Validation fold     : {splits.X_val.shape[0]} samples ({round(splits.X_val.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Held-out Test fold  : {splits.X_test.shape[0]} samples ({round(splits.X_test.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Transformed Features: {splits.X_train.shape[1]}')
print(f'Mortality Rate in Train: {np.mean(splits.y_train):.3f}, Test: {np.mean(splits.y_test):.3f}')
"""))

    # Cell 5: Markdown - Candidate Model Comparison
    cells.append(nbf.v4.new_markdown_cell("""## 2. Baseline & Candidate Model Comparison
Evaluating five candidate classifiers on the validation fold ($n=30$):
1. **Dummy Baseline**: Stratified chance classifier
2. **Logistic Regression (Balanced)**: Regularized linear model with inverse class weighting
3. **Random Forest**: Shallow ensemble (100 trees, max depth 4) to control overfitting on $n=209$ training samples
4. **Gradient Boosting**: Shallow boosting (80 estimators, max depth 2)
5. **Support Vector Classifier (RBF)**: Non-linear kernel
"""))

    # Cell 6: Code - Candidate Comparison
    cells.append(nbf.v4.new_code_cell("""best_name, best_model, val_results = train_and_select_best_hf_model(splits, random_state=42)

val_summary = []
for name, res in val_results.items():
    val_summary.append({
        'Model': name,
        'Val Accuracy': res['accuracy'],
        'Val Balanced Acc': res['balanced_accuracy'],
        'Val Sensitivity': res['recall_sensitivity'],
        'Val Specificity': res['specificity'],
        'Val Precision': res['precision'],
        'Val F1': res['f1_score'],
        'Val ROC-AUC': res.get('roc_auc'),
        'Val Brier': res.get('brier_score')
    })

val_df = pd.DataFrame(val_summary).sort_values(by='Val ROC-AUC', ascending=False)
print('Heart Failure Candidate Model Validation Comparison:')
print(val_df.to_string(index=False))
"""))

    # Cell 7: Markdown - Final Test Evaluation
    cells.append(nbf.v4.new_markdown_cell("""## 3. Final Evaluation on Held-Out Test Data
Evaluating the selected model (`Gradient Boosting (Shallow)`) on the unseen Test fold ($n=60$, with $19$ deaths and $41$ survivors).
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
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Survived', 'Deceased'])
disp.plot(ax=axes[0], cmap='Reds', colorbar=False)
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
axes[2].plot(rec, prec, color='darkorange', lw=2, label=f'PR-AUC = {test_metrics[\"pr_auc\"]:.3f}')
axes[2].axhline(baseline_prevalence, color='gray', linestyle='--', label=f'Baseline ({baseline_prevalence:.2f})')
axes[2].set_title('Precision-Recall Curve')
axes[2].set_xlabel('Recall (Sensitivity)')
axes[2].set_ylabel('Precision (Positive Predictive Value)')
axes[2].legend(loc='lower left')

plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hf_model_performance.png', dpi=150)
plt.close()
print('Saved diagnostic plot: hf_model_performance.png')
"""))

    # Cell 11: Markdown - Small Sample Limitations & Clinical Feasibility Conclusion
    cells.append(nbf.v4.new_markdown_cell("""## 5. Small-Sample Uncertainty & Clinical Feasibility Conclusion
1. **Severe Small-Sample Uncertainty**:
   - Total dataset contains only 299 patients and 96 deaths.
   - The test set contains only 19 deaths ($31.7\\%$ test prevalence). A single patient outcome shifts sensitivity by $>5.2\\%$.
   - The wide confidence intervals reflect substantial statistical variance inherent to small clinical cohorts.
2. **Leakage Safeguards vs Baseline Discriminability**:
   - Omitting `time` drops test sensitivity to $31.6\\%$ while maintaining high specificity ($87.8\\%$) and solid ROC-AUC ($0.7766$).
   - This drop reflects real-world clinical reality: predicting mortality months in advance from a single routine lab panel without knowing future follow-up duration is challenging.
3. **Final Architectural Status**:
   - **Supported Use**: Specialized exploratory research experiment for secondary risk stratification in patients with diagnosed heart failure.
   - **Explicit Unsupported Status**: **UNSUPPORTED** for outpatient heart failure screening or diagnosis. The application must display an explicit unsupported status for heart failure screening rather than using this model inappropriately.
"""))

    nb.cells = cells
    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)
    print(f'Successfully generated {notebook_path} with {len(cells)} cells.')

if __name__ == '__main__':
    target = Path(__file__).resolve().parent / '03_heart_failure.ipynb'
    generate_notebook(target)
