import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/server_history.dart';
import 'risk_controller.dart';
import 'risk_result_screen.dart';
import 'widgets/risk_widgets.dart';

/// Saved results from the server (FR13), newest first. If the server history cannot be
/// read (database stopped), it says so and shows this session's results instead.
class RiskHistoryScreen extends StatefulWidget {
  const RiskHistoryScreen({super.key, required this.controller});

  final RiskController controller;

  @override
  State<RiskHistoryScreen> createState() => _RiskHistoryScreenState();
}

class _RiskHistoryScreenState extends State<RiskHistoryScreen> {
  late Future<List<ServerHistoryItem>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.controller.serverHistory();
  }

  static String _when(DateTime t) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${t.year}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}';
  }

  static String _title(String status, RiskBand? band) => switch (status) {
        'ok' => '${C3Strings.bandPrefix}${BandCard.label(band!)}',
        'insufficient_data' => C3Strings.statusInsufficient,
        _ => C3Strings.statusInvalid,
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.history)),
      body: FutureBuilder<List<ServerHistoryItem>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) return _sessionFallback(context);
          final items = snapshot.data!;
          return RefreshIndicator(
            onRefresh: () async {
              final next = widget.controller.serverHistory();
              setState(() {
                _future = next;
              });
              await next;
            },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Text(C3Strings.historyFromServer),
                if (items.isEmpty)
                  const Padding(
                    padding: EdgeInsets.only(top: 16),
                    child: Text(C3Strings.historyEmpty),
                  ),
                for (final item in items)
                  ListTile(
                    leading: Icon(
                      item.status == 'ok'
                          ? Icons.assignment_turned_in_outlined
                          : Icons.help_outline,
                    ),
                    title: Text(_title(item.status, item.band)),
                    subtitle: Text(
                      '${_when(item.assessedAt)} · model ${item.modelVersion ?? '-'} · '
                      'schema ${item.schemaVersion}',
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _sessionFallback(BuildContext context) {
    final entries = widget.controller.history.entries;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const NoticeBox(icon: Icons.cloud_off_outlined, text: C3Strings.historyFallback),
        if (entries.isEmpty)
          const Padding(padding: EdgeInsets.only(top: 16), child: Text(C3Strings.sessionEmpty)),
        for (final entry in entries)
          ListTile(
            leading: const Icon(Icons.assignment_turned_in_outlined),
            title: Text(_title('ok', entry.assessment.band)),
            subtitle: Text(_when(entry.assessedAt)),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              c3Route<void>(
                RiskResultView(
                  assessment: entry.assessment,
                  isDemoData: widget.controller.isDemoData,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
