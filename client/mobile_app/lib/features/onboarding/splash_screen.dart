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
            color: AppColors.primaryDark,
            child: SafeArea(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        color: AppColors.accent,
                        borderRadius: BorderRadius.circular(26),
                      ),
                      child: const Icon(Icons.water_drop_outlined,
                          size: 40, color: AppColors.primaryDark),
                    ),
                    const SizedBox(height: 20),
                    Text('DiaCare AI',
                        style: GoogleFonts.manrope(
                            fontSize: 27,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                            letterSpacing: -0.02)),
                    const SizedBox(height: 8),
                    Text('Your Personalized Diabetes Companion',
                        style: GoogleFonts.manrope(
                            fontSize: 13.5,
                            color: Colors.white.withAlpha(210))),
                    const SizedBox(height: 26),
                    Text('Tap anywhere to continue',
                        style: GoogleFonts.manrope(
                            fontSize: 11, color: Colors.white.withAlpha(130))),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}
