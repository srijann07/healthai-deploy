"""AI health analysis engine.

A transparent, rule-based risk engine that turns a patient's symptoms,
vitals and lifestyle habits into:

- an overall risk level (Low / Medium / High / Critical)
- the most likely condition(s) and a recommended specialist
- a confidence score
- tailored health suggestions
- an urgency call-to-action

The engine is deterministic and fully explainable: every point of the
risk score is traceable to a symptom match, an abnormal vital, or a
lifestyle habit. Model version is recorded on each prediction so future
engine versions can be compared.

> Screening guidance only. Never a substitute for professional diagnosis.
"""

MODEL_VERSION = "healthai-rule-engine-v1"

RISK_LOW = "Low"
RISK_MEDIUM = "Medium"
RISK_HIGH = "High"
RISK_CRITICAL = "Critical"

RISK_LEVELS = (RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL)

# --- Symptom catalogue --------------------------------------------------
# Each symptom maps to (condition, weight) pairs. Weights accumulate for a
# condition when several of its symptoms are present.
SYMPTOM_CONDITIONS = {
    "fever": [("Viral infection", 2.5), ("Influenza", 1.0)],
    "cough": [("Upper respiratory infection", 1.5), ("Bronchitis", 1.5)],
    "sore_throat": [("Upper respiratory infection", 1.5)],
    "runny_nose": [("Upper respiratory infection", 1.5)],
    "fatigue": [("Anaemia", 1.5), ("Chronic fatigue", 1.0)],
    "headache": [("Tension headache", 1.5), ("Migraine", 1.0)],
    "dizziness": [("Low blood pressure", 2.0), ("Vertigo", 1.5)],
    "chest_pain": [("Cardiac concern", 3.5), ("Acid reflux", 1.0)],
    "shortness_of_breath": [("Respiratory concern", 3.5), ("Cardiac concern", 2.0)],
    "palpitations": [("Arrhythmia", 3.0)],
    "frequent_urination": [("Diabetes risk", 3.5)],
    "excessive_thirst": [("Diabetes risk", 2.5)],
    "increased_hunger": [("Diabetes risk", 2.0)],
    "unexplained_weight_loss": [("Diabetes risk", 1.5), ("Thyroid imbalance", 1.5)],
    "blurred_vision": [("Diabetes risk", 2.0), ("Vision concern", 1.5)],
    "numbness_limbs": [("Neuropathy risk", 2.5)],
    "joint_pain": [("Arthritis", 2.5)],
    "muscle_aches": [("Viral infection", 1.0)],
    "abdominal_pain": [("Gastritis", 2.0)],
    "nausea": [("Gastritis", 1.5), ("Viral infection", 0.5)],
    "vomiting": [("Gastroenteritis", 2.0)],
    "diarrhea": [("Gastroenteritis", 2.0)],
    "constipation": [("Digestive concern", 1.5)],
    "heartburn": [("Acid reflux", 2.0)],
    "skin_rash": [("Dermatitis", 2.0)],
    "swollen_feet": [("Cardiac concern", 2.5), ("Kidney concern", 2.0)],
    "night_sweats": [("Viral infection", 1.0)],
    "sleep_issues": [("Sleep disorder", 1.5)],
    "anxiety": [("Anxiety disorder", 1.5)],
    "loss_of_appetite": [("Digestive concern", 1.0)],
}

SYMPTOM_LABELS = {
    "fever": "Fever",
    "cough": "Persistent cough",
    "sore_throat": "Sore throat",
    "runny_nose": "Runny nose",
    "fatigue": "Constant fatigue / weakness",
    "headache": "Headache",
    "dizziness": "Dizziness",
    "chest_pain": "Chest pain",
    "shortness_of_breath": "Shortness of breath",
    "palpitations": "Racing or irregular heartbeat",
    "frequent_urination": "Frequent urination",
    "excessive_thirst": "Excessive thirst",
    "increased_hunger": "Increased hunger",
    "unexplained_weight_loss": "Unexplained weight loss",
    "blurred_vision": "Blurred vision",
    "numbness_limbs": "Numbness / tingling in hands or feet",
    "joint_pain": "Joint pain or stiffness",
    "muscle_aches": "Muscle aches",
    "abdominal_pain": "Abdominal pain",
    "nausea": "Nausea",
    "vomiting": "Vomiting",
    "diarrhea": "Diarrhoea",
    "constipation": "Constipation",
    "heartburn": "Heartburn / acidity",
    "skin_rash": "Skin rash",
    "swollen_feet": "Swollen ankles or feet",
    "night_sweats": "Night sweats",
    "sleep_issues": "Difficulty sleeping",
    "anxiety": "Anxiety or excessive stress",
    "loss_of_appetite": "Loss of appetite",
}

