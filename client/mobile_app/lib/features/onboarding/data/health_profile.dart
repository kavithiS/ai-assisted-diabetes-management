import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Answers entered for the research prototype. Empty answers are never inferred.
class HealthProfile {
  const HealthProfile(this.answers);

  final Map<String, String> answers;

  String? answer(String key) => answers[key];

  Map<String, dynamic> toJson() => {'answers': answers};

  factory HealthProfile.fromJson(Map<String, dynamic> json) {
    final raw = json['answers'];
    if (raw is! Map) return const HealthProfile({});
    return HealthProfile({
      for (final entry in raw.entries)
        if (entry.key is String && entry.value is String)
          entry.key as String: entry.value as String,
    });
  }
}

abstract class HealthProfileStore {
  Future<HealthProfile?> load(String userId);
  Future<void> save(String userId, HealthProfile profile);
  Future<void> delete(String userId);
}

/// Useful for isolated widget tests and temporary demonstration sessions.
class MemoryHealthProfileStore implements HealthProfileStore {
  final Map<String, HealthProfile> _profiles = {};

  @override
  Future<HealthProfile?> load(String userId) async => _profiles[userId];

  @override
  Future<void> save(String userId, HealthProfile profile) async {
    _profiles[userId] = profile;
  }

  @override
  Future<void> delete(String userId) async {
    _profiles.remove(userId);
  }
}

/// Kept on this device, separated by the gateway's user id. No questionnaire
/// answers are uploaded to a service that does not yet have an approved contract.
class SecureHealthProfileStore implements HealthProfileStore {
  SecureHealthProfileStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  String _key(String userId) => 'diacare_health_profile_$userId';

  @override
  Future<HealthProfile?> load(String userId) async {
    final raw = await _storage.read(key: _key(userId));
    if (raw == null) return null;
    return HealthProfile.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  @override
  Future<void> save(String userId, HealthProfile profile) =>
      _storage.write(key: _key(userId), value: jsonEncode(profile.toJson()));

  @override
  Future<void> delete(String userId) => _storage.delete(key: _key(userId));
}
