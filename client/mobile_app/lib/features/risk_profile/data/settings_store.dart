import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/config.dart';

/// C3 settings kept on the device: the gateway URL, Researcher mode and the
/// pseudonymous device ID (the user key until the app has a login; no names).
class RiskSettings {
  const RiskSettings({
    required this.gatewayUrl,
    required this.researcherMode,
    required this.deviceId,
  });

  final String gatewayUrl;
  final bool researcherMode;
  final String deviceId;

  RiskSettings copyWith({String? gatewayUrl, bool? researcherMode}) => RiskSettings(
        gatewayUrl: gatewayUrl ?? this.gatewayUrl,
        researcherMode: researcherMode ?? this.researcherMode,
        deviceId: deviceId,
      );
}

/// Random 128-bit ID in hex. Made once per installation; it identifies nobody.
String newDeviceId([Random? random]) {
  final source = random ?? Random.secure();
  return List.generate(16, (_) => source.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
}

/// True for a full http:// or https:// address with a host.
bool isValidGatewayUrl(String value) {
  final uri = Uri.tryParse(value.trim());
  return uri != null && (uri.scheme == 'http' || uri.scheme == 'https') && uri.host.isNotEmpty;
}

class SettingsStore {
  static const _gatewayUrlKey = 'c3.gateway_url';
  static const _researcherKey = 'c3.researcher_mode';
  static const _deviceIdKey = 'c3.device_id';

  Future<RiskSettings> load() async {
    final prefs = await SharedPreferences.getInstance();
    var deviceId = prefs.getString(_deviceIdKey);
    if (deviceId == null) {
      deviceId = newDeviceId();
      await prefs.setString(_deviceIdKey, deviceId);
    }
    return RiskSettings(
      gatewayUrl: prefs.getString(_gatewayUrlKey) ?? AppConfig.apiBaseUrl,
      researcherMode: prefs.getBool(_researcherKey) ?? false,
      deviceId: deviceId,
    );
  }

  Future<void> save(RiskSettings settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_gatewayUrlKey, settings.gatewayUrl.trim());
    await prefs.setBool(_researcherKey, settings.researcherMode);
  }

  /// Forgets the URL and Researcher mode. The device ID is kept.
  Future<void> reset() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_gatewayUrlKey);
    await prefs.remove(_researcherKey);
  }
}