# --- Condition -> recommended specialist --------------------------------
CONDITION_SPECIALISTS = {
    "Viral infection": "General Physician",
    "Influenza": "General Physician",
    "Upper respiratory infection": "General Physician",
    "Bronchitis": "Pulmonologist",
    "Pneumonia": "Pulmonologist",
    "Respiratory concern": "Pulmonologist",
    "Cardiac concern": "Cardiologist",
    "Arrhythmia": "Cardiologist",
    "Hypertension": "Cardiologist",
    "Low blood pressure": "General Physician",
    "Diabetes risk": "Endocrinologist",
    "Thyroid imbalance": "Endocrinologist",
    "Migraine": "Neurologist",
    "Tension headache": "General Physician",
    "Vertigo": "ENT Specialist",
    "Neuropathy risk": "Neurologist",
    "Anaemia": "General Physician",
    "Chronic fatigue": "General Physician",
    "Arthritis": "Orthopaedist",
    "Gastritis": "Gastroenterologist",
    "Gastroenteritis": "General Physician",
    "Digestive concern": "Gastroenterologist",
    "Acid reflux": "Gastroenterologist",
    "Dermatitis": "Dermatologist",
    "Kidney concern": "Nephrologist",
    "Sleep disorder": "General Physician",
    "Anxiety disorder": "Psychologist",
    "Vision concern": "Ophthalmologist",
}

# Symptom *combinations* worth extra weight (classic clinical pairings).
_COMBINATION_BONUSES = (
    ({"fever", "cough"}, [("Pneumonia", 3.0)]),
    ({"fever", "fatigue", "muscle_aches"}, [("Viral infection", 1.5)]),
    ({"fever", "night_sweats"}, [("Viral infection", 1.0)]),
    ({"chest_pain", "shortness_of_breath"}, [("Cardiac concern", 3.0)]),
    ({"cough", "fatigue", "shortness_of_breath"}, [("Bronchitis", 2.0)]),
    ({"frequent_urination", "excessive_thirst"}, [("Diabetes risk", 2.0)]),
    ({"frequent_urination", "excessive_thirst", "blurred_vision"}, [("Diabetes risk", 3.0)]),
    ({"headache", "blurred_vision", "nausea"}, [("Migraine", 2.0)]),
    ({"abdominal_pain", "constipation"}, [("Digestive concern", 1.5)]),
    ({"fever", "headache"}, [("Viral infection", 0.5)]),
)

# --- Clinical thresholds -------------------------------------------------
# BP cascade: (systolic limit, diastolic limit, score, condition bonus, critical)
_BP_RANGES = (
    (180, 120, 4.0, [("Hypertension", 3.0)], True),
    (140, 90, 2.5, [("Hypertension", 2.5)], False),
    (130, 85, 1.0, [("Hypertension", 1.0)], False),
)

_AGE_RANGES = ((80, 2.0), (65, 1.5), (50, 0.75))

_SMOKING_WEIGHTS = {"regular": 2.0, "occasional": 0.75, "former": 0.5}
_ALCOHOL_WEIGHTS = {"regular": 1.5, "occasional": 0.5}
_EXERCISE_WEIGHTS = {"never": 1.5, "rarely": 1.0, "few_per_week": 0.5}

# --- Risk thresholds ------------------------------------------------------
_HIGH_THRESHOLD = 9.0
_MEDIUM_THRESHOLD = 4.5
_CRITICAL_THRESHOLD = 14.0

