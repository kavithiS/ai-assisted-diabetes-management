import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import 'welcome_screen.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: () => Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const WelcomeScreen()),
        ),
        child: Scaffold(
          body: Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0A8996), AppColors.primaryDark],
              ),
            ),
            child: SafeArea(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        color: Colors.white.withAlpha(36),
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: const Icon(Icons.water_drop_outlined,
                          size: 40, color: Colors.white),
                    ),
                    const SizedBox(height: 20),
                    Text('DiaCare AI',
                        style: GoogleFonts.inter(
                            fontSize: 27,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                            letterSpacing: -0.02)),
                    const SizedBox(height: 8),
                    Text('Your Personalized Diabetes Companion',
                        style: GoogleFonts.inter(
                            fontSize: 13.5,
                            color: Colors.white.withAlpha(210))),
                    const SizedBox(height: 26),
                    Text('Tap anywhere to continue',
                        style: GoogleFonts.inter(
                            fontSize: 11,
                            color: Colors.white.withAlpha(130))),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}
