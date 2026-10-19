import '../../../core/api_client.dart';
import 'mock_risk_repository.dart';
import 'risk_api.dart';
import 'risk_repository.dart';
import 'settings_store.dart';

/// Demo switch, set with `flutter run --dart-define=C3_USE_MOCK_DATA=true`.
///
/// Kept inside the C3 feature folder because `lib/core/config.dart` is shared; moving
/// it into `AppConfig` is a PR note for the client owner. The mock is never used as a
/// silent fallback: when it is on, every screen shows a "Demo data" banner.
const bool useMockRiskData = bool.fromEnvironment('C3_USE_MOCK_DATA');

RiskRepository createRiskRepository(RiskSettings settings) => useMockRiskData
    ? const MockRiskRepository()
    : RiskApi(
        client: ApiClient(baseUrl: settings.gatewayUrl),
        researcherMode: settings.researcherMode,
      );