URGENCY = {
    RISK_CRITICAL: "Seek emergency care immediately",
    RISK_HIGH: "Book a consultation within 24-48 hours",
    RISK_MEDIUM: "Consult a doctor within the next 1-2 weeks",
    RISK_LOW: "Routine check-up",
}


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze(inputs: dict) -> dict:
    """Run the risk analysis for one assessment.

    `inputs` may contain any of: symptoms, age, gender, height_cm,
    weight_kg, bmi, systolic_bp, diastolic_bp, heart_rate, blood_sugar,
    body_temperature, oxygen_level, smoking_status, alcohol_consumption,
    exercise_frequency, chronic_conditions, previous_diseases,
    current_medicines, family_history.
    """
    symptoms = [s for s in (inputs.get("symptoms") or []) if s in SYMPTOM_CONDITIONS]
    conditions: dict[str, float] = {}
    total = [0.0]  # mutable accumulator; all risk points land here
    critical_flag = False

    # 1. Symptom matches -------------------------------------------------
    for symptom in symptoms:
        for condition, weight in SYMPTOM_CONDITIONS[symptom]:
            _apply(total, conditions, [(condition, weight)], weight)

    # 2. Combination bonuses ---------------------------------------------
    symptom_set = set(symptoms)
    for combo, bonuses in _COMBINATION_BONUSES:
        if combo <= symptom_set:
            for condition, weight in bonuses:
                _apply(total, conditions, [(condition, weight)], weight)

    # 3. Vitals -----------------------------------------------------------
    sys_bp = _as_float(inputs.get("systolic_bp"))
    dia_bp = _as_float(inputs.get("diastolic_bp"))
    if sys_bp is not None or dia_bp is not None:
        sys_bp = sys_bp or 0
        dia_bp = dia_bp or 0
        matched = False
        for sys_lim, dia_lim, points, bonus, critical in _BP_RANGES:
            if sys_bp >= sys_lim or dia_bp >= dia_lim:
                _apply(total, conditions, bonus, points)
                critical_flag = critical_flag or critical
                matched = True
                break
        if not matched and (sys_bp < 90 or dia_bp < 60):
            _apply(total, conditions, [("Low blood pressure", 1.0)], 0.5)

    heart_rate = _as_float(inputs.get("heart_rate"))
    if heart_rate is not None:
        if heart_rate >= 120:
            _apply(total, conditions, [("Arrhythmia", 1.5)], 2.0)
        elif heart_rate >= 100:
            _apply(total, conditions, [], 1.0)
        elif heart_rate <= 50:
            _apply(total, conditions, [], 1.0)

    sugar = _as_float(inputs.get("blood_sugar"))
    if sugar is not None:
        if sugar >= 200:
            _apply(total, conditions, [("Diabetes risk", 3.0)], 3.5)
            critical_flag = True
        elif sugar >= 126:
            _apply(total, conditions, [("Diabetes risk", 2.0)], 2.5)
        elif sugar >= 100:
            _apply(total, conditions, [("Diabetes risk", 0.5)], 1.0)
        elif sugar <= 70:
            _apply(total, conditions, [], 1.0)

    spo2 = _as_float(inputs.get("oxygen_level"))
    if spo2 is not None:
        if spo2 <= 90:
            _apply(total, conditions, [], 5.0)
            critical_flag = True
        elif spo2 <= 94:
            _apply(total, conditions, [], 3.0)
        elif spo2 <= 96:
            _apply(total, conditions, [], 1.5)

    temperature = _as_float(inputs.get("body_temperature"))
    if temperature is not None:
        if temperature >= 40.0:
            _apply(total, conditions, [], 3.5)
            critical_flag = True
        elif temperature >= 38.0:
            _apply(total, conditions, [], 2.0)
        elif temperature >= 37.5:
            _apply(total, conditions, [], 1.0)
        elif temperature <= 35.5:
            _apply(total, conditions, [], 1.5)

    # 4. Body composition ---------------------------------------------------
    bmi = _as_float(inputs.get("bmi"))
    if bmi is None and inputs.get("height_cm") and inputs.get("weight_kg"):
        height = _as_float(inputs.get("height_cm")) / 100
        weight = _as_float(inputs.get("weight_kg"))
        if height and weight and height > 0:
            bmi = weight / (height ** 2)
    if bmi is not None:
        if bmi >= 35:
            _apply(total, conditions, [], 2.0)
        elif bmi >= 30:
            _apply(total, conditions, [], 1.5)
        elif bmi >= 25:
            _apply(total, conditions, [], 0.5)
        elif bmi < 18.5:
            _apply(total, conditions, [], 1.5)

    # 5. Demographics -------------------------------------------------------
    age = _as_float(inputs.get("age"))
    if age is not None:
        for limit, points in _AGE_RANGES:
            if age >= limit:
                _apply(total, conditions, [], points)
                break
        if age < 5:
            _apply(total, conditions, [], 0.75)

    # 6. Lifestyle habits ---------------------------------------------------
    smoking = (inputs.get("smoking_status") or "").lower()
    if smoking in _SMOKING_WEIGHTS:
        _apply(total, conditions, [], _SMOKING_WEIGHTS[smoking])

    alcohol = (inputs.get("alcohol_consumption") or "").lower()
    if alcohol in _ALCOHOL_WEIGHTS:
        _apply(total, conditions, [], _ALCOHOL_WEIGHTS[alcohol])

    exercise = (inputs.get("exercise_frequency") or "").lower()
    if exercise in _EXERCISE_WEIGHTS:
        _apply(total, conditions, [], _EXERCISE_WEIGHTS[exercise])

    # 7. Medical history ------------------------------------------------------
    if (inputs.get("chronic_conditions") or "").strip():
        _apply(total, conditions, [], 2.0)
    if (inputs.get("previous_diseases") or "").strip():
        _apply(total, conditions, [], 0.5)
    if (inputs.get("current_medicines") or "").strip():
        _apply(total, conditions, [], 0.5)
    if (inputs.get("family_history") or "").strip():
        _apply(total, conditions, [], 0.5)

    score = total[0]

    # 8. Risk level -------------------------------------------------------------
    if critical_flag or score >= _CRITICAL_THRESHOLD:
        risk_level = RISK_CRITICAL
    elif score >= _HIGH_THRESHOLD:
        risk_level = RISK_HIGH
    elif score >= _MEDIUM_THRESHOLD:
        risk_level = RISK_MEDIUM
    else:
        risk_level = RISK_LOW

    # 9. Output selection --------------------------------------------------------
    ranked = sorted(conditions.items(), key=lambda kv: (-kv[1], kv[0]))
    possible_disease = ranked[0][0] if ranked else "No specific condition detected"
    secondary = [c for c, w in ranked[1:] if w >= 1.0][:2]
    specialist = CONDITION_SPECIALISTS.get(possible_disease, "General Physician")

    confidence = _confidence(symptoms, inputs)
    suggestions = _suggestions(inputs, conditions, risk_level, possible_disease)

    return {
        "score": round(score, 2),
        "risk_level": risk_level,
        "urgency": URGENCY[risk_level],
        "confidence": round(confidence, 1),
        "possible_disease": possible_disease,
        "secondary_conditions": secondary,
        "conditions": ranked,
        "recommended_specialist": specialist,
        "health_suggestions": suggestions,
        "model_version": MODEL_VERSION,
    }


