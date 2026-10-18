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
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 22),
            child: Column(children: [
              const SizedBox(height: 34),
              // Image placeholder
              Container(
                height: 230,
                margin: const EdgeInsets.only(bottom: 26),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFFCFEEEF), AppColors.primaryLight],
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Center(
                  child: Icon(Icons.favorite_border,
                      size: 78, color: AppColors.primary),
                ),
              ),
              Text('Manage your diabetes with confidence',
                  style: GoogleFonts.inter(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      color: AppColors.text,
                      height: 1.25)),
              const SizedBox(height: 12),
              Text(
                'AI-powered meal analysis, glucose prediction, risk insight and foot monitoring — built for how Sri Lankans actually eat and live.',
                style: GoogleFonts.inter(
                    fontSize: 14.5,
                    color: AppColors.textSecondary,
                    height: 1.55),
              ),
              const Spacer(),
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
              const SizedBox(height: 24),
            ]),
          ),
        ),
      );
}
