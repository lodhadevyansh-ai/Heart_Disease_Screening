# Empirical Model Evaluation & Experimental Findings

**Project**: Heart Disease Screening and Condition-Risk Prediction System  
**Document**: Empirical Model Evaluation, Experimental Methodology & Dataset Constraints  
**Classification**: Research & Educational Clinical Decision-Support Prototype  
**Date**: October 2026  

---

## 1. Evaluation Methodology

All models were evaluated using rigorous, leakage-free statistical procedures:
1. **Train/Test Stratification**: 80/20 train/test split stratified on the target class distribution.
2. **Preprocessing Isolation**: All transformations (imputation medians, standardization parameters, one-hot encodings) were learned strictly on training partitions and applied to testing partitions without refitting.
3. **Multi-Metric Assessment**: In medical screening, accuracy alone is insufficient. Performance is evaluated across balanced accuracy, sensitivity (recall), specificity, precision (positive predictive value), F1 score, Area Under the ROC Curve (ROC-AUC), Precision-Recall AUC (PR-AUC), Brier score, and Expected Calibration Error (ECE).
4. **Zero Look-Ahead Leakage**: For follow-up mortality tasks, time-to-event tracking variables (`time`) were removed from predictors.

---

## 2. Measured Experimental Results

The following metrics represent strictly empirical, measured outcomes obtained on held-out test splits. No values are extrapolated or assumed.

### 2.1. Task 1: Coronary Artery Disease Classifier (`coronary_artery_disease`)

- **Cohort**: Multi-Center UCI Heart Disease Dataset (Cleveland, Hungary, Long Beach, Switzerland)
- **Algorithm**: Support Vector Classifier with Radial Basis Function (RBF) Kernel
- **Evaluation Partition**: Held-Out Test Split ($N=184$ patients)
- **Target Definition**: Angiographic presence of coronary artery disease ($\ge 50\%$ diameter stenosis in at least one major vessel, `num > 0`)

| Metric | Measured Value | Clinical Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | 81.52% (0.8152) | Overall proportion of correct classifications across all test patients |
| **Balanced Accuracy** | 80.94% (0.8094) | Unweighted mean of sensitivity and specificity, adjusting for class prevalence |
| **Sensitivity (Recall)** | **86.27%** (0.8627) | Ability to detect true positive CAD cases (essential for minimizing missed diagnoses) |
| **Specificity** | 75.61% (0.7561) | Ability to correctly identify individuals without significant CAD |
| **Precision (PPV)** | 81.48% (0.8148) | Likelihood that a positive prediction reflects true angiographic CAD |
| **F1 Score** | 0.8381 | Harmonic mean of precision and sensitivity |
| **ROC-AUC** | **0.8985** | Strong discriminative ability across discrimination thresholds |
| **PR-AUC** | 0.9119 | Area under the precision-recall curve reflecting positive class performance |
| **Brier Score** | **0.1273** | Mean squared difference between predicted probabilities and binary outcomes |
| **Expected Calibration Error (ECE)** | **0.0541** | 5.4% average deviation between predicted probability bins and observed prevalence |
| **Calibration Method** | Platt Scaling (`SVC(probability=True)`) | Output is a mathematically calibrated probability ($0.0 \le P \le 1.0$) |

### 2.2. Task 2: Heart Failure Follow-up Mortality Stratifier (`heart_failure_mortality`)

- **Cohort**: Faisalabad Institute of Cardiology, Pakistan (Ahmad et al., 2020)
- **Algorithm**: Shallow Gradient Boosting Classifier
- **Evaluation Partition**: Held-Out Test Split ($N=60$ patients, 19 mortality events)
- **Target Definition**: All-cause mortality event during post-admission follow-up among hospitalized patients with diagnosed NYHA Class III-IV heart failure (`DEATH_EVENT = 1`)

| Metric | Measured Value | Clinical Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | 70.00% (0.7000) | Overall correct classification rate on held-out cohort |
| **Balanced Accuracy** | 59.73% (0.5973) | Adjusted classification performance accounting for event imbalance |
| **Sensitivity (Recall)** | 31.58% (0.3158) | Low recall on small test set without survival time information |
| **Specificity** | **87.80%** (0.8780) | Strong ability to identify patients who remained stable during follow-up |
| **Precision (PPV)** | 54.55% (0.5455) | Proportion of flagged high-risk predictions that experienced mortality |
| **F1 Score** | 0.4000 | Harmonic balance impacted by modest sensitivity on $N=19$ test events |
| **ROC-AUC** | **0.7766** | Acceptable risk discrimination without look-ahead time features |
| **PR-AUC** | 0.6515 | Precision-recall area on event rate of 31.7% |
| **Brier Score** | 0.1983 | Moderate calibration accuracy on small test sample |
| **Expected Calibration Error (ECE)** | 0.1142 | 11.4% discrepancy; output is presented as an uncalibrated classifier score |
| **Calibration Status** | Uncalibrated Raw Score | Output is explicitly labeled as a confidence score, NOT a calibrated probability |

