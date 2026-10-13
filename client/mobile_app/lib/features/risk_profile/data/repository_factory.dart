// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import 'mock_risk_repository.dart';
import 'risk_api.dart';
import 'risk_repository.dart';

/// Demo switch, set with `flutter run --dart-define=C3_USE_MOCK_DATA=true`.
///
/// Kept inside the C3 feature folder because `lib/core/config.dart` is shared; moving
/// it into `AppConfig` is a PR note for the client owner.
const bool useMockRiskData = bool.fromEnvironment('C3_USE_MOCK_DATA');

RiskRepository createRiskRepository() =>
    useMockRiskData ? const MockRiskRepository() : RiskApi();
