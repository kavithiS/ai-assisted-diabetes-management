/// Every user-facing text of the Risk Profile (C3) feature, in one place.
///
/// Kept as Dart constants so it can move to ARB files when the client owner sets up
/// localisation (PR note `server/services/c3_risk_xai/docs/pr_notes/client_note.md`).
/// Wording rules: "estimated risk", never "diagnosis"; never a probability or percentage.
class C3Strings {
  const C3Strings._();

  // Module 3 screens (team prototype: DHS, health info, analysis, result, XAI,
  // recommendations, what-if)
  /// Proposed app name (PR note `docs/pr_notes/app_name_note.md`); used by the C3-only entry.
  static const appName = 'DiaCare';
  static const dhsName = 'Your health score';
  static const estimatedRisk = 'estimated risk';
  static const provisional = 'Early estimate';
  static const provisionalScore = 'Early estimate';
  static const statusGood = 'On track';
  static const statusMixed = 'In progress';
  static const statusAttention = 'Needs attention';
  static const bandLow = 'Low';
  static const bandModerate = 'Moderate';
  static const bandHigh = 'High';
  static const activityLow = 'Low';
  static const activityModerate = 'Moderate';
  static const activityHigh = 'High';
  static const cholesterolNormal = 'Normal';
  static const cholesterolBorderlineHigh = 'Borderline high';
  static const cholesterolHigh = 'High';
  static const adherencePoor = 'Poor';
  static const adherenceFair = 'Fair';
  static const adherenceGood = 'Good';
  static const systolic = 'Systolic';
  static const diastolic = 'Diastolic';
  static const restingPulse = 'Resting pulse';
  static const age = 'Age';
  static const height = 'Height';
  static const weight = 'Weight';
  static const bloodGlucose = 'Blood glucose';
  static const scoreDenominator = '/100';
  static String scoreSemantics(int score) => '$dhsName $score out of 100';
  static const yourCurrentDhs = 'Your health score';
  static const noScoreYet = 'Start with a quick health check.';
  static const lastAssessed = 'Last check: ';
  static const today = 'today';
  static const recalculate = 'Check again';
  static const riskFactors = 'Your factors';
  static const bloodPressureTitle = 'Blood pressure';
  static const usedByModel = 'included in this check';
  static const understandMyScore = 'Why this score';
  static const updateHealthInfoShort = 'Update answers';
  static const fullAssessment = 'See full check';
  static const inputTitle = 'Your health details';
  static const inputIntro = 'A few answers help create your estimate.';
  static const bmiNeeded = 'Add height and weight to continue.';
  static const bloodPressure = 'Blood pressure (mmHg)';
  static const lifestyleTitle = 'Lifestyle and risk factors';
  static const lifestyleNote = 'Your answers help shape your score and suggestions.';
  static const activityLevel = 'Physical activity level';
  static const smokingStatus = 'Smoking';
  static const adherence = 'Medication adherence';
  static const cholesterol = 'Cholesterol level (as told by your doctor)';
  static const kidney = 'Kidney condition';
  static const liver = 'Liver condition';
  static const weightChange = 'Body-weight change in 3 months';
  static const weightChangeHelp = 'Enter a change in kilograms.';
  static const optionalClinical = 'Optional clinical values';
  static const historyTitle = 'Family and medical history';
  static const saveAndRecalculate = 'Save & recalculate';
  static const analyzingTitle = 'Your health check';
  static const analyzing = 'Preparing your estimate';
  static const analyzingSub = 'This usually takes a few seconds.';
  static const resultSummary = 'An early estimate to support self-care.';
  static const resultFooter = 'Estimate for self-care support. Not medical advice.';
  static const highReferral = 'Please see your doctor.';
  static const detailsBody = 'This is an early estimate based on the answers you shared.';
  static const understandMyRisk = 'Why this score';
  static String viewRecommendations(int n) => n == 0 ? 'What you can do' : 'What you can do ($n)';
  static const updateHealthInfo = 'Update health information';
  static const aiExplanation = 'Why this score';
  static const factorsAffecting = 'What shaped this score';
  static const increasing = 'May raise your estimate';
  static const protective = 'May lower your estimate';
  static const legendIncreasing = 'May raise estimate';
  static const legendProtective = 'May lower estimate';
  static const noneInThisGroup = 'No factors to show here.';
  static const shapFootnote =
      'These factors help explain your estimate. They do not show medical causes.';
  static const recommendationsTitle = 'What you can do';
  static const personalised = 'A suggestion for you';
  static const topPriority = 'Try this first';
  static const current = 'Current';
  static const target = 'Target';
  static const additional = 'Additional suggestions';
  static const noRecommendations = 'No suggestions for this check.';
  static const recommendationsFooter = '';

