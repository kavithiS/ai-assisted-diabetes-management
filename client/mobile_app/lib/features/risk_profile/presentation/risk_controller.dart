import 'package:flutter/foundation.dart';

import '../data/history_store.dart';
import '../data/repository_factory.dart';
import '../data/risk_repository.dart';
import '../data/settings_store.dart';
import '../domain/risk_assessment.dart';
import '../domain/risk_presets.dart';
import '../domain/risk_profile.dart';
import '../domain/server_history.dart';

enum GatewayState { checking, online, modelNotLoaded, offline }

/// State of the Risk Profile feature: settings, connection, repository and history.
///
/// Plain ChangeNotifier, no state-management package. It holds no model logic: every
/// band and explanation comes from the server through [RiskRepository].
class RiskController extends ChangeNotifier {
  RiskController({
    SettingsStore? store,
    RiskRepository Function(RiskSettings settings)? repositoryBuilder,
  })  : _store = store ?? SettingsStore(),
        _build = repositoryBuilder ?? createRiskRepository;

  final SettingsStore _store;
  final RiskRepository Function(RiskSettings settings) _build;
  final RiskHistoryStore history = RiskHistoryStore();

  RiskSettings? _settings;
  RiskAssessment? _latest;
  RiskProfile? _latestProfile;
  DateTime? _latestAt;
  RiskRepository? _repository;
  GatewayState _gateway = GatewayState.checking;
  String? _gatewayMessage;

  RiskSettings? get settings => _settings;
  GatewayState get gateway => _gateway;
  String? get gatewayMessage => _gatewayMessage;
  bool get isReady => _repository != null;
  bool get isDemoData => _repository?.isDemoData ?? false;

  /// Latest `ok` result of this session, its answers and when it was made.
  RiskAssessment? get latest => _latest;
  RiskProfile? get latestProfile => _latestProfile;
  DateTime? get latestAt => _latestAt;

  Future<void> init() async {
    _settings = await _store.load();
    _repository = _build(_settings!);
    notifyListeners();
    await checkConnection();
  }

  Future<void> checkConnection() async {
    final repository = _repository;
    if (repository == null) return;
    _gateway = GatewayState.checking;
    notifyListeners();
    try {
      final status = await repository.status();
      _gateway = status.modelLoaded ? GatewayState.online : GatewayState.modelNotLoaded;
      _gatewayMessage = status.detail;
    } on Object catch (error) {
      _gateway = GatewayState.offline;
      _gatewayMessage = error.toString();
    }
    notifyListeners();
  }

  Future<void> updateSettings(RiskSettings settings) async {
    await _store.save(settings);
    _settings = settings;
    _repository = _build(settings);
    notifyListeners();
    await checkConnection();
  }

  Future<void> resetSettings() async {
    await _store.reset();
    await init();
  }

  /// Sends the profile to C3. Errors are passed on so the screen can offer Retry.
  Future<RiskAssessment> assess(RiskProfile profile) async {
    final assessment = await _repository!.assess(profile);
    history.add(assessment);
    if (assessment.status == AssessmentStatus.ok) {
      _latest = assessment;
      _latestProfile = profile;
      _latestAt = DateTime.now();
    }
    notifyListeners();
    return assessment;
  }

  /// What-if preview: same server call, but not saved and not added to history.
  Future<RiskAssessment> simulate(RiskProfile profile) => _repository!.assess(profile, save: false);

  /// Saved results from the server (FR13). Errors are passed on; the history screen
  /// then falls back to this session's list and says so.
  Future<List<ServerHistoryItem>> serverHistory() => _repository!.history();

  /// FR16: delete this device's saved results on the server. Returns how many.
  Future<int> deleteMyRecords() async {
    final count = await _repository!.deleteMyRecords();
    notifyListeners();
    return count;
  }

  /// One throw-away request so SHAP and LIME are loaded before the demo. Not kept in
  /// history and not saved on the server. Returns how long it took.
  Future<Duration> warmUp() async {
    final watch = Stopwatch()..start();
    await _repository!.assess(lowerRiskPreset.profile, save: false);
    watch.stop();
    await checkConnection();
    return watch.elapsed;
  }
}