### 2.3. Task 3: Cardiac Arrhythmia 12-Lead ECG Classifier (`arrhythmia_ecg`)

- **Cohort**: UCI Arrhythmia Database (Guvenir et al.)
- **Algorithm**: Balanced Random Forest (Max Depth: 6)
- **Evaluation Partition**: Held-Out Test Split ($N=87$ patients)
- **Target Definition**: 5-class categorization of quantitative 12-lead ECG waveform measurements:
  - Class 0: Normal ECG
  - Class 1: Ischemic Changes (Coronary Artery Disease)
  - Class 2: Old Myocardial Infarction
  - Class 3: Conduction Disturbances / Bundle Branch Blocks
  - Class 4: Other Cardiac Arrhythmias

| Metric | Measured Value | Clinical Interpretation |
| :--- | :--- | :--- |
| **Overall Accuracy** | 67.44% (0.6744) | Multiclass classification accuracy across all 5 electrophysiological groups |
| **Balanced Accuracy** | 48.84% (0.4884) | Average accuracy across individual condition classes |
| **Macro F1 Score** | 0.4789 | Unweighted mean F1 score across rare and common rhythm classes |
| **Weighted F1 Score** | 0.6559 | Prevalence-weighted F1 reflecting dominant classes |
| **Macro ROC-AUC (OvR)** | **0.9016** | One-vs-Rest area under ROC curve across multi-class boundaries |
| **Calibration Status** | Uncalibrated Vote Fractions | Class probability vector represents decision tree leaf proportions |

---

## 3. Dataset Constraints & Critical Limitations

### 3.1. UCI Heart Disease Dataset Constraints
- **Demographic Bias**: The Cleveland cohort predominantly comprises male patients (approx. 70%) admitted to tertiary hospital cardiology departments between 1984 and 1988. It does not reflect a modern, primary-care screening demographic.
- **Angiographic Spectrum Bias**: Patients referred for fluoroscopic coronary angiography had clinical suspicion of ischemic heart disease, creating spectrum bias that may inflate sensitivity relative to asymptomatic community screening.
- **Missing Diagnostic Modalities**: Fluoroscopy vessel counts (`ca`) and thallium stress tests (`thal`) were missing in over 50% of records in European centers, necessitating median/mode imputation on non-Cleveland splits.

### 3.2. Heart Failure Dataset Constraints
- **Severity Restriction**: All 299 patients had established NYHA Class III or IV heart failure with reduced ejection fraction ($<40\%$). The model evaluates **post-diagnosis follow-up mortality risk**, not disease onset.
- **Exclusion of `time`**: Prospective screening cannot know how long a patient will survive. Omitting the `time` variable drops nominal model accuracy from $\approx 84\%$ to the realistic, leakage-free **70.0%** reported above.
- **Sample Size ($N=299$)**: Held-out testing on $N=60$ patients with 19 events yields wide 95% confidence intervals ($\approx \pm 12\%$).

### 3.3. Arrhythmia Dataset Constraints
- **Extreme Feature Dimensionality**: 279 features for 430 total records ($N/P < 2$). Despite variance thresholding, high dimensionality limits generalizability without automated feature extraction from raw signal waveforms.
- **Outpatient Inapplicability**: This model cannot run without digitized 12-lead ECG features (QRS duration, PR interval, P wave amplitude). Patient-reported palpitations alone cannot be passed to this model.

---

## 4. Scientific Honesty & Regulatory Boundary

> [!CAUTION]
> **Regulatory Notice**: These models have been developed and evaluated for educational, research, and algorithmic transparency purposes. They have **not** undergone prospective clinical trials, randomized controlled validation, or regulatory clearance (e.g., FDA 510(k), CE mark) as Software as a Medical Device (SaMD). They must **never** be used as autonomous diagnostic agents or to replace licensed clinical judgment.