  /// The server's trigger text is technical, so only its window is shown.
  static String because(String window, bool raised) =>
      raised ? 'This raised your estimate.' : 'Based on $window.';
  static String mainReasons(List<String> names) =>
      names.isEmpty ? 'No single answer stood out.' : 'Main reasons: ${names.join(', ')}.';
  static const exploreWhatIf = 'Try a change';
  static const whatIfTitle = 'Try a change';
  static const whatIfIntro = 'Explore how a different answer could change your score.';
  static const cholesterolManagement = 'Cholesterol';
  static const estimate = 'Update estimate';
  static const estimatedDhs = 'Estimated health score';
  static const whatIfBandNote = 'Your risk band stays the same in this preview.';
  static const whatIfDisclaimer = 'Preview only. This check is not saved.';

  // Home
  static const homeTitle = 'Your health score';
  static const homeIntro = 'An early estimate to support healthier choices.';
  static const startQuestionnaire = 'Start a health check';
  static const history = 'Past checks';
  static const presetsTitle = 'Example answers';
  static const warmUp = 'Prepare check';
  static const warmUpDone = 'Ready';

  // Connection
  static const checking = 'Checking connection…';
  static const online = 'Connected';
  static const notLoaded = 'Connected · getting ready';
  static const offline = 'Not connected';
  static const demoData = 'Early estimate';
  static const serverDownTitle = 'Can’t connect right now.';
  static const serverDownBody = 'Start the service, then tap “Check again”.';
  static const checkAgain = 'Check again';
  static const demoBanner = 'Early estimate · example answers';

  // Questionnaire
  static const questionnaireTitle = 'Health check';
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
  static const glucoseOffNote = 'You can continue without a glucose result.';
  static const bmiPrefix = 'Your BMI: ';
  static const familyDiabetes = 'A parent, brother or sister has diabetes';
  static const familyPressure = 'A parent, brother or sister has high blood pressure';
  static const diagnosedPressure = 'A doctor told me I have high blood pressure';
  static const heartDisease = 'I have had heart disease';
  static const stroke = 'I have had a stroke';
  static const required = 'Needed';
  static String outOfRange(num min, num max) =>
      'Enter a value from ${_plain(min)} to ${_plain(max)}';
  static String _plain(num n) => n == n.roundToDouble() ? n.toInt().toString() : n.toString();
  static const notANumber = 'Enter a number';
  static const checkAnswers = 'Please check the answers marked in red.';

  // Result
  static const resultTitle = 'Your estimate';
  static const estimating = 'Preparing estimate…';
  static const bandPrefix = 'Estimated risk: ';
  static const workOn = 'What you can do';
  static const background = 'Other factors';
  static const raises = 'may raise your estimate';
  static const lowers = 'may lower your estimate';
  static const secondCheck = 'More detail';
  static const secondCheckIntro = 'A second view of the factors in your answers.';
  static String agreement(int shared, int total) => '';
  static String limeFit(double r2) => '';
  static const notCauses = 'These factors do not show medical causes.';
  static const allAnswersUsed = 'All required answers were included.';
  static const imputedIntro = 'Some answers were estimated: ';
  static String modelLine(String model, String version, bool withGlucose) => '';
  static const insufficientTitle = 'We need a few more answers';
  static const insufficientBody = 'Add the missing details to continue.';
  static const invalidTitle = 'Some answers look out of range';
  static const answerQuestions = 'Answer the questions';
  static const errorTitle = 'We couldn’t finish this check.';
  static const retry = 'Retry';
  static const connectionSuccess = 'Connection successful.';
  static const connectionFailed = 'Could not connect. Check the address and try again.';
  static const analysisStepFactors = 'Reviewing your answers';
  static const analysisStepScore = 'Preparing your health score';
  static const presetHigher = 'Higher-risk example';
  static const presetLower = 'Lower-risk example';
  static const presetMissing = 'Missing details example';
  static const presetHigherNote = 'Example answers with more factors to review.';
  static const presetLowerNote = 'Example answers with fewer factors to review.';
  static const presetMissingNote = 'See what happens when an answer is missing.';
  static const connectionButtonHint = 'Tap to check again.';

  // Researcher view (hidden, never for patients)
  static const researcherTitle = 'Details';
  static const researcherOff = 'No extra details are available.';

  // History
  static const historyEmpty = 'No saved results yet.';
  static const historyFromServer = 'Saved checks';
  static const savedCheckTitle = 'Saved check';
  static const savedCheckNote =
      'Only the risk band and date are saved. Do a new check for details.';
  static const historyFallback =
      'Past checks are offline right now. Showing checks from this session.';
  static const sessionEmpty = 'No results in this session yet.';
  static const statusInsufficient = 'More answers needed';
  static const statusInvalid = 'Please check your answers';
  static const notSaved = 'This check wasn’t saved. Past checks are temporarily unavailable.';

  // Settings
  static const settingsTitle = 'Settings';
  static const gatewayUrl = 'Gateway URL';
  static const gatewayUrlHelp =
      'Chrome: http://127.0.0.1:8000 · Android emulator: http://10.0.2.2:8000 · '
      'Phone: http://<laptop IP>:8000';
  static const invalidUrl = 'Enter a full http:// or https:// address';
  static const testConnection = 'Test connection';
  static const researcherMode = 'Details';
  static const researcherModeHelp = '';
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
