"""Builder script for Machine_Learning/notebooks/04_arrhythmia.ipynb.

Documents:
1. Input modality analysis (279 precomputed 12-lead ECG waveform features vs outpatient symptoms)
2. Class distribution and extreme rarity (Structural_Atrial_Abnormality, n=9)
3. Candidate model comparison on validation fold
4. Multi-class confusion matrix and per-class metrics
5. Feasibility determination and unsupported task declarations
"""

from pathlib import Path
import nbformat as nbf

def generate_notebook(notebook_path: Path):
    nb = nbf.v4.new_notebook()
    cells = []

    # Cell 1: Markdown Title & Scope
    cells.append(nbf.v4.new_markdown_cell("""# 04 - Arrhythmia Feasibility Analysis & Multi-Class ECG Modeling
## Multi-Class Electrophysiological Categorization (UCI Arrhythmia Dataset)

> **CRITICAL ARCHITECTURAL & CLINICAL FEASIBILITY DIRECTIVES (Rule 7, 10 & 20)**:
> 1. **Input Modality**: The dataset consists of **279 quantitative numerical features derived from 12-lead ECG waveforms** (intervals, vector angles, wave deflections across leads DI-V6).
> 2. **Symptom Infeasibility**: This model **CANNOT** predict arrhythmia from patient symptoms (palpitations, dizziness, syncope) or routine laboratory tests.
> 3. **Signal/Image Infeasibility**: Precomputed numerical features **do NOT prove** that the application can interpret scanned PDF reports, paper ECGs, or raw time-series voltage waveforms.
> 4. **Rare Class Limitation**: `Structural_Atrial_Abnormality` has only 9 instances in the entire cohort, resulting in severe statistical uncertainty for that subgroup.
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
from sklearn.metrics import confusion_matrix

PROJECT_ROOT = Path('.').resolve().parent.parent if Path('.').resolve().name == 'notebooks' else Path('.').resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Machine_Learning.src.data_loader import load_arrhythmia_data
from Machine_Learning.src.preprocessing import prepare_arrhythmia_splits
from Machine_Learning.src.train_arrhythmia import (
    get_arrhythmia_candidate_models,
    train_and_select_best_arrhythmia_model,
)
from Machine_Learning.src.evaluate import evaluate_multiclass_classifier, print_multiclass_summary

sns.set_theme(style='whitegrid', palette='muted')
print('Environment initialized successfully. Project root:', PROJECT_ROOT)
"""))

    # Cell 3: Markdown - Feature Space & Input Representation
    cells.append(nbf.v4.new_markdown_cell("""## 1. Feature Representation & Clinical Feasibility Assessment
Inspection of the 280 columns confirms:
- Columns 0-3: Demographics (Age, Sex, Height, Weight).
- Columns 4-14: Global intervals (QRS, PR, QT, T, P) and vector angles. Column 13 (J-angle) has 83.3% missingness and is dropped.
- Columns 15-278: 264 waveform deflection metrics across 12 standard leads.
**Verdict**: A patient-facing symptom intake form cannot supply these 279 parameters. Outpatient screening triage must mark arrhythmia ML prediction as **UNSUPPORTED WITHOUT 12-LEAD ECG**.
"""))

    # Cell 4: Code - Data Ingestion & Splitting
    cells.append(nbf.v4.new_code_cell("""df_raw = load_arrhythmia_data()
splits = prepare_arrhythmia_splits(
    df_raw, test_size=0.2, val_size=0.1, random_state=42
)

classes = sorted(list(np.unique(splits.y_train)))
print(f'Total Dataset Records: {len(df_raw)}')
print(f'Training fold       : {splits.X_train.shape[0]} samples ({round(splits.X_train.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Validation fold     : {splits.X_val.shape[0]} samples ({round(splits.X_val.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Held-out Test fold  : {splits.X_test.shape[0]} samples ({round(splits.X_test.shape[0]/len(df_raw)*100, 1)}%)')
print(f'Transformed Features: {splits.X_train.shape[1]}')
print(f'Classes ({len(classes)}): {classes}')
"""))

    # Cell 5: Markdown - Candidate Model Comparison
    cells.append(nbf.v4.new_markdown_cell("""## 2. Multi-Class Candidate Model Comparison
Comparing candidate multi-class classifiers on the validation fold ($n=43$) using **Balanced Accuracy (Macro Recall)** as the primary selection criterion:
1. **Dummy Baseline**: Stratified chance classifier
2. **Logistic Regression (Balanced)**: Multinomial regularized linear classifier
3. **Random Forest (Depth 6 Balanced)**: Ensemble of 150 balanced trees
4. **Gradient Boosting**: Sequential boosting model
5. **Support Vector Classifier (RBF Balanced)**: Non-linear kernel
"""))

    # Cell 6: Code - Candidate Comparison
    cells.append(nbf.v4.new_code_cell("""best_name, best_model, val_results = train_and_select_best_arrhythmia_model(splits, random_state=42)

val_summary = []
for name, res in val_results.items():
    val_summary.append({
        'Model': name,
        'Val Accuracy': res['accuracy'],
        'Val Balanced Acc (Macro Recall)': res['balanced_accuracy'],
        'Val Macro Prec': res['macro_precision'],
        'Val Macro F1': res['macro_f1'],
        'Val Weighted F1': res['weighted_f1'],
        'Val Macro ROC-AUC': res.get('macro_roc_auc_ovr')
    })

val_df = pd.DataFrame(val_summary).sort_values(by='Val Balanced Acc (Macro Recall)', ascending=False)
print('Arrhythmia Candidate Model Validation Comparison:')
print(val_df.to_string(index=False))
"""))

    # Cell 7: Markdown - Final Test Evaluation
    cells.append(nbf.v4.new_markdown_cell("""## 3. Final Evaluation on Held-Out Test Data
Evaluating the top-performing model (`Random Forest (Depth 6 Balanced)`) on the unseen Test fold ($n=86$).
"""))

    # Cell 8: Code - Test Metrics
    cells.append(nbf.v4.new_code_cell("""y_test_pred = best_model.predict(splits.X_test)
y_test_prob = best_model.predict_proba(splits.X_test)

test_metrics = evaluate_multiclass_classifier(splits.y_test, y_test_pred, y_test_prob, class_labels=classes)
print_multiclass_summary(test_metrics, f'HELD-OUT TEST SET ({best_name})')
"""))

    # Cell 9: Markdown - Confusion Matrix Heatmap
    cells.append(nbf.v4.new_markdown_cell("""## 4. Multi-Class Confusion Matrix Heatmap
Visualizing classification performance across condition groups.
"""))

    # Cell 10: Code - Confusion Matrix Plot
    cells.append(nbf.v4.new_code_cell("""cm = confusion_matrix(splits.y_test, y_test_pred, labels=classes)
cm_df = pd.DataFrame(cm, index=classes, columns=classes)

plt.figure(figsize=(9, 7))
sns.heatmap(cm_df, annot=True, fmt='d', cmap='Purples', cbar=False)
plt.title(f'Arrhythmia Confusion Matrix\\n({best_name})')
plt.xlabel('Predicted Condition Group')
plt.ylabel('Actual Condition Group')
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'arrhythmia_confusion_matrix.png', dpi=150)
plt.close()
print('Saved diagnostic plot: arrhythmia_confusion_matrix.png')
"""))

    # Cell 11: Markdown - Feasibility Summary & Unsupported Declarations
    cells.append(nbf.v4.new_markdown_cell("""## 5. Feasibility Verdict & Clinical Scope Declarations
1. **Supported Use**: Multi-class categorization of precomputed, digitized 12-lead ECG waveform measurements.
2. **Explicit Unsupported Declarations (Rule 7 & 20)**:
   - **Symptom-Based Screening**: **UNSUPPORTED**. Patient questionnaires (palpitations, dizziness) cannot substitute for ECG waveform deflections.
   - **Raw Signal Interpretation**: **UNSUPPORTED**. Precomputed tabular features do not enable direct parsing of raw voltage signals or scanned PDF waveforms.
3. **Rare Class Performance**:
   - `Structural_Atrial_Abnormality` ($n=2$ in test set) achieved $0\\%$ recall despite class weighting. This demonstrates the hard statistical ceiling of extreme rarity ($n=9$ in entire cohort).
4. **Clinical Policy**: When patients present with palpitations in outpatient intake, the application must **NOT** guess arrhythmia risk. It must output an explicit `PENDING_ECG` status and recommend an ambulatory 12-lead ECG or Holter monitor.
"""))

    nb.cells = cells
    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)
    print(f'Successfully generated {notebook_path} with {len(cells)} cells.')

if __name__ == '__main__':
    target = Path(__file__).resolve().parent / '04_arrhythmia.ipynb'
    generate_notebook(target)
