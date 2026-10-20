# 2-minute script (about 255 spoken words)

`[CUE]` = what to click. Start with the app open on the Risk Profile tab, model warmed up.

---

**(Problem, 15 s)**
"Diabetic patients in Sri Lanka live with many risk factors at once: blood pressure, weight,
history, activity, smoking, medication. My component, C3, turns these into one clear,
explained picture, as an estimate, never a diagnosis."

**(Input, 15 s)** `[CUE: tap "Higher-risk example"]`
"Here is a 58-year-old man with high blood pressure and low activity. The app sends his
answers through the team gateway to my C3 service."

**(F1 prediction, 25 s)** `[CUE: result screen appears]`
"Function one: the model estimates his risk band as High. The Diabetic Health Score is 58
out of 100. It combines the model with his lifestyle answers. The score is marked provisional
until a clinician reviews the weights. Because the band is High, the app adds a referral note."

**(F2 explanation, 30 s)** `[CUE: tap "Understand my risk"]`
"Function two: why. SHAP shows which answers raised the estimate, here diagnosed high blood
pressure and BMI. LIME checks it a second way; the two methods agree on four of the top
five factors. The app says clearly: these are contributions, not medical causes."

**(Recommendation, 15 s)** `[CUE: tap "View recommendations"]`
"Recommendations come only from fixed templates for things he can change. They never touch
his medicines."

**(Evidence, 25 s)**
"On 1,058 people never used in training, ROC-AUC is 0.78 without glucose and 0.85 with it.
85 server tests and 37 app tests pass. Every result is saved in PostgreSQL with model and
schema versions. No real patient data is used yet: our ethics application was submitted on
21 September, so this demo uses made-up people and public South Asian data."

**(Next, 5 s)**
"Next: real Sri Lankan lifestyle data after ethics approval, and connecting C1 and C2. Thank you."