def _apply(total: list, conditions: dict, bonus: list, points: float) -> None:
    """Add risk `points` to the total and fold any condition bonuses in."""
    total[0] += points
    for condition, weight in bonus:
        conditions[condition] = conditions.get(condition, 0.0) + weight


def _confidence(symptoms: list, inputs: dict) -> float:
    """Confidence grows with the number of signals we have to reason about."""
    symptom_signal = min(len(symptoms), 5)
    vitals = [
        inputs.get(k)
        for k in (
            "systolic_bp", "diastolic_bp", "heart_rate", "blood_sugar",
            "body_temperature", "oxygen_level",
        )
    ]
    vital_signal = min(sum(1 for v in vitals if v not in (None, "")), 6)
    habit_signal = sum(
        1
        for k in ("smoking_status", "alcohol_consumption", "exercise_frequency")
        if (inputs.get(k) or "").strip()
    )
    confidence = 52 + 4 * symptom_signal + 3 * vital_signal + 2 * habit_signal
    return min(confidence, 97)


def _suggestions(inputs: dict, conditions: dict, risk_level: str, disease: str) -> list:
    """Build human-readable, tailored health advice."""
    suggestions: list[str] = []
    smoking = (inputs.get("smoking_status") or "").lower()
    alcohol = (inputs.get("alcohol_consumption") or "").lower()
    exercise = (inputs.get("exercise_frequency") or "").lower()
    sugar = _as_float(inputs.get("blood_sugar"))
    sys_bp = _as_float(inputs.get("systolic_bp"))
    dia_bp = _as_float(inputs.get("diastolic_bp"))
    spo2 = _as_float(inputs.get("oxygen_level"))
    temperature = _as_float(inputs.get("body_temperature"))
    bmi = _as_float(inputs.get("bmi"))
    if bmi is None and inputs.get("height_cm") and inputs.get("weight_kg"):
        height = _as_float(inputs.get("height_cm")) / 100
        weight = _as_float(inputs.get("weight_kg"))
        if height and weight and height > 0:
            bmi = weight / (height ** 2)

    if smoking in ("regular", "occasional"):
        suggestions.append(
            "Consider a structured plan to cut down or quit smoking — it is one "
            "of the strongest controllable risk factors for heart and lung disease."
        )
    if alcohol == "regular":
        suggestions.append(
            "Limit alcohol to at most a couple of drinks per week; regular use "
            "raises blood pressure and liver risk."
        )
    if exercise in ("never", "rarely"):
        suggestions.append(
            "Aim for at least 150 minutes of moderate activity per week — brisk "
            "walks, cycling or swimming all count."
        )
    if bmi is not None and bmi >= 30:
        suggestions.append(
            "Your BMI indicates excess weight. Gradual, sustainable changes to "
            "diet and activity can meaningfully reduce your risk profile."
        )
    if bmi is not None and bmi < 18.5:
        suggestions.append(
            "Your BMI is on the low side. Ensure adequate, balanced nutrition "
            "and discuss any unexplained weight loss with your doctor."
        )
    if sugar is not None and sugar >= 126:
        suggestions.append(
            "Your blood sugar reading is elevated. Limit sugary drinks and "
            "refined carbs, and get a fasting blood glucose test."
        )
    if sugar is not None and 100 <= sugar < 126:
        suggestions.append(
            "Your blood sugar is at the higher end of normal — reducing added "
            "sugar now can prevent it from climbing."
        )
    if sys_bp is not None and (sys_bp >= 140 or (dia_bp or 0) >= 90):
        suggestions.append(
            "Your blood pressure reading is high. Reduce salt intake, stay "
            "active, and have it rechecked by a doctor."
        )
    if spo2 is not None and spo2 < 94:
        suggestions.append(
            "Your oxygen level is low. If you feel short of breath or unwell, "
            "this needs urgent medical attention."
        )
    if temperature is not None and temperature >= 38:
        suggestions.append(
            "You have a fever. Rest, hydrate well, and monitor your temperature; "
            "seek care if it persists beyond a few days."
        )
    if "Diabetes risk" in conditions:
        suggestions.append(
            "A repeated fasting glucose test and an HbA1c check are recommended "
            "to confirm or rule out diabetes."
        )
    if disease == "No specific condition detected":
        suggestions.append(
            "No specific condition was matched from your symptoms. If symptoms "
            "persist, keep a diary and check in with your doctor."
        )

    if risk_level in (RISK_HIGH, RISK_CRITICAL):
        suggestions.insert(
            0,
            "Your results warrant prompt medical attention. Do not wait for "
            "symptoms to resolve on their own.",
        )
    else:
        suggestions.append(
            "Keep your profile and health information up to date so future "
            "assessments stay accurate."
        )
    suggestions.append(
        "These results are screening guidance only — always follow your "
        "doctor's advice over this analysis."
    )
    return suggestions[:8]
