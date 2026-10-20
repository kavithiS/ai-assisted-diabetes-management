import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import 'auth_widgets.dart';
import 'data/auth_api.dart';
import 'data/auth_tokens.dart';
import 'login_screen.dart';
import '../onboarding/questionnaire_screen.dart';

/// Wording of the consent checkbox, as given by the project owner.
const String kConsentText =
    'I agree to the terms and consent to my data being used for this research study';

/// The gateway accepts passwords of 10 to 128 characters.
const int kMinPasswordLength = 10;

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key, this.api, this.session});

  /// Overridable so tests can use a fake gateway.
  final AuthApi? api;
  final AuthSession? session;

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _fullName = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  late final AuthApi _api = widget.api ?? AuthApi();
  late final AuthSession _session = widget.session ?? AuthSession.instance;

  bool _consent = false;
  bool _consentMissing = false;
  bool _busy = false;
  bool _accountCreated = false;
  String? _createdUserId;
  AuthApiException? _error;

  @override
  void dispose() {
    _fullName.dispose();
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy) return;
    final formOk = _formKey.currentState!.validate();
    setState(() => _consentMissing = !_consent);
    if (!formOk || !_consent) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (!_accountCreated) {
        _createdUserId = await _api.register(
            fullName: _fullName.text,
            email: _email.text,
            password: _password.text);
        _accountCreated = true;
      }
      // The gateway returns no tokens when an account is created, so sign in straight away.
      final tokens =
          await _api.login(email: _email.text, password: _password.text);
      await _session.signIn(tokens);
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute<void>(
            builder: (_) => QuestionnaireScreen(userId: _createdUserId!)),
        (_) => false,
      );
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
        title: 'Create your account',
        subtitle:
            'One account keeps your meals and health information together.',
        children: [
          Form(
            key: _formKey,
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              AuthField(
                label: 'Full name *',
                child: TextFormField(
                  controller: _fullName,
                  autofillHints: const [AutofillHints.name],
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(hintText: 'Your full name'),
                  validator: (value) {
                    final name = value?.trim() ?? '';
                    if (name.isEmpty) return 'Enter your full name.';
                    if (name.length < 2 || name.length > 100) {
                      return 'Use 2 to 100 characters.';
                    }
                    return null;
                  },
                ),
              ),
              AuthField(
                label: 'Email *',
                child: TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  textInputAction: TextInputAction.next,
                  decoration:
                      const InputDecoration(hintText: 'you@example.com'),
                  validator: (v) =>
                      (v != null && emailPattern.hasMatch(v.trim()))
                          ? null
                          : 'Enter a valid email address.',
                ),
              ),
              AuthField(
                label: 'Password *',
                child: PasswordField(
                  controller: _password,
                  hintText: 'At least $kMinPasswordLength characters',
                  autofillHints: const [AutofillHints.newPassword],
                  textInputAction: TextInputAction.next,
                  validator: (v) => (v != null &&
                          v.length >= kMinPasswordLength &&
                          v.length <= 128)
                      ? null
                      : 'Use $kMinPasswordLength to 128 characters.',
                ),
              ),
              AuthField(
                label: 'Confirm password *',
                child: PasswordField(
                  controller: _confirm,
                  autofillHints: const [AutofillHints.newPassword],
                  textInputAction: TextInputAction.done,
                  onSubmitted: _submit,
                  validator: (v) =>
                      v == _password.text ? null : 'Passwords do not match.',
                ),
              ),
            ]),
          ),
          InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: _busy
                ? null
                : () => setState(() {
                      _consent = !_consent;
                      _consentMissing = false;
                    }),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child:
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Checkbox(
                  value: _consent,
                  onChanged: _busy
                      ? null
                      : (v) => setState(() {
                            _consent = v ?? false;
                            _consentMissing = false;
                          }),
                  activeColor: AppColors.primary,
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(kConsentText,
                        style: GoogleFonts.manrope(
                            fontSize: 13, height: 1.45, color: AppColors.text)),
                  ),
                ),
              ]),
            ),
          ),
          if (_consentMissing)
            Padding(
              padding: const EdgeInsets.only(left: 12, bottom: 8),
              child: Text('Please agree to continue.',
                  style: GoogleFonts.manrope(
                      fontSize: 13, color: AppColors.danger)),
            ),
          const SizedBox(height: 10),
          if (_error != null) AuthErrorText(_error!),
          if (_accountCreated && _error != null)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Text(
                  'Your account was created. Try signing in again to continue.'),
            ),
          FilledButton(
            style: primaryButtonStyle(),
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const ButtonSpinner()
                : Text(
                    _accountCreated ? 'Continue to account' : 'Create Account'),
          ),
          const SizedBox(height: 18),
          Wrap(
              alignment: WrapAlignment.center,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text('Already have an account?',
                    style: GoogleFonts.manrope(
                        fontSize: 13.5, color: AppColors.textSecondary)),
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => Navigator.of(context).pushReplacement(
                            MaterialPageRoute(
                                builder: (_) => LoginScreen(
                                    api: widget.api, session: widget.session)),
                          ),
                  child: Text('Log in',
                      style: GoogleFonts.manrope(
                          fontSize: 13.5, fontWeight: FontWeight.w700)),
                ),
              ]),
        ],
      );
}
