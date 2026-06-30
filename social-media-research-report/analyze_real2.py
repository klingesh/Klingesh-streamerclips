# -*- coding: utf-8 -*-
"""
Analysis of REAL responses: Impact of Social Media on Consumer Buying Behaviour.
Likert items already numeric 1-5. Composite = mean of all 22 attitude statements.
Tests: T-test (Influence by Gender), ANOVA (Influence by Age), plus ANOVA by Income,
correlation, reliability, item means. Only consenting respondents are analysed.
"""
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("real_responses2.csv")
df.columns = [c.strip() for c in df.columns]

col_consent = "Do you voluntarily agree to participate in this research?"
col_age = "Age"; col_gender = "Gender"; col_edu = "Highest Educational Qualification"
col_occ = "Occupation"; col_income = "Monthly Income"
col_platform = "Which social media platform do you use most?"
col_time = "How much time do you spend on social media daily?"
col_purchased = "Have you ever purchased a product after seeing it on social media?"
col_prodtype = "Which type of products do you purchase most through social media?"

# Consent filter
before = len(df)
df[col_consent] = df[col_consent].astype(str).str.strip().str.lower()
consent_counts = df[col_consent].value_counts()
df = df[df[col_consent] == "yes"].copy()
print(f"Consent: total={before}, yes={len(df)}  ({dict(consent_counts)})")

# Likert items: statements between product-type col and 'Email address'
all_cols = list(df.columns)
start = all_cols.index(col_prodtype) + 1
likert_cols = []
for c in all_cols[start:]:
    if c.lower().startswith("email") or c.lower().startswith("column"):
        continue
    s = pd.to_numeric(df[c], errors="coerce")
    if s.notna().mean() > 0.8 and s.dropna().between(1, 5).mean() > 0.9:
        df[c] = s
        likert_cols.append(c)
# drop exact duplicate column (the ".1" repeat)
seen, uniq = set(), []
for c in likert_cols:
    base = c.rstrip(" .1")
    if base in seen:   # duplicate statement
        continue
    seen.add(base); uniq.append(c)
likert_cols = uniq
print(f"Likert statements used: {len(likert_cols)}")

df["Influence_Score"] = df[likert_cols].mean(axis=1)

def cronbach_alpha(frame):
    frame = frame.dropna(); k = frame.shape[1]
    return (k/(k-1))*(1 - frame.var(axis=0, ddof=1).sum()/frame.sum(axis=1).var(ddof=1))

print("="*70)
print(f"ANALYSED RESPONDENTS: {len(df)}")
print(f"Overall Mean Influence Score = {df['Influence_Score'].mean():.3f} (sd {df['Influence_Score'].std(ddof=1):.3f})")
print(f"Cronbach's alpha (22-item scale) = {cronbach_alpha(df[likert_cols]):.3f}")
print("="*70)

def pct(col, title):
    vc = df[col].astype(str).str.strip().value_counts()
    p = (vc/vc.sum()*100).round(1)
    print(f"\nTABLE - {title}")
    for idx in vc.index:
        print(f"  {idx:<28} {vc[idx]:>4}  {p[idx]:>5}%")
    return vc, p

print("\n#### PERCENTAGE ANALYSIS ####")
for c,t in [(col_age,"Age"),(col_gender,"Gender"),(col_edu,"Education"),(col_occ,"Occupation"),
            (col_income,"Monthly Income"),(col_platform,"Platform"),(col_time,"Daily Time"),
            (col_purchased,"Purchased via Social Media"),(col_prodtype,"Product Type")]:
    pct(c, t)

print("\n#### ITEM-WISE MEANS ####")
for c in likert_cols:
    s = df[c]
    print(f"  {s.mean():.2f} (sd {s.std(ddof=1):.2f})  {c}")

