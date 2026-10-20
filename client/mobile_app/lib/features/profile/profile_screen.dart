import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../auth/auth_widgets.dart';
import '../auth/data/account_api.dart';
import '../auth/data/auth_api.dart';
import '../meal_history/meal_history_screen.dart';
import '../meal_history/today_summary_screen.dart';
import '../onboarding/data/health_profile.dart';
import '../onboarding/questionnaire_screen.dart';

const _healthLabels = <String, String>{
  'staple_food': 'Usual staple food',
  'meals_per_day': 'Meals per day',
  'eat_out': 'Eating out',
  'sugar_in_tea': 'Sugar in drinks',
  'diabetes_type': 'Diabetes type',
  'years_since_diagnosis': 'Years since diagnosis',
  'uses_glucose_meter': 'Uses glucose meter or CGM',
  'medication': 'Medication',
  'systolic_bp': 'Systolic blood pressure',
  'diastolic_bp': 'Diastolic blood pressure',
  'activity_level': 'Activity level',
  'cholesterol': 'Cholesterol',
  'smokes': 'Smoking',
  'foot_ulcers': 'Foot ulcer history',
  'foot_numbness': 'Foot numbness',
  'checks_feet': 'Checks feet',
  'footwear': 'Usual footwear',
};

/// The Profile tab: who is signed in, log out, and delete the account.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    this.user,
    this.api,
    this.onSignedOut,
    this.onProfileUpdated,
    this.onMealHistory,
    this.onTodaySummary,
    this.healthProfileStore,
  });

  /// The signed-in patient, or `null` while it is loading or could not be loaded.
  final UserProfile? user;
  final AccountApi? api;
  final ValueChanged<UserProfile>? onProfileUpdated;
  final VoidCallback? onMealHistory;
  final VoidCallback? onTodaySummary;
  final HealthProfileStore? healthProfileStore;

  /// Called after logging out or deleting the account. By default the app returns to the
  /// start screen and clears the screens behind it.
  final VoidCallback? onSignedOut;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final AccountApi _api = widget.api ?? AccountApi();
  late final HealthProfileStore _healthStore =
      widget.healthProfileStore ?? SecureHealthProfileStore();

  bool _busy = false;
  AuthApiException? _error;
  UserProfile? _freshUser;
  HealthProfile? _healthProfile;
  String? _loadedHealthUserId;

  @override
  void initState() {
    super.initState();
    _loadHealthProfile(widget.user);
  }

  @override
  void didUpdateWidget(covariant ProfileScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.user?.userId != oldWidget.user?.userId) {
      _loadHealthProfile(widget.user);
    }
  }

  Future<void> _loadHealthProfile(UserProfile? user) async {
    if (user == null || _loadedHealthUserId == user.userId) return;
    _loadedHealthUserId = user.userId;
    try {
      final profile = await _healthStore.load(user.userId);
      if (mounted && _loadedHealthUserId == user.userId) {
        setState(() => _healthProfile = profile);
      }
    } catch (_) {
      if (mounted) setState(() => _healthProfile = null);
    }
  }

  Future<void> _editHealthProfile(UserProfile? user) async {
    if (user == null) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => QuestionnaireScreen(
        userId: user.userId,
        initialProfile: _healthProfile,
        store: _healthStore,
        onCompleted: () => Navigator.of(context).pop(),
      ),
    ));
    if (!mounted) return;
    _loadedHealthUserId = null;
    await _loadHealthProfile(user);
  }

  Future<void> _refreshAccount() async {
    try {
      final user = await _api.me();
      if (mounted) {
        setState(() => _freshUser = user);
        widget.onProfileUpdated?.call(user);
      }
    } on AuthApiException catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  Future<void> _editName(UserProfile? user) async {
    final updated = await showModalBottomSheet<UserProfile>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _EditNameSheet(api: _api, currentName: user?.displayName),
    );
    if (updated != null && mounted) {
      setState(() {
        _freshUser = updated;
        _error = null;
      });
      widget.onProfileUpdated?.call(updated);
    }
  }

  void _openMealHistory() {
    if (widget.onMealHistory != null) {
      widget.onMealHistory!();
    } else {
      Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => const MealHistoryScreen()),
      );
    }
  }

  void _openTodaySummary() {
    if (widget.onTodaySummary != null) {
      widget.onTodaySummary!();
    } else {
      Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => const TodaySummaryScreen()),
      );
    }
  }

  void _showAccountDetails(UserProfile? user) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 10, 22, 28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('Account details',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            AppListRow(title: 'Email', subtitle: user?.email ?? 'Unavailable'),
            const Divider(),
            AppListRow(
                title: 'Display name',
                subtitle: user?.displayName?.isNotEmpty == true
                    ? user!.displayName!
                    : 'Not set'),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: () {
                Navigator.pop(context);
                _refreshAccount();
              },
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Refresh account'),
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: () {
                Navigator.pop(context);
                _editName(user);
              },
              icon: const Icon(Icons.edit_outlined),
              label: const Text('Edit name'),
            ),
          ]),
        ),
      ),
    );
  }

  void _showPrivacy() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 10, 22, 28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('Your data', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            const Text(
              'Meals you save are linked to your account. Health profile answers stay on this device. You can edit them in Profile. Deleting your account also removes its local health profile and saved meals.',
              style: TextStyle(height: 1.5),
            ),
          ]),
        ),
      ),
    );
  }

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
      if (widget.user != null) {
        try {
          await _healthStore.delete(widget.user!.userId);
        } catch (_) {
          // The gateway deletion has already succeeded. Do not leave the user
          // on a deleted account because local storage is unavailable.
        }
      }
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
    final user = _freshUser ?? widget.user;
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
              children: [
                Text('Your profile',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 5),
                Text('Your account and saved meals',
                    style: GoogleFonts.manrope(
                        fontSize: 13, color: AppColors.textSecondary)),
                const SizedBox(height: 22),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppColors.primaryDark,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Row(children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: AppColors.accent,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: const Icon(Icons.person_rounded,
                          color: AppColors.primaryDark, size: 28),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('SIGNED IN AS',
                              style: GoogleFonts.manrope(
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1,
                                  color: Colors.white.withAlpha(160))),
                          const SizedBox(height: 5),
                          Text(user?.label ?? 'Your account',
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.manrope(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white)),
                        ],
                      ),
                    ),
                  ]),
                ),
                const SizedBox(height: 22),
                if (user != null &&
                    user.displayName?.trim().isNotEmpty != true) ...[
                  FilledButton.icon(
                    onPressed: () => _editName(user),
                    icon: const Icon(Icons.edit_outlined),
                    label: const Text('Add your name'),
                  ),
                  const SizedBox(height: 20),
                ],
                Text('Your account',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 10),
                AppCard(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
                  child: Column(children: [
                    AppListRow(
                      title: 'Account details',
                      subtitle: 'Email and display name',
                      leading: const IconContainer(
                          icon: Icons.person_outline_rounded, size: 40),
                      trailing: const Icon(Icons.chevron_right_rounded,
                          size: 18, color: AppColors.textSecondary),
                      onTap: () => _showAccountDetails(user),
                    ),
                    const Divider(),
                    AppListRow(
                      title: 'Health profile',
                      subtitle: _healthProfile == null
                          ? 'Add your setup answers'
                          : '${_healthProfile!.answers.length} answers saved on this device',
                      leading: const IconContainer(
                          icon: Icons.assignment_outlined, size: 40),
                      trailing: const Icon(Icons.chevron_right_rounded,
                          size: 18, color: AppColors.textSecondary),
                      onTap: () => _editHealthProfile(user),
                    ),
                    if (_healthProfile != null &&
                        _healthProfile!.answers.isNotEmpty) ...[
                      const Divider(),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (final item in _healthProfile!.answers.entries)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 7),
                                child: Text(
                                  '${_healthLabels[item.key] ?? item.key}: ${item.value}',
                                  style: GoogleFonts.manrope(
                                      fontSize: 12, color: AppColors.text),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                    const Divider(),
                    AppListRow(
                      title: 'Meal history',
                      subtitle: 'View and manage saved meals',
                      leading: const IconContainer(
                          icon: Icons.restaurant_outlined, size: 40),
                      trailing: const Icon(Icons.chevron_right_rounded,
                          size: 18, color: AppColors.textSecondary),
                      onTap: _openMealHistory,
                    ),
                    const Divider(),
                    AppListRow(
                      title: 'Today’s summary',
                      subtitle: 'Review today’s saved food',
                      leading: const IconContainer(
                          icon: Icons.today_outlined, size: 40),
                      trailing: const Icon(Icons.chevron_right_rounded,
                          size: 18, color: AppColors.textSecondary),
                      onTap: _openTodaySummary,
                    ),
                    const Divider(),
                    AppListRow(
                      title: 'Your data',
                      subtitle: 'How saved meals are managed',
                      leading: const IconContainer(
                          icon: Icons.verified_user_outlined, size: 40),
                      trailing: const Icon(Icons.chevron_right_rounded,
                          size: 18, color: AppColors.textSecondary),
                      onTap: _showPrivacy,
                    ),
                  ]),
                ),
                const DisclaimerBanner(
                    'Research prototype. Outputs are estimates and predictions, not diagnoses.'),
                if (_error != null) AuthErrorText(_error!),
                OutlinedButton.icon(
                  icon: const Icon(Icons.logout_rounded, size: 18),
                  onPressed: _busy ? null : _logOut,
                  label: _busy ? const ButtonSpinner() : const Text('Log out'),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: _busy ? null : _deleteAccount,
                  style:
                      TextButton.styleFrom(foregroundColor: AppColors.danger),
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

class _EditNameSheet extends StatefulWidget {
  const _EditNameSheet({required this.api, this.currentName});

  final AccountApi api;
  final String? currentName;

  @override
  State<_EditNameSheet> createState() => _EditNameSheetState();
}

class _EditNameSheetState extends State<_EditNameSheet> {
  final _formKey = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.currentName ?? '');
  bool _saving = false;
  AuthApiException? _error;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving || !_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final user = await widget.api.updateName(_name.text);
      if (mounted) {
        Navigator.pop(context, user);
      }
    } on AuthApiException catch (error) {
      if (mounted) {
        setState(() {
          _saving = false;
          _error = error;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
              22, 10, 22, MediaQuery.viewInsetsOf(context).bottom + 24),
          child: SingleChildScrollView(
            child: Form(
              key: _formKey,
              child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Your name',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    const Text(
                        'This name appears on your home screen and profile.'),
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: _name,
                      autofocus: true,
                      textCapitalization: TextCapitalization.words,
                      autofillHints: const [AutofillHints.name],
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _save(),
                      decoration:
                          const InputDecoration(labelText: 'Full name *'),
                      validator: (value) {
                        final name = value?.trim() ?? '';
                        if (name.isEmpty) return 'Enter your full name.';
                        if (name.length < 2 || name.length > 100) {
                          return 'Use 2 to 100 characters.';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    if (_error != null) AuthErrorText(_error!),
                    FilledButton(
                      onPressed: _saving ? null : _save,
                      child: _saving
                          ? const ButtonSpinner()
                          : const Text('Save name'),
                    ),
                  ]),
            ),
          ),
        ),
      );
}
