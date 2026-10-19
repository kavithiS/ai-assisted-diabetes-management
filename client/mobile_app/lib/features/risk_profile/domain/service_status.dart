/// Answer of `GET /api/v1/risk/status`: is C3 reachable and are its models loaded?
class ServiceStatus {
  const ServiceStatus({required this.modelLoaded, this.models = const {}, this.detail});

  factory ServiceStatus.fromJson(Map<String, dynamic> json) => ServiceStatus(
        modelLoaded: json['model_loaded'] as bool,
        models: (json['models'] as Map<String, dynamic>? ?? const {}).cast<String, String>(),
        detail: json['detail'] as String?,
      );

  final bool modelLoaded;

  /// Feature set -> model name, e.g. `with_glucose: random_forest`.
  final Map<String, String> models;
  final String? detail;
}
