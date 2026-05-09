import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import (mean_absolute_error, r2_score,
                             classification_report, confusion_matrix)
from sklearn.preprocessing import LabelEncoder
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

def train_model():
    print("=" * 60)
    print("TOURISM RISK SYSTEM — MODEL TRAINING REPORT")
    print("=" * 60)

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    # ── STEP 1: LOAD DATA ──
    print("\n[STEP 1] Loading master dataset...")
    df = pd.read_csv("data/master_dataset.csv")
    print(f"  Total records: {len(df)}")
    print(f"  Total columns: {len(df.columns)}")

    # ── STEP 2: ENCODE CATEGORICAL COLUMNS ──
    print("\n[STEP 2] Encoding categorical columns...")
    
    le_category = LabelEncoder()
    le_season = LabelEncoder()
    le_district = LabelEncoder()
    le_risk = LabelEncoder()

    df['category_encoded'] = le_category.fit_transform(df['category'])
    df['season_encoded'] = le_season.fit_transform(df['season'])
    df['district_encoded'] = le_district.fit_transform(df['district'])
    df['risk_encoded'] = le_risk.fit_transform(df['risk_level'])

    print(f"  Category classes: {list(le_category.classes_)}")
    print(f"  Season classes:   {list(le_season.classes_)}")
    print(f"  Risk classes:     {list(le_risk.classes_)}")

    # ── STEP 3: DEFINE FEATURES ──
    print("\n[STEP 3] Defining features...")
    
    FEATURES = [
        'day_of_week',
        'month',
        'is_weekend',
        'is_public_holiday',
        'is_festival_period',
        'avg_temperature_c',
        'avg_rainfall_mm',
        'daily_flights_at_cmb',
        'capacity_per_day',
        'category_encoded',
        'season_encoded',
        'district_encoded',
        'is_eco_friendly',
        'is_unesco',
        'entrance_fee_lkr'
    ]

    available = [f for f in FEATURES if f in df.columns]
    missing = [f for f in FEATURES if f not in df.columns]
    
    print(f"  Features available: {len(available)}")
    if missing:
        print(f"  Features missing: {missing}")

    X = df[available]
    y_score = df['crowd_score_normalized']
    y_risk = df['risk_encoded']

    print(f"  Feature matrix shape: {X.shape}")
    print(f"  Target (regression) shape: {y_score.shape}")
    print(f"  Target (classification) shape: {y_risk.shape}")

    # ── STEP 4: TRAIN TEST SPLIT ──
    print("\n[STEP 4] Splitting data 80/20...")
    
    X_train, X_test, y_score_train, y_score_test = train_test_split(
        X, y_score, test_size=0.2, random_state=42
    )
    _, _, y_risk_train, y_risk_test = train_test_split(
        X, y_risk, test_size=0.2, random_state=42
    )

    print(f"  Training set: {len(X_train)} records ({len(X_train)/len(X)*100:.0f}%)")
    print(f"  Test set:     {len(X_test)} records ({len(X_test)/len(X)*100:.0f}%)")

    # ── STEP 5: BASELINE MODEL ──
    print("\n[STEP 5] Building baseline model...")
    
    baseline_pred = np.full(len(y_score_test), y_score_train.mean())
    baseline_mae = mean_absolute_error(y_score_test, baseline_pred)
    baseline_r2 = r2_score(y_score_test, baseline_pred)
    
    print(f"  Baseline always predicts mean: {y_score_train.mean():.4f}")
    print(f"  Baseline MAE: {baseline_mae:.4f}")
    print(f"  Baseline R2:  {baseline_r2:.4f}")

    # ── STEP 6: TRAIN REGRESSION MODEL ──
    print("\n[STEP 6] Training Random Forest Regression model...")
    
    rf_regressor = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_regressor.fit(X_train, y_score_train)
    
    y_pred_score = rf_regressor.predict(X_test)
    mae = mean_absolute_error(y_score_test, y_pred_score)
    r2 = r2_score(y_score_test, y_pred_score)

    print(f"\n  === REGRESSION RESULTS ===")
    print(f"  MAE:  {mae:.4f}  (target <= 0.25) {'PASSED' if mae <= 0.25 else 'FAILED'}")
    print(f"  R2:   {r2:.4f}  (target >= 0.70) {'PASSED' if r2 >= 0.70 else 'FAILED'}")
    print(f"\n  Improvement over baseline:")
    print(f"  MAE improved: {((baseline_mae - mae) / baseline_mae * 100):.1f}%")
    print(f"  R2  improved: {r2 - baseline_r2:.4f} points")

    # ── STEP 7: CROSS VALIDATION ──
    print("\n[STEP 7] Running 5-fold cross validation...")
    
    cv_mae_scores = cross_val_score(
        rf_regressor, X, y_score,
        cv=5, scoring='neg_mean_absolute_error', n_jobs=-1
    )
    cv_r2_scores = cross_val_score(
        rf_regressor, X, y_score,
        cv=5, scoring='r2', n_jobs=-1
    )

    cv_mae = -cv_mae_scores.mean()
    cv_mae_std = cv_mae_scores.std()
    cv_r2 = cv_r2_scores.mean()
    cv_r2_std = cv_r2_scores.std()

    print(f"\n  5-Fold Cross Validation Results:")
    print(f"  CV MAE: {cv_mae:.4f} (+/- {cv_mae_std:.4f})")
    print(f"  CV R2:  {cv_r2:.4f} (+/- {cv_r2_std:.4f})")
    print(f"\n  Individual fold MAE scores:")
    for i, score in enumerate(-cv_mae_scores):
        print(f"  Fold {i+1}: {score:.4f}")
    print(f"\n  Model is {'STABLE' if cv_mae_std < 0.05 else 'VARIABLE'} across folds")

    # ── STEP 8: HYPERPARAMETER TUNING ──
    print("\n[STEP 8] Hyperparameter tuning with Grid Search...")
    print("  Testing parameter combinations...")
    
    param_grid = {
        'n_estimators': [50, 100, 150],
        'max_depth': [8, 10, 12],
        'min_samples_split': [3, 5, 7]
    }
    
    grid_search = GridSearchCV(
        RandomForestRegressor(random_state=42, n_jobs=-1),
        param_grid,
        cv=3,
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        verbose=0
    )
    grid_search.fit(X_train, y_score_train)
    
    best_params = grid_search.best_params_
    print(f"\n  Best hyperparameters found:")
    for param, value in best_params.items():
        print(f"  {param}: {value}")
    
    best_score = -grid_search.best_score_
    print(f"  Best CV MAE: {best_score:.4f}")

    # Retrain with best params
    print("\n  Retraining with best hyperparameters...")
    rf_regressor = RandomForestRegressor(
        n_estimators=best_params['n_estimators'],
        max_depth=best_params['max_depth'],
        min_samples_split=best_params['min_samples_split'],
        random_state=42,
        n_jobs=-1
    )
    rf_regressor.fit(X_train, y_score_train)
    
    y_pred_score = rf_regressor.predict(X_test)
    mae_tuned = mean_absolute_error(y_score_test, y_pred_score)
    r2_tuned = r2_score(y_score_test, y_pred_score)
    
    print(f"\n  Tuned Model Results:")
    print(f"  MAE: {mae_tuned:.4f} (was {mae:.4f})")
    print(f"  R2:  {r2_tuned:.4f} (was {r2:.4f})")

    # Use best values
    mae = mae_tuned
    r2 = r2_tuned

    # ── STEP 9: TRAIN CLASSIFICATION MODEL ──
    print("\n[STEP 9] Training Random Forest Classification model...")
    
    rf_classifier = RandomForestClassifier(
        n_estimators=best_params['n_estimators'],
        max_depth=best_params['max_depth'],
        min_samples_split=best_params['min_samples_split'],
        random_state=42,
        n_jobs=-1
    )
    rf_classifier.fit(X_train, y_risk_train)
    y_pred_risk = rf_classifier.predict(X_test)

    print(f"\n  === CLASSIFICATION RESULTS ===")
    print(classification_report(
        y_risk_test, y_pred_risk,
        target_names=le_risk.classes_
    ))

    # ── STEP 10: CONFUSION MATRIX ──
    print("\n[STEP 10] Generating confusion matrix...")
    
    cm = confusion_matrix(y_risk_test, y_pred_risk)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, cmap='Blues')
    
    classes = le_risk.classes_
    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes, fontsize=12)
    ax.set_yticklabels(classes, fontsize=12)
    
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, str(cm[i, j]),
                   ha='center', va='center',
                   fontsize=14, fontweight='bold',
                   color='white' if cm[i, j] > cm.max() / 2 else 'black')
    
    ax.set_xlabel('Predicted Risk Level', fontsize=12)
    ax.set_ylabel('Actual Risk Level', fontsize=12)
    ax.set_title('Confusion Matrix — Risk Level Classification\nTourism Risk & Context Intelligence System', fontsize=12)
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig("outputs/confusion_matrix.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  Confusion matrix saved: outputs/confusion_matrix.png")

    # ── STEP 11: ACTUAL VS PREDICTED PLOT ──
    print("\n[STEP 11] Generating actual vs predicted plot...")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Scatter plot — actual vs predicted
    sample_size = min(500, len(y_score_test))
    idx = np.random.choice(len(y_score_test), sample_size, replace=False)
    
    actual_sample = y_score_test.iloc[idx]
    predicted_sample = y_pred_score[idx]
    
    axes[0].scatter(actual_sample, predicted_sample, alpha=0.4, color='#3b82f6', s=20)
    axes[0].plot([0, 1], [0, 1], 'r--', linewidth=2, label='Perfect prediction')
    axes[0].set_xlabel('Actual Crowd Score', fontsize=11)
    axes[0].set_ylabel('Predicted Crowd Score', fontsize=11)
    axes[0].set_title(f'Actual vs Predicted Crowd Score\nMAE={mae:.4f}, R²={r2:.4f}', fontsize=11)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Bar chart — baseline vs RF comparison
    models = ['Baseline\n(Mean)', 'Random Forest\n(Tuned)']
    mae_scores = [baseline_mae, mae]
    r2_scores = [baseline_r2, r2]
    
    x = np.arange(2)
    width = 0.35
    
    bars1 = axes[1].bar(x - width/2, mae_scores, width, label='MAE (lower=better)', color=['#ef4444', '#22c55e'])
    bars2 = axes[1].bar(x + width/2, r2_scores, width, label='R² (higher=better)', color=['#f59e0b', '#3b82f6'])
    
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(models, fontsize=11)
    axes[1].set_title('Baseline vs Random Forest Comparison', fontsize=11)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis='y')
    
    for bar in bars1:
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    for bar in bars2:
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig("outputs/actual_vs_predicted.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  Actual vs predicted plot saved: outputs/actual_vs_predicted.png")

    # ── STEP 12: FEATURE IMPORTANCE ──
    print("\n[STEP 12] Generating feature importance chart...")
    
    importance_df = pd.DataFrame({
        'feature': available,
        'importance': rf_regressor.feature_importances_
    }).sort_values('importance', ascending=True)

    colors = ['#3b82f6' if f == 'daily_flights_at_cmb' else '#6366f1' for f in importance_df['feature']]
    
    fig, ax = plt.subplots(figsize=(10, 8))
    bars = ax.barh(importance_df['feature'], importance_df['importance'], color=colors)
    ax.set_xlabel('Feature Importance Score (Gini)', fontsize=11)
    ax.set_title('Random Forest Feature Importance\nTourism Risk & Context Intelligence System\n(Blue = Key Novelty Feature)', fontsize=11)
    
    for bar, val in zip(bars, importance_df['importance']):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2,
               f'{val:.3f}', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig("outputs/feature_importance.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  Feature importance chart saved: outputs/feature_importance.png")

    # ── STEP 13: SHAP ANALYSIS ──
    print("\n[STEP 13] Running SHAP analysis...")
    
    explainer = shap.TreeExplainer(rf_regressor)
    shap_sample = X_test.iloc[:200]
    shap_values = explainer.shap_values(shap_sample)

    # SHAP Summary Plot
    plt.figure(figsize=(10, 8))
    shap.summary_plot(
        shap_values, shap_sample,
        feature_names=available,
        show=False
    )
    plt.title("SHAP Feature Importance\nTourism Risk & Context Intelligence System", fontsize=12)
    plt.tight_layout()
    plt.savefig("outputs/shap_summary_plot.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  SHAP summary plot saved: outputs/shap_summary_plot.png")

    # SHAP Bar Plot
    plt.figure(figsize=(10, 6))
    shap.summary_plot(
        shap_values, shap_sample,
        feature_names=available,
        plot_type="bar",
        show=False
    )
    plt.title("SHAP Mean Feature Impact\nTourism Risk & Context Intelligence System", fontsize=12)
    plt.tight_layout()
    plt.savefig("outputs/shap_bar_plot.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  SHAP bar plot saved: outputs/shap_bar_plot.png")

    # ── STEP 14: SAVE MODELS ──
    print("\n[STEP 14] Saving trained models...")
    
    with open("models/rf_regressor.pkl", "wb") as f:
        pickle.dump(rf_regressor, f)
    with open("models/rf_classifier.pkl", "wb") as f:
        pickle.dump(rf_classifier, f)
    with open("models/risk_encoder.pkl", "wb") as f:
        pickle.dump(le_risk, f)
    with open("models/label_encoders.pkl", "wb") as f:
        pickle.dump({
            'category': le_category,
            'season': le_season,
            'district': le_district
        }, f)

    print("  All models saved to models/ folder")

    # Save metrics to JSON for API
    import json
    metrics = {
        "model_type": "Random Forest",
        "n_estimators": best_params['n_estimators'],
        "max_depth": best_params['max_depth'],
        "min_samples_split": best_params['min_samples_split'],
        "train_records": len(X_train),
        "test_records": len(X_test),
        "features_used": len(available),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "mae_target": 0.25,
        "r2_target": 0.70,
        "mae_achieved": bool(mae <= 0.25),
        "r2_achieved": bool(r2 >= 0.70),
        "baseline_mae": round(baseline_mae, 4),
        "baseline_r2": round(baseline_r2, 4),
        "cv_mae": round(cv_mae, 4),
        "cv_mae_std": round(cv_mae_std, 4),
        "cv_r2": round(cv_r2, 4),
        "cv_r2_std": round(cv_r2_std, 4),
        "risk_classes": list(le_risk.classes_),
        "best_params": best_params
    }
    
    with open("models/model_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("  Model metrics saved to models/model_metrics.json")

    # ── FINAL SUMMARY ──
    print("\n" + "=" * 60)
    print("MODEL TRAINING COMPLETE — PP1 SUMMARY")
    print("=" * 60)
    print(f"  Algorithm:        Random Forest")
    print(f"  Training records: {len(X_train)}")
    print(f"  Test records:     {len(X_test)}")
    print(f"  Features used:    {len(available)}")
    print(f"  Best n_estimators:{best_params['n_estimators']}")
    print(f"  Best max_depth:   {best_params['max_depth']}")
    print(f"  Best min_samples: {best_params['min_samples_split']}")
    print(f"")
    print(f"  REGRESSION RESULTS:")
    print(f"  MAE:  {mae:.4f}  (target <= 0.25) {'✅ PASSED' if mae <= 0.25 else '❌ FAILED'}")
    print(f"  R2:   {r2:.4f}  (target >= 0.70) {'✅ PASSED' if r2 >= 0.70 else '❌ FAILED'}")
    print(f"")
    print(f"  CROSS VALIDATION:")
    print(f"  CV MAE: {cv_mae:.4f} +/- {cv_mae_std:.4f}")
    print(f"  CV R2:  {cv_r2:.4f} +/- {cv_r2_std:.4f}")
    print(f"")
    print(f"  BASELINE COMPARISON:")
    print(f"  Baseline MAE: {baseline_mae:.4f}")
    print(f"  RF MAE:       {mae:.4f}")
    print(f"  Improvement:  {((baseline_mae - mae) / baseline_mae * 100):.1f}%")
    print(f"")
    print(f"  OUTPUTS SAVED:")
    print(f"  - outputs/confusion_matrix.png")
    print(f"  - outputs/actual_vs_predicted.png")
    print(f"  - outputs/feature_importance.png")
    print(f"  - outputs/shap_summary_plot.png")
    print(f"  - outputs/shap_bar_plot.png")
    print(f"  - models/model_metrics.json")
    print("=" * 60)
    print("\n  NEXT STEP: Copy all outputs/ images to frontend/public/")

if __name__ == "__main__":
    train_model()