import 'package:flutter/material.dart';

import '../c3_strings.dart';
import '../c3_theme.dart';
import '../domain/risk_assessment.dart';
import '../domain/server_history.dart';
import 'risk_controller.dart';
import 'risk_result_screen.dart';
import 'widgets/c3_widgets.dart';
import 'widgets/risk_widgets.dart';

/// Saved checks from the server, newest first. If server history cannot be
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
            return const Padding(
              padding: EdgeInsets.all(16),
              child: C3LoadingSkeleton(lines: 5),
            );
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
                    subtitle: Text(_when(item.assessedAt)),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _openSaved(context, item),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  /// The server keeps only the band, date and status of a saved check (no answers), so
  /// an old check opens as a short summary.
  void _openSaved(BuildContext context, ServerHistoryItem item) => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (context) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Semantics(
                  header: true,
                  child: const Text(
                    C3Strings.savedCheckTitle,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                ),
                const SizedBox(height: 4),
                Text(_when(item.assessedAt), style: const TextStyle(color: C3Colors.text2)),
                const SizedBox(height: 12),
                if (item.status == 'ok' && item.band != null)
                  BandBadge(band: item.band!)
                else
                  Text(_title(item.status, item.band)),
                const SizedBox(height: 12),
                const Text(C3Strings.savedCheckNote),
              ],
            ),
          ),
        ),
      );

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
            onTap: () => c3Push<void>(
              context,
              RiskResultView(
                assessment: entry.assessment,
                isDemoData: widget.controller.isDemoData,
              ),
            ),
          ),
      ],
    );
  }
}
