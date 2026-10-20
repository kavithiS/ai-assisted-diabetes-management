import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../auth/login_screen.dart';
import '../auth/register_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: ListView(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
                children: [
                  Row(children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.water_drop_outlined,
                          size: 20, color: Colors.white),
                    ),
                    const SizedBox(width: 10),
                    Text('DiaCare AI',
                        style: GoogleFonts.manrope(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            color: AppColors.text)),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppColors.primaryLight,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text('Research prototype',
                          style: GoogleFonts.manrope(
                              fontSize: 10.5,
                              fontWeight: FontWeight.w700,
                              color: AppColors.primaryDark)),
                    ),
                  ]),
                  const SizedBox(height: 22),
                  Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      color: AppColors.primaryDark,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 58,
                          height: 58,
                          decoration: BoxDecoration(
                            color: AppColors.accent,
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: const Icon(Icons.favorite_outline_rounded,
                              color: AppColors.primaryDark, size: 29),
                        ),
                        const SizedBox(height: 42),
                        Text('Everyday care,\nmade clearer.',
                            style: GoogleFonts.manrope(
                                fontSize: 32,
                                height: 1.08,
                                letterSpacing: -1,
                                fontWeight: FontWeight.w800,
                                color: Colors.white)),
                        const SizedBox(height: 12),
                        Text(
                          'Bring meals, glucose predictions, risk insights and foot monitoring into one calm daily view.',
                          style: GoogleFonts.manrope(
                              fontSize: 13.5,
                              height: 1.5,
                              color: Colors.white.withAlpha(220)),
                        ),
                        const SizedBox(height: 22),
                        const Row(children: [
                          _FeaturePill(Icons.restaurant_outlined, 'Meals'),
                          SizedBox(width: 8),
                          _FeaturePill(Icons.insights_outlined, 'Insights'),
                          SizedBox(width: 8),
                          _FeaturePill(Icons.healing_outlined, 'Foot'),
                        ]),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  FilledButton(
                    style: primaryButtonStyle(),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const RegisterScreen()),
                    ),
                    child: const Text('Get Started'),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton(
                    style: ghostButtonStyle(),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                    ),
                    child: const Text('I already have an account'),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Outputs are estimates and predictions, not diagnoses.',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.manrope(
                        fontSize: 11.5, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _FeaturePill extends StatelessWidget {
  const _FeaturePill(this.icon, this.label);

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: Colors.white.withAlpha(24),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(children: [
            Icon(icon, size: 18, color: Colors.white),
            const SizedBox(height: 5),
            Text(label,
                style: GoogleFonts.manrope(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    color: Colors.white)),
          ]),
        ),
      );
}
