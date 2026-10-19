import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../c3_strings.dart';
import '../data/risk_api.dart';
import '../data/settings_store.dart';
import 'risk_controller.dart';

/// Hidden settings (long-press the connection status): gateway URL with
/// "Test connection", Researcher mode, and the pseudonymous device ID.
class RiskSettingsScreen extends StatefulWidget {
  const RiskSettingsScreen({super.key, required this.controller});

  final RiskController controller;

  @override
  State<RiskSettingsScreen> createState() => _RiskSettingsScreenState();
}

class _RiskSettingsScreenState extends State<RiskSettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _url;
  late bool _researcher;
  String? _testResult;
  bool _testing = false;

  RiskSettings get _current => widget.controller.settings!;

  @override
  void initState() {
    super.initState();
    _url = TextEditingController(text: _current.gatewayUrl);
    _researcher = _current.researcherMode;
  }

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _test() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _testing = true;
      _testResult = null;
    });
    final api = RiskApi(client: ApiClient(baseUrl: _url.text.trim()));
    String result;
    try {
      final status = await api.status();
      result = status.modelLoaded
          ? 'OK: C3 reachable, models ${status.models}'
          : 'Reachable, but the model is not loaded: ${status.detail ?? ''}';
    } on RiskApiException catch (error) {
      result = error.message;
    }
    if (!mounted) return;
    setState(() {
      _testing = false;
      _testResult = result;
    });
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    await widget.controller.updateSettings(
      _current.copyWith(gatewayUrl: _url.text.trim(), researcherMode: _researcher),
    );
    if (mounted) Navigator.of(context).pop();
  }

  Future<void> _deleteMine() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: const Text(C3Strings.deleteConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text(C3Strings.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text(C3Strings.delete),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    String message;
    try {
      message = C3Strings.deleted(await widget.controller.deleteMyRecords());
    } on Object catch (error) {
      message = '$error';
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _reset() async {
    await widget.controller.resetSettings();
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.settingsTitle)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _url,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                labelText: C3Strings.gatewayUrl,
                helperText: C3Strings.gatewayUrlHelp,
                helperMaxLines: 3,
                border: OutlineInputBorder(),
              ),
              validator: (text) => isValidGatewayUrl(text ?? '') ? null : C3Strings.invalidUrl,
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _testing ? null : _test,
              icon: const Icon(Icons.network_check),
              label: const Text(C3Strings.testConnection),
            ),
            if (_testing) const LinearProgressIndicator(),
            if (_testResult != null)
              Padding(padding: const EdgeInsets.only(top: 8), child: Text(_testResult!)),
            const SizedBox(height: 16),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text(C3Strings.researcherMode),
              subtitle: const Text(C3Strings.researcherModeHelp),
              value: _researcher,
              onChanged: (value) => setState(() => _researcher = value),
            ),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text(C3Strings.deviceId),
              subtitle: SelectableText(_current.deviceId),
            ),
            const SizedBox(height: 16),
            FilledButton(onPressed: _save, child: const Text(C3Strings.save)),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _deleteMine,
              icon: const Icon(Icons.delete_outline),
              label: const Text(C3Strings.deleteMine),
            ),
            TextButton(onPressed: _reset, child: const Text(C3Strings.resetDefaults)),
          ],
        ),
      ),
    );
  }
}
