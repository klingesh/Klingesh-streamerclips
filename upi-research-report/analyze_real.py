"""
Analysis of REAL UPI survey responses (171 respondents).
Likert answers are text -> mapped to 1..5.
Produces: percentage analysis, reliability (Cronbach's alpha), T-test, ANOVA,
correlation, and charts.
"""
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("real_responses.csv")
df = df.drop(columns=[c for c in ["Score"] if c in df.columns])

LIKERT_MAP = {
    "strongly disagree": 1, "disagree": 2, "neutral": 3,
    "agree": 4, "strongly agree": 5,
}
def to_score(x):
    if isinstance(x, str):
        return LIKERT_MAP.get(x.strip().lower(), np.nan)
    return np.nan

col_gender = "Gender"
col_age = "Age"
col_edu = "Educational Qualification"
col_income = "Monthly income"
col_app = "Which UPI app do you use the most?"

cols = list(df.columns)
likert_cols = cols[cols.index(col_app) + 1:]   # everything after the app question
spending_cols = likert_cols[:10]
saving_cols = likert_cols[10:20]

for c in likert_cols:
    df[c] = df[c].map(to_score)

df["Spending_Score"] = df[spending_cols].mean(axis=1)
df["Saving_Score"] = df[saving_cols].mean(axis=1)

def cronbach_alpha(frame):
    frame = frame.dropna()
    k = frame.shape[1]
    item_var = frame.var(axis=0, ddof=1).sum()
    total_var = frame.sum(axis=1).var(ddof=1)
    return (k / (k - 1)) * (1 - item_var / total_var)

print("=" * 70)
print(f"REAL DATA  |  Respondents: {len(df)}")
print("=" * 70)

# ---- Percentage analysis ----
def pct_table(col, title):
    vc = df[col].value_counts()
    pct = (vc / vc.sum() * 100).round(1)
    out = pd.DataFrame({"Respondents": vc, "Percentage": pct})
    print(f"\nTABLE - {title}")
    print(out.to_string())

print("\n" + "#" * 70 + "\nSECTION A: PERCENTAGE ANALYSIS\n" + "#" * 70)
pct_table(col_gender, "Gender")
pct_table(col_age, "Age")
pct_table(col_edu, "Educational Qualification")
pct_table(col_income, "Monthly Income")
pct_table(col_app, "Most Used UPI App")

# ---- Reliability ----
print("\n" + "#" * 70 + "\nSECTION B: RELIABILITY (Cronbach's Alpha)\n" + "#" * 70)
print(f"  Spending scale (10 items): alpha = {cronbach_alpha(df[spending_cols]):.3f}")
print(f"  Saving scale   (10 items): alpha = {cronbach_alpha(df[saving_cols]):.3f}")

print(f"\n  Overall Mean Spending Score = {df['Spending_Score'].mean():.3f} (sd {df['Spending_Score'].std(ddof=1):.3f})")
print(f"  Overall Mean Saving Score   = {df['Saving_Score'].mean():.3f} (sd {df['Saving_Score'].std(ddof=1):.3f})")

# ---- T-test: Spending by Gender ----
print("\n" + "#" * 70 + "\nSECTION C: T-TEST  (Spending Score by Gender)\n" + "#" * 70)
g = df[col_gender].astype(str).str.strip()
x1 = df.loc[g == "Male", "Spending_Score"].dropna()
x2 = df.loc[g == "Female", "Spending_Score"].dropna()
t, p_t = stats.ttest_ind(x1, x2, equal_var=False)
print(f"  Male:   n={len(x1)}, mean={x1.mean():.3f}, sd={x1.std(ddof=1):.3f}")
print(f"  Female: n={len(x2)}, mean={x2.mean():.3f}, sd={x2.std(ddof=1):.3f}")
print(f"  t = {t:.3f} | p-value = {p_t:.4f}")
print("  Decision: " + ("REJECT H0 (significant difference)" if p_t < 0.05 else "ACCEPT H0 (no significant difference)"))

# ---- ANOVA: Saving by Income ----
print("\n" + "#" * 70 + "\nSECTION D: ANOVA  (Saving Score by Income)\n" + "#" * 70)
inc = df[col_income].astype(str).str.strip()
order = ["Below 25000", "25000-50000", "50000-100000", "Above 100000"]
present = [o for o in order if (inc == o).any()]
groups = [df.loc[inc == o, "Saving_Score"].dropna() for o in present]
for o, grp in zip(present, groups):
    print(f"  {o:<16} n={len(grp):<4} mean={grp.mean():.3f}  sd={grp.std(ddof=1):.3f}")
f, p_f = stats.f_oneway(*groups)
print(f"  F = {f:.3f} | p-value = {p_f:.4f}")
print("  Decision: " + ("REJECT H0 (significant difference across income)" if p_f < 0.05 else "ACCEPT H0 (no significant difference)"))

# ---- Correlation ----
print("\n" + "#" * 70 + "\nSECTION E: CORRELATION (Spending vs Saving)\n" + "#" * 70)
mask = df["Spending_Score"].notna() & df["Saving_Score"].notna()
r, p_r = stats.pearsonr(df.loc[mask, "Spending_Score"], df.loc[mask, "Saving_Score"])
print(f"  Pearson r = {r:.3f} | p-value = {p_r:.4f}")

# ---- Charts ----
def bar(series, title, fname, color, rot=0):
    plt.figure(figsize=(6, 4))
    series.plot(kind="bar", color=color)
    plt.title(title); plt.ylabel("Count"); plt.xticks(rotation=rot, ha="right" if rot else "center")
    plt.tight_layout(); plt.savefig(fname, dpi=120); plt.close()

bar(df[col_gender].value_counts(), "Respondents by Gender", "r_gender.png", ["#4C72B0", "#DD8452"])
bar(df[col_age].value_counts(), "Respondents by Age", "r_age.png", "#937860", 20)
bar(df[col_income].value_counts(), "Respondents by Monthly Income", "r_income.png", "#55A868", 25)
bar(df[col_app].value_counts(), "Most Used UPI App", "r_app.png", "#8172B3", 20)

plt.figure(figsize=(6, 4))
df.groupby(inc)["Saving_Score"].mean().reindex(present).plot(kind="bar", color="#C44E52")
plt.title("Mean Saving Score by Income"); plt.ylabel("Mean Saving Score"); plt.xticks(rotation=25, ha="right")
plt.tight_layout(); plt.savefig("r_saving_by_income.png", dpi=120); plt.close()

print("\nCharts saved: r_gender.png, r_age.png, r_income.png, r_app.png, r_saving_by_income.png")
df.to_csv("real_scored.csv", index=False)
print("Scored dataset saved: real_scored.csv")
