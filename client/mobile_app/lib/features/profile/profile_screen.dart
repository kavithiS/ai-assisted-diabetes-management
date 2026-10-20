import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../auth/auth_widgets.dart';
import '../auth/data/account_api.dart';
import '../auth/data/auth_api.dart';

/// The Profile tab: who is signed in, log out, and delete the account.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, this.user, this.api, this.onSignedOut});

  /// The signed-in patient, or `null` while it is loading or could not be loaded.
  final UserProfile? user;
  final AccountApi? api;

  /// Called after logging out or deleting the account. By default the app returns to the
  /// start screen and clears the screens behind it.
  final VoidCallback? onSignedOut;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final AccountApi _api = widget.api ?? AccountApi();

  bool _busy = false;
  AuthApiException? _error;

  void _backToStart() {
    final callback = widget.onSignedOut;
    if (callback != null) {
      callback();
    } else {
      Navigator.of(context).pushNamedAndRemoveUntil('/', (_) => false);
    }
  }

  Future<void> _logOut() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    await _api.logout();
    if (!mounted) return;
    setState(() => _busy = false);
    _backToStart();
  }

  Future<void> _deleteAccount() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete your account?'),
        content: const Text(
            'This permanently deletes your account and the meals saved with it. '
            'This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('Delete account'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _api.deleteAccount();
      if (!mounted) return;
      setState(() => _busy = false);
      _backToStart();
    } on AuthApiException catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = e;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.user;
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(22, 14, 22, 24),
              children: [
                Text('Profile',
                    style: GoogleFonts.inter(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: AppColors.text)),
                const SizedBox(height: 16),
                AppCard(
                  child: Row(children: [
                    const IconContainer(icon: Icons.person_outline, size: 44),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('SIGNED IN AS',
                                style: GoogleFonts.inter(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: .05,
                                    color: AppColors.textSecondary)),
                            const SizedBox(height: 2),
                            Text(user?.email ?? 'Your account',
                                style: GoogleFonts.inter(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.text)),
                          ]),
                    ),
                  ]),
                ),
                const DisclaimerBanner(
                    'Research prototype. Outputs are estimates and predictions, not diagnoses.'),
                if (_error != null) AuthErrorText(_error!),
                FilledButton(
                  style: primaryButtonStyle(),
                  onPressed: _busy ? null : _logOut,
                  child: _busy ? const ButtonSpinner() : const Text('Log out'),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: _busy ? null : _deleteAccount,
                  style: TextButton.styleFrom(foregroundColor: AppColors.danger),
                  child: const Text('Delete my account'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
