/// Every user-facing text of the Risk Profile (C3) feature, in one place.
///
/// Kept as Dart constants so it can move to ARB files when the client owner sets up
/// localisation (PR note `server/services/c3_risk_xai/docs/pr_notes/client_note.md`).
/// Wording rules: "estimated risk", never "diagnosis"; never a probability or percentage.
class C3Strings {
  const C3Strings._();

  // Module 3 screens (team prototype: DHS, health info, analysis, result, XAI,
  // recommendations, what-if)
  static const dhsName = 'Diabetic Health Score';
  static const estimatedRisk = 'estimated risk';
  static const provisional = 'Provisional';
  static const provisionalScore = 'Provisional score - weights pending clinician review';
  static const statusGood = 'Good';
  static const statusMixed = 'Fair';
  static const statusAttention = 'Needs attention';
  static const yourCurrentDhs = 'Your current DHS';
  static const noScoreYet =
      'No score yet. Fill in your health and lifestyle information, or try a demo example.';
  static const lastAssessed = 'Last assessed: ';
  static const today = 'today';
  static const recalculate = 'Recalculate score';
  static const riskFactors = 'Risk factors';
  static const bloodPressureTitle = 'Blood pressure';
  static const usedByModel = 'used by the risk model';
  static const understandMyScore = 'Understand my score';
  static const updateHealthInfoShort = 'Update health info';
  static const fullAssessment = 'Full risk assessment';
  static const inputTitle = 'Health & Lifestyle Info';
  static const inputIntro = 'Feeds your multi-factor Diabetic Health Score and the explainable AI. '
      'Leave anything you do not know empty.';
  static const bmiNeeded = 'Enter height and weight to work out your BMI (needed).';
  static const bloodPressure = 'Blood pressure (mmHg)';
  static const lifestyleTitle = 'Lifestyle and risk factors';
  static const lifestyleNote =
      'These answers shape your health score and recommendations. The risk model itself '
      'does not use them yet.';
  static const activityLevel = 'Physical activity level';
  static const smokingStatus = 'Smoking';
  static const adherence = 'Medication adherence';
  static const cholesterol = 'Cholesterol level (as told by your doctor)';
  static const kidney = 'Kidney condition';
  static const liver = 'Liver condition';
  static const weightChange = 'Body-weight change in 3 months';
  static const weightChangeHelp = 'For example 2 for +2 kg, -1.5 for a loss.';
  static const optionalClinical = 'Optional clinical values';
  static const historyTitle = 'Family and medical history';
  static const saveAndRecalculate = 'Save & recalculate';
  static const analyzingTitle = 'Multi-factor analysis';
  static const analyzing = 'Analyzing your risk';
  static const analyzingSub = 'Running the multi-factor risk engine · research prototype';
  static const resultSummary =
      'The band is the risk model\'s estimate. The health score also uses your lifestyle '
      'answers. Both are estimates, not a diagnosis.';
  static const understandMyRisk = 'Understand my risk';
  static String viewRecommendations(int n) =>
      n == 0 ? 'Recommendations' : 'View recommendations ($n)';
  static const updateHealthInfo = 'Update health information';
  static const aiExplanation = 'AI Explanation';
  static const factorsAffecting = 'Factors affecting your estimate';
  static const increasing = 'Factors increasing risk';
  static const protective = 'Factors reducing risk (protective)';
  static const legendIncreasing = 'Increasing risk';
  static const legendProtective = 'Protective';
  static const noneInThisGroup = 'None among the top factors.';
  static const shapFootnote =
      'Generated with SHAP feature attributions over the risk model. Each bar shows how much '
      'that answer moved the model\'s estimate; these are not medical causes.';
  static const recommendationsTitle = 'Recommendations';
  static const personalised = 'Personalised recommendation';
  static const topPriority = 'Top priority';
  static const current = 'Current';
  static const target = 'Target';
  static const additional = 'Additional suggestions';
  static const noRecommendations = 'No recommendations for your current answers. Keep it up.';
  static const recommendationsFooter =
      'From a fixed set of message templates, pending clinician review. They never ask '
      'you to change your medicines.';
  static String because(String trigger, String window, bool raised) =>
      'Why: $trigger (from $window)'
      '${raised && !trigger.contains('raised') ? '; it raised the model\'s estimate' : ''}.';
  static const exploreWhatIf = 'Explore what-if changes';
  static const whatIfTitle = 'Explore your risk';
  static const whatIfIntro =
      'What happens to your health score if you improve these factors? · Prototype scenario';
  static const cholesterolManagement = 'Cholesterol management';
  static const estimate = 'Estimate';
  static const estimatedDhs = 'Your estimated DHS (today)';
  static const whatIfBandNote =
      'The risk band comes from the model, which does not use these answers, so it stays the same.';
  static const whatIfDisclaimer =
      'Estimated scenario, not a guaranteed medical outcome. Not saved.';

  // Home
  static const homeTitle = 'Your diabetes risk profile';
  static const homeIntro =
      'Your multi-factor health score with explainable AI. It is an estimate, not a diagnosis.';
  static const startQuestionnaire = 'Enter health & lifestyle info';
  static const history = 'Past results';
  static const presetsTitle = 'Demo examples (made-up people)';
  static const warmUp = 'Warm up the model';
  static const warmUpDone = 'Model is ready';
  static const settingsHint = 'Long-press the connection status for settings.';

  // Connection
  static const checking = 'Checking connection…';
  static const online = 'Connected';
  static const notLoaded = 'Connected, model not loaded';
  static const offline = 'Not connected';
  static const demoData = 'Demo data';
  static const serverDownTitle = 'The risk server is not reachable.';
  static const serverDownBody = 'On the demo laptop, start C3 and the gateway with one command:\n'
      r'.\server\services\c3_risk_xai\scripts\demo.ps1'
      '\nThen tap "Check again". Results are never replaced by demo data.';
  static const checkAgain = 'Check again';
  static const demoBanner = 'DEMO DATA: these results are fixed examples, not from the risk model.';

  // Questionnaire
  static const questionnaireTitle = 'Risk questionnaire';
  static const stepAbout = 'About you';
  static const stepBody = 'Height and weight';
  static const stepPressure = 'Blood pressure';
  static const stepPulse = 'Resting pulse';
  static const stepGlucose = 'Blood glucose';
  static const stepFamily = 'Family history';
  static const stepMedical = 'Medical history';
  static const next = 'Next';
  static const back = 'Back';
  static const getResult = 'Get my estimate';
  static const sex = 'Sex';
  static const male = 'Male';
  static const female = 'Female';
  static const yes = 'Yes';
  static const no = 'No';
  static const notSure = 'Not sure';
  static const optional = 'Optional. Leave empty if you do not know.';
  static const hasGlucose = 'I have a recent blood glucose result';
  static const glucoseOffNote =
      'Without a glucose result the app uses the questionnaire-only model.';
  static const bmiPrefix = 'Your BMI: ';
  static const familyDiabetes = 'A parent, brother or sister has diabetes';
  static const familyPressure = 'A parent, brother or sister has high blood pressure';
  static const diagnosedPressure = 'A doctor told me I have high blood pressure';
  static const heartDisease = 'I have had heart disease';
  static const stroke = 'I have had a stroke';
  static const required = 'Needed for an estimate';
  static String outOfRange(num min, num max) =>
      'Enter a value from ${_plain(min)} to ${_plain(max)}';
  static String _plain(num n) => n == n.roundToDouble() ? n.toInt().toString() : n.toString();
  static const notANumber = 'Enter a number';

  // Result
  static const resultTitle = 'Your estimated risk';
  static const estimating = 'Estimating your risk…';
  static const bandPrefix = 'Estimated risk band: ';
  static const workOn = 'Factors you can work on';
  static const background = 'Background and medical history';
  static const raises = 'raised the estimate';
  static const lowers = 'lowered the estimate';
  static const secondCheck = 'Second check (LIME)';
  static const secondCheckIntro =
      'A second, simpler method looked at the same answers. Its main factors:';
  static String agreement(int shared, int total) =>
      'The two methods agree on $shared of their top $total factors.';
  static String limeFit(double r2) => 'LIME fit (R²): ${r2.toStringAsFixed(2)}';
  static const notCauses = 'These are contributions to the model\'s estimate, not medical causes.';
  static const allAnswersUsed = 'All your answers were used.';
  static const imputedIntro = 'Some answers were missing and were filled with typical values: ';
  static String modelLine(String model, String version, bool withGlucose) =>
      'Model: ${model.replaceAll('_', ' ')}, version $version, '
      '${withGlucose ? 'with' : 'without'} a glucose result.';
  static const insufficientTitle = 'We need a few more answers';
  static const insufficientBody =
      'An estimate needs these answers. No risk band is shown without them:';
  static const invalidTitle = 'Some answers look out of range';
  static const answerQuestions = 'Answer the questions';
  static const errorTitle = 'Could not get an estimate';
  static const retry = 'Retry';

  // Researcher view (hidden, never for patients)
  static const researcherTitle = 'Researcher view (not for patients)';
  static const researcherOff =
      'No researcher data. Turn on Researcher mode in Settings and start C3 with '
      'C3_RESEARCH_MODE=true.';

  // History
  static const historyEmpty = 'No saved results yet.';
  static const historyFromServer = 'Saved results on the server (newest first)';
  static const historyFallback =
      'Saved results are not available right now (the database may be stopped). '
      'Showing only the results from this session:';
  static const sessionEmpty = 'No results in this session yet.';
  static const statusInsufficient = 'More answers were needed (no band)';
  static const statusInvalid = 'Answers were out of range (no band)';
  static const notSaved =
      'This result was not saved (the database is unavailable). The result itself is valid.';

  // Settings
  static const settingsTitle = 'Settings';
  static const gatewayUrl = 'Gateway URL';
  static const gatewayUrlHelp =
      'Chrome: http://127.0.0.1:8000 · Android emulator: http://10.0.2.2:8000 · '
      'Phone: http://<laptop IP>:8000';
  static const invalidUrl = 'Enter a full http:// or https:// address';
  static const testConnection = 'Test connection';
  static const researcherMode = 'Researcher mode';
  static const researcherModeHelp =
      'Asks the server for researcher data (only sent when the server allows it). '
      'Patient screens never show it.';
  static const deviceId = 'Pseudonymous device ID';
  static const save = 'Save';
  static const deleteMine = 'Delete my saved results';
  static const deleteConfirm =
      'Delete every result saved on the server for this device? This cannot be undone.';
  static const cancel = 'Cancel';
  static const delete = 'Delete';
  static String deleted(int n) => 'Deleted $n saved result${n == 1 ? '' : 's'}.';
  static const resetDefaults = 'Reset to defaults';
}

/// Readable names for the fields the server can list as missing or out of range.
const Map<String, String> c3FieldLabels = {
  'age': 'age',
  'sex_male': 'sex',
  'bmi': 'height and weight (BMI)',
  'systolic_bp': 'blood pressure (upper number)',
  'diastolic_bp': 'blood pressure (lower number)',
  'pulse_rate': 'resting pulse',
  'glucose_mmol': 'blood glucose',
  'family_history_diabetes': 'family history of diabetes',
  'family_history_hypertension': 'family history of high blood pressure',
  'hypertensive': 'diagnosed high blood pressure',
  'cardiovascular_disease': 'heart disease',
  'stroke': 'stroke',
};
