import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import 'dietary_risk_screen.dart';
import 'glucose_screen.dart';
import 'glucose_session.dart';
import 'what_if_screen.dart';
import 'what_if_session.dart';

/// Glucose (C2): the four-hour forecast, the Dynamic Dietary Risk page and the
/// What-If Meal Simulation.
///
/// All pages share one [GlucoseSession], so the meal is entered once (on the
/// forecast tab) and inputs and results survive switching tabs. The simulation
/// keeps its own [WhatIfSession] for the same reason.
class GlucoseTabs extends StatefulWidget {
  const GlucoseTabs({super.key, this.apiClient, this.session});

  /// Injected in tests and passed to every page.
  final ApiClient? apiClient;

  /// Injected in tests. When null, the tabs create and own their own session.
  final GlucoseSession? session;

  @override
  State<GlucoseTabs> createState() => _GlucoseTabsState();
}

class _GlucoseTabsState extends State<GlucoseTabs> {
  late final GlucoseSession _session = widget.session ?? GlucoseSession();
  late final ApiClient _client = widget.apiClient ?? ApiClient();
  final WhatIfSession _whatIf = WhatIfSession();

  @override
  void dispose() {
    if (widget.session == null) _session.dispose();
    if (widget.apiClient == null) _client.close();
    _whatIf.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Column(
        children: [
          const TabBar(
            // Scrolls on narrow screens, so the three labels are never squeezed.
            isScrollable: true,
            tabs: [
              Tab(text: '4-hour forecast'),
              Tab(text: 'Dietary risk'),
              Tab(text: 'What-if simulation'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                GlucoseScreen(apiClient: _client, session: _session),
                DietaryRiskScreen(apiClient: _client, session: _session),
                WhatIfScreen(
                  apiClient: _client,
                  session: _session,
                  whatIf: _whatIf,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