# ---- T-TEST: Influence by Gender (Male vs Female) ----
print("\n#### T-TEST: Influence Score by Gender ####")
g = df[col_gender].astype(str).str.strip()
m = df.loc[g=="Male","Influence_Score"].dropna()
f = df.loc[g=="Female","Influence_Score"].dropna()
t,pt = stats.ttest_ind(m,f,equal_var=False)
print(f"  Male:   n={len(m)} mean={m.mean():.3f} sd={m.std(ddof=1):.3f}")
print(f"  Female: n={len(f)} mean={f.mean():.3f} sd={f.std(ddof=1):.3f}")
print(f"  t={t:.3f}  p={pt:.4f}  -> {'REJECT H0 (significant)' if pt<0.05 else 'ACCEPT H0 (not significant)'}")

# ---- ANOVA: Influence by Age ----
print("\n#### ANOVA: Influence Score by Age ####")
age_order = ["Below 18","18–24","25–34","35–44","45–54","55 and above"]
a = df[col_age].astype(str).str.strip()
present = [o for o in age_order if (a==o).any()]
groups = [df.loc[a==o,"Influence_Score"].dropna() for o in present]
for o,gr in zip(present,groups):
    print(f"  {o:<14} n={len(gr):<4} mean={gr.mean():.3f} sd={gr.std(ddof=1):.3f}")
F,pf = stats.f_oneway(*groups)
print(f"  F={F:.3f}  p={pf:.4f}  -> {'REJECT H0 (significant)' if pf<0.05 else 'ACCEPT H0 (not significant)'}")

# ---- ANOVA: Influence by Income (supplementary) ----
print("\n#### ANOVA: Influence Score by Income (supplementary) ####")
inc_order = ["Below ₹20,000","₹20,001–₹40,000","₹40,001–₹60,000","₹60,001–₹80,000","Above ₹80,000"]
inc = df[col_income].astype(str).str.strip()
ip = [o for o in inc_order if (inc==o).any()]
ig = [df.loc[inc==o,"Influence_Score"].dropna() for o in ip]
for o,gr in zip(ip,ig):
    print(f"  {o:<18} n={len(gr):<4} mean={gr.mean():.3f} sd={gr.std(ddof=1):.3f}")
Fi,pfi = stats.f_oneway(*ig)
print(f"  F={Fi:.3f}  p={pfi:.4f}  -> {'REJECT H0 (significant)' if pfi<0.05 else 'ACCEPT H0 (not significant)'}")

# save scored data
df.to_csv("real2_scored.csv", index=False)

# ---- Charts ----
def bar(series, title, fname, color, rot=20):
    plt.figure(figsize=(6,4)); series.plot(kind="bar", color=color)
    plt.title(title); plt.ylabel("Count"); plt.xticks(rotation=rot, ha="right")
    plt.tight_layout(); plt.savefig(fname, dpi=120); plt.close()

bar(df[col_gender].value_counts(), "Respondents by Gender", "s_gender.png", "#4C72B0", 0)
bar(df[col_age].astype(str).str.strip().value_counts().reindex([o for o in age_order if o in a.values]).dropna(),
    "Respondents by Age", "s_age.png", "#937860")
bar(df[col_platform].value_counts(), "Most Used Platform", "s_platform.png", "#55A868")
bar(df[col_income].astype(str).str.strip().value_counts().reindex([o for o in inc_order if o in inc.values]).dropna(),
    "Respondents by Monthly Income", "s_income.png", "#8172B3")
bar(df[col_purchased].value_counts(), "Purchased After Seeing on Social Media", "s_purchased.png", "#C44E52", 0)
plt.figure(figsize=(6,4))
df.groupby(a)["Influence_Score"].mean().reindex(present).plot(kind="bar", color="#DD8452")
plt.title("Mean Influence Score by Age"); plt.ylabel("Mean Score"); plt.xticks(rotation=20, ha="right")
plt.tight_layout(); plt.savefig("s_score_by_age.png", dpi=120); plt.close()
print("\nCharts saved.")
