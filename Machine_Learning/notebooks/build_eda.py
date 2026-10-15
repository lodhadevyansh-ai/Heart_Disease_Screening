"""Script to assemble the complete 01_eda.ipynb notebook.
"""

from pathlib import Path
import nbformat as nbf

def generate_eda_notebook(notebook_path: Path):
    nb = nbf.v4.new_notebook()
    cells = []

    # Cell 1: Header
    cells.append(nbf.v4.new_markdown_cell("""# 01 - Exploratory Data Analysis & Dataset Audit
## Heart Disease Screening and Condition-Risk Prediction System

> **Clinical Decision-Support Prototype Note**:
> This notebook conducts a comprehensive, non-destructive audit and exploratory analysis of the three cardiovascular datasets:
> 1. **Heart Disease (UCI)** - Coronary Artery Disease detection and severity
> 2. **Heart Failure Clinical Records** - Follow-up survival/mortality risk analysis
> 3. **Arrhythmia Conditions** - Multiclass electrophysiological categorization from 12-lead ECG
>
> **Mandatory Clinical & Architectural Principles Applied**:
> - Raw data files are preserved strictly unchanged.
> - Separate dataset targets: `DEATH_EVENT` is analyzed as recorded follow-up mortality in heart failure patients, NOT a diagnosis of heart failure.
> - Data leakage risks (such as follow-up `time` in heart failure or site-specific testing variations in UCI) are identified and evaluated.
> - Arrhythmia input requirements (279 ECG waveform metrics) are evaluated against outpatient screening capabilities to prevent unsupported claims.
"""))

    # Cell 2: Imports
    cells.append(nbf.v4.new_code_cell("""import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path('.').resolve().parent.parent if Path('.').resolve().name == 'notebooks' else Path('.').resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Machine_Learning.src.data_loader import (
    load_heart_disease_data,
    load_heart_failure_data,
    load_arrhythmia_data,
    audit_all_datasets
)

sns.set_theme(style='whitegrid', palette='muted')
print('Environment initialized successfully. Project root:', PROJECT_ROOT)
"""))

    # Cell 3: Unified Audit Header
    cells.append(nbf.v4.new_markdown_cell("""## 1. Unified Dataset Audit
Running non-destructive statistical audit across all three datasets using `Machine_Learning.src.data_loader.audit_all_datasets()`.
"""))

    # Cell 4: Unified Audit Code
    cells.append(nbf.v4.new_code_cell("""raw_data_dir = PROJECT_ROOT / 'Machine_Learning' / 'datasets' / 'raw'
audit_results = audit_all_datasets(raw_data_dir)
audit_summary = []

for name, report in audit_results.items():
    audit_summary.append({
        'Dataset': name,
        'Rows': report.row_count,
        'Columns': report.column_count,
        'Duplicate Rows': report.duplicate_rows,
        'Target': report.target_column,
        'Distinct Target Values': len(report.target_distribution) if report.target_distribution else 0,
        'Features with Missing Data': len(report.missing_values),
        'Flagged Anomalies': len(report.anomalies)
    })

audit_df = pd.DataFrame(audit_summary)
print(audit_df.to_string(index=False))
"""))

    # Cell 5: Section 2 - Heart Disease UCI
    cells.append(nbf.v4.new_markdown_cell("""## 2. Heart Disease UCI Dataset
### 2.1 Overview & Schema Structure
- **Source**: UCI Machine Learning Repository (Cleveland, Hungary, Switzerland, VA Long Beach).
- **Target**: `num` (0: <50% diameter stenosis; 1 to 4: >=50% diameter stenosis in 1 to 4 major coronary arteries).
- **Clinical Task**: Stratification of coronary artery disease presence and severity.
"""))

    # Cell 6: UCI Loading & Info
    cells.append(nbf.v4.new_code_cell("""df_hd = load_heart_disease_data()
print('Shape:', df_hd.shape)
print('\\nData Types and Null Counts:')
for col in df_hd.columns:
    print(f'  {col:<10}: {str(df_hd[col].dtype):<10} nulls={df_hd[col].isnull().sum()}')
df_hd.head()
"""))

    # Cell 7: UCI Missing Data & Zero-Value Scanning
    cells.append(nbf.v4.new_markdown_cell("""### 2.2 Missing Data & Physiological Zero-Value Scan
In clinical research data, unmeasured lab values are occasionally encoded as 0. Here we scan for explicit `NaN` values and biologically impossible zeros.
"""))

    # Cell 8: UCI Missing Code
    cells.append(nbf.v4.new_code_cell("""missing_counts = df_hd.isnull().sum()
missing_table = pd.DataFrame({
    'Missing Count': missing_counts[missing_counts > 0],
    'Percentage (%)': (missing_counts[missing_counts > 0] / len(df_hd) * 100).round(2)
}).sort_values(by='Missing Count', ascending=False)

print('Explicit Missing Values (NaN):')
print(missing_table)

zero_chol = int((df_hd['chol'] == 0).sum())
zero_trestbps = int((df_hd['trestbps'] == 0).sum())
print(f'\\nImplicit Missing Data (Physiologically impossible zeros):')
print(f'- Serum Cholesterol == 0: {zero_chol} records ({round(zero_chol / len(df_hd) * 100, 2)}%)')
print(f'- Resting Blood Pressure == 0: {zero_trestbps} records ({round(zero_trestbps / len(df_hd) * 100, 2)}%)')
"""))

    # Cell 9: Target Distribution
    cells.append(nbf.v4.new_markdown_cell("""### 2.3 Target Class Distribution (`num`)
The target `num` represents the degree of coronary angiographic stenosis (0 = normal, 1-4 = diseased).
"""))

    # Cell 10: Target Distribution Code
    cells.append(nbf.v4.new_code_cell("""num_counts = df_hd['num'].value_counts().sort_index()
binary_cad = (df_hd['num'] > 0).astype(int).value_counts().rename({0: 'No CAD (num=0)', 1: 'CAD Present (num>=1)'})

print('Multiclass distribution (num 0 to 4):')
print(num_counts)
print('\\nBinary CAD distribution (Presence vs Absence):')
print(binary_cad)

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
num_counts.plot(kind='bar', ax=axes[0], color='cornflowerblue', edgecolor='black')
axes[0].set_title('Heart Disease: Multiclass Severity (num: 0-4)')
axes[0].set_xlabel('Angiographic Severity Stage')
axes[0].set_ylabel('Patient Count')

binary_cad.plot(kind='bar', ax=axes[1], color=['mediumseagreen', 'coral'], edgecolor='black')
axes[1].set_title('Heart Disease: Binary CAD Classification')
axes[1].set_xlabel('Diagnostic Class')
axes[1].set_ylabel('Patient Count')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hd_target_dist.png', dpi=150)
plt.close()
print('Generated figure: hd_target_dist.png')
"""))

    # Cell 11: Numerical Distributions
    cells.append(nbf.v4.new_markdown_cell("""### 2.4 Numerical Feature Distributions & Outliers
Evaluating physiological parameters: `age`, `trestbps`, `chol`, `thalch`, and `oldpeak`.
"""))

    # Cell 12: Numerical Distributions Code
    cells.append(nbf.v4.new_code_cell("""num_cols_hd = ['age', 'trestbps', 'chol', 'thalch', 'oldpeak']
desc_hd = df_hd[num_cols_hd].describe().T[['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]
print('Numerical Summary Statistics:')
print(desc_hd)

fig, axes = plt.subplots(1, 5, figsize=(16, 3.5))
for i, col in enumerate(num_cols_hd):
    sns.boxplot(y=df_hd[col], ax=axes[i], color='lightblue')
    axes[i].set_title(col)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hd_numerical_boxplots.png', dpi=150)
plt.close()
print('Generated figure: hd_numerical_boxplots.png')
"""))

    # Cell 13: Categorical Frequencies
    cells.append(nbf.v4.new_markdown_cell("""### 2.5 Categorical Features & Clinical Testing Sites
Evaluating distributions of `sex`, `dataset` (collection site), `cp` (chest pain type), `restecg`, `slope`, and `thal`.
"""))

    # Cell 14: Categorical Code
    cells.append(nbf.v4.new_code_cell("""cat_cols_hd = ['sex', 'dataset', 'cp', 'restecg', 'slope', 'thal']
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
for i, col in enumerate(cat_cols_hd):
    ax = axes[i // 3, i % 3]
    df_hd[col].value_counts(dropna=False).plot(kind='bar', ax=ax, color='teal', edgecolor='black')
    ax.set_title(f'{col} (Missing: {df_hd[col].isnull().sum()})')
    ax.tick_params(axis='x', rotation=30)
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hd_categorical_dist.png', dpi=150)
plt.close()
print('Generated figure: hd_categorical_dist.png')
"""))

    # Cell 15: Correlation Matrix
    cells.append(nbf.v4.new_markdown_cell("""### 2.6 Numerical Correlation Matrix
Linear correlations between patient vitals, ECG stress indicators, and target severity.
"""))

    # Cell 16: Correlation Matrix Code
    cells.append(nbf.v4.new_code_cell("""corr_hd = df_hd[num_cols_hd + ['num']].corr()
plt.figure(figsize=(7, 5))
sns.heatmap(corr_hd, annot=True, cmap='coolwarm', fmt='.2f', vmin=-1, vmax=1)
plt.title('UCI Heart Disease: Numerical Feature Correlations')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hd_correlation.png', dpi=150)
plt.close()
print('Generated figure: hd_correlation.png')
"""))

    # Cell 17: UCI Leakage and Clinical Findings
    cells.append(nbf.v4.new_markdown_cell("""### 2.7 Key Findings & Clinical Leakage Assessment (UCI Heart Disease)
1. **Hospital Site Protocol Disparities**: Fluoroscopy vessels (`ca`, 611 missing) and thallium scintigraphy (`thal`, 486 missing) were largely restricted to Cleveland patients. Models trained on non-Cleveland patients must avoid catastrophic missing-data artifacts.
2. **Physiological Zero Imputation**: The 172 records with `chol == 0` must be treated as `NaN` and imputed with median or model-based imputers fit strictly on training splits (Rule 9).
3. **Clinical Interpretation**: Maximum achieved heart rate (`thalch`) negatively correlates with CAD presence (-0.40), while ST depression (`oldpeak`) positively correlates (+0.40), reflecting established myocardial ischemia pathophysiology.
"""))

    # Cell 18: Section 3 - Heart Failure
    cells.append(nbf.v4.new_markdown_cell("""## 3. Heart Failure Clinical Records Dataset
### 3.1 Overview & Target Verification
- **Source**: Chicco & Jurman (2020), BMC Medical Informatics and Decision Making.
- **Population**: 299 patients with diagnosed heart failure (NYHA Class III-IV).
- **CRITICAL CLINICAL & ARCHITECTURAL VERIFICATION (Rule 8)**: The target is **`DEATH_EVENT`** (all-cause mortality during follow-up). This dataset does **NOT** diagnose heart failure. It stratifies survival/mortality outcome in confirmed heart failure patients.
"""))

    # Cell 19: HF Loading & Distribution
    cells.append(nbf.v4.new_code_cell("""df_hf = load_heart_failure_data()
print('Shape:', df_hf.shape)
print('Missing values total:', df_hf.isnull().sum().sum())
print('\\nTarget DEATH_EVENT Distribution:')
print(df_hf['DEATH_EVENT'].value_counts())
print(f'Mortality rate in cohort: {round(df_hf[\"DEATH_EVENT\"].mean() * 100, 2)}%')
df_hf.head()
"""))

    # Cell 20: Follow-up Time Leakage Analysis
    cells.append(nbf.v4.new_markdown_cell("""### 3.2 Follow-up `time` & Look-Ahead Leakage Investigation
The feature `time` records the follow-up duration (in days) until death or study exit.
In prospective clinical intake, a clinician does not know how long the patient will be tracked in the future.
Conditioning on `time` produces look-ahead target leakage.
"""))

    # Cell 21: Follow-up Time Code
    cells.append(nbf.v4.new_code_cell("""print('Follow-up Time (days) by Survival Status (DEATH_EVENT):')
print(df_hf.groupby('DEATH_EVENT')['time'].describe())

fig, ax = plt.subplots(figsize=(8, 4))
sns.histplot(data=df_hf, x='time', hue='DEATH_EVENT', kde=True, bins=20, ax=ax, palette=['royalblue', 'crimson'])
ax.set_title('Follow-up Time Distribution by DEATH_EVENT (Evidence of Target Leakage)')
ax.set_xlabel('Follow-up Time (Days)')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hf_time_leakage.png', dpi=150)
plt.close()
print('Generated figure: hf_time_leakage.png')
"""))

    # Cell 22: Clinical Biomarkers
    cells.append(nbf.v4.new_markdown_cell("""### 3.3 Clinical Biomarkers Analysis
Biomarkers: `ejection_fraction`, `serum_creatinine`, `serum_sodium`, `creatinine_phosphokinase`, and `platelets`.
"""))

    # Cell 23: Clinical Biomarkers Code
    cells.append(nbf.v4.new_code_cell("""biomarkers = ['ejection_fraction', 'serum_creatinine', 'serum_sodium', 'creatinine_phosphokinase', 'platelets']
print(df_hf[biomarkers].describe().T[['count', 'mean', 'std', 'min', '50%', 'max']])

fig, axes = plt.subplots(1, 4, figsize=(16, 3.5))
cols_to_plot = ['ejection_fraction', 'serum_creatinine', 'serum_sodium', 'creatinine_phosphokinase']
for i, col in enumerate(cols_to_plot):
    sns.boxplot(x='DEATH_EVENT', y=col, data=df_hf, ax=axes[i], palette=['skyblue', 'lightcoral'])
    axes[i].set_title(f'{col} vs DEATH_EVENT')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hf_biomarkers.png', dpi=150)
plt.close()
print('Generated figure: hf_biomarkers.png')
"""))

    # Cell 24: HF Correlation Matrix
    cells.append(nbf.v4.new_markdown_cell("""### 3.4 Correlation Matrix (Heart Failure)
Evaluates pairwise correlations among biomarkers, demographics, `time`, and `DEATH_EVENT`.
"""))

    # Cell 25: HF Correlation Code
    cells.append(nbf.v4.new_code_cell("""corr_hf = df_hf.corr()
plt.figure(figsize=(9, 7))
sns.heatmap(corr_hf, annot=True, cmap='coolwarm', fmt='.2f', vmin=-1, vmax=1)
plt.title('Heart Failure Records: Correlation Heatmap')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'hf_correlation.png', dpi=150)
plt.close()
print('Generated figure: hf_correlation.png')
"""))

    # Cell 26: HF Key Findings & Feasibility
    cells.append(nbf.v4.new_markdown_cell("""### 3.5 Key Findings & Feasibility Guidelines (Heart Failure)
1. **Target Semantics**: The model predicts mortality hazard among patients with established heart failure. It must be presented strictly as "Heart Failure Follow-up Mortality Risk", never as "Heart Failure Diagnostic Probability".
2. **Leakage Elimination**: In prospective screening models, `time` must either be omitted from baseline predictors or modeled strictly through survival analysis horizons (e.g. 6-month or 1-year mortality probability).
3. **Core Predictive Biomarkers**: Ejection fraction (negatively correlated, r=-0.27) and serum creatinine (positively correlated, r=+0.29) carry the greatest physiological predictive power.
"""))

    # Cell 27: Section 4 - Arrhythmia
    cells.append(nbf.v4.new_markdown_cell("""## 4. Arrhythmia Conditions Dataset
### 4.1 Overview & Schema Structure
- **Source**: UCI Arrhythmia Database (Guvenir et al.).
- **Shape**: 430 instances, 280 columns (features `'0'` to `'278'` and target `'condition_group'`).
- **Input Breakdown**:
  - Columns 0-14: Age, Sex, Height, Weight, ECG Intervals (QRS, P-R, Q-T, T, P), Vector Angles (QRS, T, P, QRST, J), Heart Rate.
  - Columns 15-278: 12-lead ECG waveform amplitudes, durations, deflections across 12 standard leads (DI, DII, DIII, AVR, AVL, AVF, V1, V2, V3, V4, V5, V6).
"""))

    # Cell 28: Arrhythmia Loading & Class Counts
    cells.append(nbf.v4.new_code_cell("""df_arr = load_arrhythmia_data()
print('Shape:', df_arr.shape)
target_counts = df_arr['condition_group'].value_counts()
print('\\nTarget condition_group distribution:')
print(target_counts)

fig, ax = plt.subplots(figsize=(8, 4))
target_counts.plot(kind='barh', ax=ax, color='darkorchid', edgecolor='black')
ax.set_title('Arrhythmia Dataset: Condition Group Class Distribution')
ax.set_xlabel('Patient Count')
ax.set_ylabel('Condition Group')
plt.tight_layout()
plt.savefig(PROJECT_ROOT / 'Machine_Learning' / 'notebooks' / 'arrhythmia_classes.png', dpi=150)
plt.close()
print('Generated figure: arrhythmia_classes.png')
"""))

    # Cell 29: Arrhythmia Missingness
    cells.append(nbf.v4.new_markdown_cell("""### 4.2 Missing Data Profiling
Evaluation of missingness across features.
"""))

    # Cell 30: Arrhythmia Missingness Code
    cells.append(nbf.v4.new_code_cell("""arr_missing = df_arr.isnull().sum()
arr_missing_table = pd.DataFrame({
    'Feature': arr_missing[arr_missing > 0].index,
    'Missing Count': arr_missing[arr_missing > 0].values,
    'Missing %': (arr_missing[arr_missing > 0].values / len(df_arr) * 100).round(2)
})
print('Features with missing values:')
print(arr_missing_table.to_string(index=False))
"""))

    # Cell 31: Arrhythmia Outliers
    cells.append(nbf.v4.new_markdown_cell("""### 4.3 Physical Outlier & Data Entry Anomaly Scan
Inspection of feature 2 (Height) reveals extreme values.
"""))

    # Cell 32: Arrhythmia Outliers Code
    cells.append(nbf.v4.new_code_cell("""height_outliers = df_arr[df_arr['2'] > 250][['0', '1', '2', '3', 'condition_group']]
print('Extreme Height values (>250 cm):')
print(height_outliers)
"""))

    # Cell 33: Arrhythmia Input Feasibility
    cells.append(nbf.v4.new_markdown_cell("""### 4.4 Critical Architectural Feasibility Assessment: 12-Lead ECG vs Outpatient Screening
- **Required Inputs**: The arrhythmia dataset requires **279 quantitative numerical features derived from 12-lead ECG waveforms** (QRS duration, intervals, vector angles, and lead deflections).
- **Clinical Intake Reality**: Outpatient screening questionnaires capture symptoms (palpitations, dizziness, chest fluttering) and vitals (resting heart rate, blood pressure). They do **NOT** provide 279 digitized ECG waveform deflection amplitudes.
- **Rule 7 & 20 Mandate**: The application must **NEVER** claim to predict arrhythmia condition groups from patient symptom questions or routine lab values without digitized 12-lead ECG data.
- **System Architecture Recommendation**:
  1. The arrhythmia prediction pipeline is designated for **ECG-Assisted Assessment mode**.
  2. In the absence of 12-lead ECG inputs, the system safely renders an **Explicit Unsupported Status** (`Status: PENDING_ECG`), routing the patient through symptom-based clinical safety triage rules instead of fabricating an ML output.
"""))

    # Cell 34: Section 5 - Cross Dataset Synthesis
    cells.append(nbf.v4.new_markdown_cell("""## 5. Cross-Dataset Synthesis & Modeling Guidelines
1. **Target Independence (Rule 11)**: The three datasets cannot be merged into a single arbitrary "total cardiovascular risk score". They address distinct medical tasks:
   - **Heart Disease UCI**: Diagnostic probability of coronary artery disease (>50% stenosis).
   - **Heart Failure Clinical**: Prognostic survival / mortality risk in known heart failure patients.
   - **Arrhythmia Conditions**: Electrophysiological classification of 12-lead ECG waveforms.
2. **Leakage Control**: Preprocessing pipelines must strictly fit all imputation, scaling, and encoding on training folds only.
3. **Phase 2 Status**: Data exploration, audit, and documentation are complete. Ready for pipeline implementation.
"""))

    nb.cells = cells
    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbf.write(nb, f)
    print(f'Successfully generated {notebook_path} with {len(cells)} cells.')

if __name__ == '__main__':
    target = Path(__file__).resolve().parent / '01_eda.ipynb'
    generate_eda_notebook(target)
