import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import 'auth_widgets.dart';
import 'data/auth_api.dart';
import 'data/auth_tokens.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, this.api, this.session});

  /// Overridable so tests can use a fake gateway.
  final AuthApi? api;
  final AuthSession? session;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  late final AuthApi _api = widget.api ?? AuthApi();
  late final AuthSession _session = widget.session ?? AuthSession.instance;

  bool _busy = false;
  AuthApiException? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy || !_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final tokens = await _api.login(email: _email.text, password: _password.text);
      await _session.signIn(tokens);
      if (!mounted) return;
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (_) => false);
    } on AuthApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => AuthScaffold(
        title: 'Welcome back',
        subtitle: 'Log in to continue with your meals, glucose and health insights.',
        children: [
          Form(
            key: _formKey,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              AuthField(
                label: 'Email',
                child: TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(hintText: 'you@example.com'),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Enter your email.' : null,
                ),
              ),
              AuthField(
                label: 'Password',
                child: PasswordField(
                  controller: _password,
                  autofillHints: const [AutofillHints.password],
                  textInputAction: TextInputAction.done,
                  onSubmitted: _submit,
                  validator: (v) =>
                      (v == null || v.isEmpty) ? 'Enter your password.' : null,
                ),
              ),
            ]),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: null,
              child: Text('Forgot password?',
                  style: GoogleFonts.inter(
                      fontSize: 13, fontWeight: FontWeight.w600)),
            ),
          ),
          if (_error != null) AuthErrorText(_error!),
          const SizedBox(height: 4),
          FilledButton(
            style: primaryButtonStyle(),
            onPressed: _busy ? null : _submit,
            child: _busy ? const ButtonSpinner() : const Text('Log In'),
          ),
          const SizedBox(height: 18),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text("Don't have an account?",
                style: GoogleFonts.inter(
                    fontSize: 13.5, color: AppColors.textSecondary)),
            TextButton(
              onPressed: _busy
                  ? null
                  : () => Navigator.of(context).pushReplacement(
                        MaterialPageRoute(
                            builder: (_) => RegisterScreen(
                                api: widget.api, session: widget.session)),
                      ),
              child: Text('Create account',
                  style: GoogleFonts.inter(
                      fontSize: 13.5, fontWeight: FontWeight.w700)),
            ),
          ]),
        ],
      );
}
