import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import 'data/auth_api.dart';

/// Page frame shared by the login and register screens: back arrow, heading, scrolling body.
class AuthScaffold extends StatelessWidget {
  const AuthScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.children,
  });

  final String title;
  final String subtitle;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 24),
            children: [
              if (Navigator.of(context).canPop())
                Align(
                  alignment: Alignment.centerLeft,
                  child: IconButton(
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back, color: AppColors.text),
                    tooltip: 'Back',
                  ),
                )
              else
                const SizedBox(height: 14),
              const SizedBox(height: 6),
              Text(title,
                  style: GoogleFonts.inter(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      color: AppColors.text,
                      height: 1.25)),
              const SizedBox(height: 8),
              Text(subtitle,
                  style: GoogleFonts.inter(
                      fontSize: 14.5,
                      color: AppColors.textSecondary,
                      height: 1.55)),
              const SizedBox(height: 26),
              ...children,
            ],
          ),
        ),
      );
}

/// A label above a form control, in the style of the onboarding questionnaire.
class AuthField extends StatelessWidget {
  const AuthField({super.key, required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label,
              style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppColors.text)),
          const SizedBox(height: 9),
          child,
        ]),
      );
}

/// A password box with a show/hide button.
class PasswordField extends StatefulWidget {
  const PasswordField({
    super.key,
    required this.controller,
    required this.validator,
    this.hintText,
    this.autofillHints,
    this.textInputAction,
    this.onSubmitted,
  });

  final TextEditingController controller;
  final FormFieldValidator<String> validator;
  final String? hintText;
  final Iterable<String>? autofillHints;
  final TextInputAction? textInputAction;
  final VoidCallback? onSubmitted;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _hidden = true;

  @override
  Widget build(BuildContext context) => TextFormField(
        controller: widget.controller,
        obscureText: _hidden,
        validator: widget.validator,
        autofillHints: widget.autofillHints,
        textInputAction: widget.textInputAction,
        onFieldSubmitted: widget.onSubmitted == null ? null : (_) => widget.onSubmitted!(),
        decoration: InputDecoration(
          hintText: widget.hintText,
          suffixIcon: IconButton(
            tooltip: _hidden ? 'Show password' : 'Hide password',
            onPressed: () => setState(() => _hidden = !_hidden),
            icon: Icon(
              _hidden ? Icons.visibility_outlined : Icons.visibility_off_outlined,
              size: 20,
              color: AppColors.textSecondary,
            ),
          ),
        ),
      );
}

/// The gateway's error message (and the problems it lists), in the style the meal scan uses.
class AuthErrorText extends StatelessWidget {
  const AuthErrorText(this.error, {super.key});

  final AuthApiException error;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(error.message,
              style: const TextStyle(color: AppColors.danger, fontSize: 13)),
          for (final issue in error.details)
            Text('• $issue',
                style: const TextStyle(color: AppColors.danger, fontSize: 13)),
          const SizedBox(height: 2),
          Text(error.code,
              style: GoogleFonts.inter(
                  fontSize: 11, color: AppColors.textSecondary)),
        ]),
      );
}

final RegExp emailPattern = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

/// Shown on the busy button.
class ButtonSpinner extends StatelessWidget {
  const ButtonSpinner({super.key});

  @override
  Widget build(BuildContext context) => const SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
      );
}
