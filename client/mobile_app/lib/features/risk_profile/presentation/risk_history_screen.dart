import 'package:flutter/material.dart';

import '../c3_strings.dart';
import 'risk_controller.dart';
import 'risk_result_screen.dart';
import 'widgets/risk_widgets.dart';

/// Results of this session, newest first. Server-side history (FR13) comes with the
/// database phase.
class RiskHistoryScreen extends StatelessWidget {
  const RiskHistoryScreen({super.key, required this.controller});

  final RiskController controller;

  String _when(DateTime t) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${t.year}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    final entries = controller.history.entries;
    return Scaffold(
      appBar: AppBar(title: const Text(C3Strings.history)),
      body: entries.isEmpty
          ? const Center(
              child: Padding(padding: EdgeInsets.all(24), child: Text(C3Strings.historyEmpty)),
            )
          : ListView(
              children: [
                for (final entry in entries)
                  ListTile(
                    leading: const Icon(Icons.assignment_turned_in_outlined),
                    title: Text(
                      '${C3Strings.bandPrefix}${BandCard.label(entry.assessment.band!)}',
                    ),
                    subtitle: Text(_when(entry.assessedAt)),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => RiskResultView(
                          assessment: entry.assessment,
                          isDemoData: controller.isDemoData,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}
