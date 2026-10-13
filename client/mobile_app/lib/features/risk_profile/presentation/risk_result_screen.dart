// UNVERIFIED: written without the Flutter SDK; run `flutter analyze` before use.

import 'package:flutter/material.dart';

/// Shows one RiskAssessment from the server.
class RiskResultScreen extends StatelessWidget {
  const RiskResultScreen({super.key});

  // TODO(c3): band as label + icon (not colour alone); the disclaimer on every result;
  // the referral as a banner for High; the server's explanation text and factor lists;
  // "estimated risk", never "diagnosis"; never a probability; a "Demo data" banner
  // when RiskRepository.isDemoData; an error with Retry on network failure.

  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('Risk result (C3): coming soon'));
  }
}
