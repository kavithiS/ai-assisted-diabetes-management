import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../meal_history/data/meal_history_api.dart';
import 'data/meal_analysis.dart';
import 'data/meal_api.dart';
import 'widgets/meal_module_flow.dart';

typedef MealImagePicker = Future<Uint8List?> Function(ImageSource source);

Future<Uint8List?> pickMealImage(ImageSource source) async {
  final file = await ImagePicker().pickImage(
    source: source,
    maxWidth: 1280,
    maxHeight: 1280,
  );
  return file?.readAsBytes();
}

enum _Stage { capture, review, analysing, result }

class MealScanScreen extends StatefulWidget {
  const MealScanScreen({super.key, this.api, this.historyApi, this.pickImage});

  final MealApi? api;
  final MealHistoryApi? historyApi;
  final MealImagePicker? pickImage;

  @override
  State<MealScanScreen> createState() => _MealScanScreenState();
}

class _MealScanScreenState extends State<MealScanScreen> {
  late final MealApi _api = widget.api ?? MealApi();
  late final MealImagePicker _pickImage = widget.pickImage ?? pickMealImage;

  _Stage _stage = _Stage.capture;
  Uint8List? _image;
  MealType? _mealType;
  DateTime? _capturedAt;
  MealAnalysis? _result;
  String? _error;

  bool get _canAnalyse => _image != null && _mealType != null;

  Future<void> _choosePhoto(ImageSource source) async {
    final Uint8List? bytes;
    try {
      bytes = await _pickImage(source);
    } on Exception {
      if (!mounted) return;
      setState(() => _error =
          'Could not open the camera or gallery. Check app permissions.');
      return;
    }
    if (bytes == null || !mounted) return;
    setState(() {
      _image = bytes;
      _capturedAt = DateTime.now();
      _error = null;
    });
  }

  Future<void> _analyse() async {
    setState(() {
      _stage = _Stage.analysing;
      _error = null;
    });
    try {
      final result = await _api.analyze(
        imageBytes: _image!,
        mealType: _mealType!,
        capturedAt: _capturedAt,
      );
      if (!mounted) return;
      setState(() {
        _result = result;
      });
    } on MealApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = _Stage.capture;
        _error = e.message;
      });
    }
  }

  void _reset() {
    setState(() {
      _stage = _Stage.capture;
      _image = null;
      _mealType = null;
      _capturedAt = null;
      _result = null;
      _error = null;
    });
  }

  void _handleBack() {
    if (_stage == _Stage.review) {
      setState(() => _stage = _Stage.capture);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope<void>(
        canPop: _stage == _Stage.capture,
        onPopInvokedWithResult: (didPop, _) {
          if (!didPop) _handleBack();
        },
        child: switch (_stage) {
          _Stage.capture => _CaptureScreen(
              image: _image,
              mealType: _mealType,
              error: _error,
              onPickPhoto: _choosePhoto,
              onMealTypeChanged: (t) => setState(() => _mealType = t),
              onReview: _canAnalyse
                  ? () => setState(() {
                        _stage = _Stage.review;
                        _error = null;
                      })
                  : null,
            ),
          _Stage.review => _ReviewScreen(
              image: _image!,
              mealType: _mealType!,
              onBack: () => setState(() => _stage = _Stage.capture),
              onAnalyse: _analyse,
              onRetake: () => setState(() => _stage = _Stage.capture),
            ),
          _Stage.analysing => _AnalysingScreen(
              ready: _result != null,
              onCompleted: () {
                if (mounted && _stage == _Stage.analysing && _result != null) {
                  setState(() => _stage = _Stage.result);
                }
              },
            ),
          _Stage.result => MealModuleFlow(
              analysis: _result!,
              capturedAt: _capturedAt ?? DateTime.now(),
              onScanAgain: _reset,
              historyApi: widget.historyApi,
              image: _image,
            ),
        },
      );
}

// ─── Capture Screen ──────────────────────────────────────────────────────────

class _CaptureScreen extends StatelessWidget {
  const _CaptureScreen({
    required this.image,
    required this.mealType,
    this.error,
    required this.onPickPhoto,
    required this.onMealTypeChanged,
    required this.onReview,
  });

  final Uint8List? image;
  final MealType? mealType;
  final String? error;
  final void Function(ImageSource) onPickPhoto;
  final ValueChanged<MealType?> onMealTypeChanged;
  final VoidCallback? onReview;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Column(children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 18),
                children: [
                  Text('Scan Meal',
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 5),
                  Text(
                      'Capture your plate for an estimated nutrition breakdown.',
                      style: GoogleFonts.manrope(
                          fontSize: 12.5, color: AppColors.textSecondary)),
                  const SizedBox(height: 18),
                  AspectRatio(
                    aspectRatio: 4 / 3,
                    child: Container(
                      decoration: BoxDecoration(
                        color: AppColors.primaryDark,
                        borderRadius: BorderRadius.circular(24),
                      ),
                      clipBehavior: Clip.antiAlias,
                      child: image == null
                          ? Stack(fit: StackFit.expand, children: [
                              Positioned(
                                right: -35,
                                top: -45,
                                child: Container(
                                  width: 160,
                                  height: 160,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                        color: Colors.white.withAlpha(18),
                                        width: 28),
                                  ),
                                ),
                              ),
                              Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Container(
                                      width: 54,
                                      height: 54,
                                      decoration: BoxDecoration(
                                        color: Colors.white.withAlpha(22),
                                        borderRadius: BorderRadius.circular(17),
                                      ),
                                      child: const Icon(
                                          Icons.camera_alt_outlined,
                                          size: 26,
                                          color: Colors.white),
                                    ),
                                    const SizedBox(height: 12),
                                    Text('Frame your meal within the guide',
                                        textAlign: TextAlign.center,
                                        style: GoogleFonts.manrope(
                                            fontSize: 12.5,
                                            fontWeight: FontWeight.w700,
                                            color: Colors.white)),
                                  ]),
                              IgnorePointer(
                                  child: CustomPaint(
                                      painter: _FrameGuidePainter())),
                            ])
                          : Image.memory(image!, fit: BoxFit.cover),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Text('Meal type',
                      style: GoogleFonts.manrope(
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          color: AppColors.text)),
                  const SizedBox(height: 9),
                  ChipRow(
                    options: MealType.values.map((t) => t.label).toList(),
                    selected: mealType?.label,
                    onChanged: (label) => onMealTypeChanged(
                        MealType.values.firstWhere((t) => t.label == label)),
                  ),
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.primaryLight,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Row(children: [
                      Icon(Icons.light_mode_outlined,
                          size: 17, color: AppColors.primary),
                      SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          'For the clearest result, use good light and a top-down angle.',
                          style: TextStyle(
                              fontSize: 11.5,
                              height: 1.35,
                              color: AppColors.primaryDark),
                        ),
                      ),
                    ]),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 14),
                    Text(error!,
                        style: const TextStyle(
                            color: AppColors.danger, fontSize: 13)),
                  ],
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Column(children: [
                Row(children: [
                  Expanded(
                    child: FilledButton.icon(
                      style: primaryButtonStyle(),
                      onPressed: () => onPickPhoto(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt_outlined, size: 17),
                      label: const Text('Take Photo'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      style: ghostButtonStyle(),
                      onPressed: () => onPickPhoto(ImageSource.gallery),
                      icon: const Icon(Icons.image_outlined, size: 17),
                      label: const Text('Upload Image'),
                    ),
                  ),
                ]),
                if (onReview != null) ...[
                  const SizedBox(height: 10),
                  FilledButton(
                    style: primaryButtonStyle(),
                    onPressed: onReview,
                    child: const Text('Review Photo'),
                  ),
                ],
              ]),
            ),
          ]),
        ),
      );
}

// ─── Review Screen ───────────────────────────────────────────────────────────

class _ReviewScreen extends StatelessWidget {
  const _ReviewScreen({
    required this.image,
    required this.mealType,
    required this.onBack,
    required this.onAnalyse,
    required this.onRetake,
  });

  final Uint8List image;
  final MealType mealType;
  final VoidCallback onBack;
  final VoidCallback onAnalyse;
  final VoidCallback onRetake;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Column(children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(22, 8, 22, 16),
                children: [
                  // Back row
                  Padding(
                    padding: const EdgeInsets.only(top: 8, bottom: 16),
                    child: Row(children: [
                      Tooltip(
                        message: 'Back',
                        child: InkWell(
                          onTap: onBack,
                          borderRadius: BorderRadius.circular(11),
                          child: Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: AppColors.card,
                              borderRadius: BorderRadius.circular(11),
                              border: Border.all(color: AppColors.border),
                            ),
                            child: const Icon(Icons.arrow_back,
                                size: 17, color: AppColors.text),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text('Review Meal',
                          style: GoogleFonts.manrope(
                              fontSize: 18,
                              fontWeight: FontWeight.w800,
                              color: AppColors.text)),
                    ]),
                  ),
                  // Photo
                  Stack(children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: AspectRatio(
                        aspectRatio: 4 / 3,
                        child: Image.memory(image, fit: BoxFit.cover),
                      ),
                    ),
                    Positioned(
                      bottom: 10,
                      left: 10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 11, vertical: 5),
                        decoration: BoxDecoration(
                          color: AppColors.primaryLight,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(mealType.label,
                            style: GoogleFonts.manrope(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: AppColors.primaryDark)),
                      ),
                    ),
                  ]),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: Text(
                      'Use a clear image with the full plate visible for better recognition.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.manrope(
                          fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(22, 0, 22, 12),
              child: Column(children: [
                FilledButton.icon(
                  style: primaryButtonStyle(),
                  onPressed: onAnalyse,
                  icon: const Icon(Icons.auto_awesome, size: 17),
                  label: const Text('Analyze Meal'),
                ),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      style: secondaryButtonStyle(),
                      onPressed: onRetake,
                      child: const Text('Retake Photo'),
                    ),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: OutlinedButton(
                      style: ghostButtonStyle(),
                      onPressed: onRetake,
                      child: const Text('Choose Another'),
                    ),
                  ),
                ]),
              ]),
            ),
          ]),
        ),
      );
}

// ─── Analysing Screen ─────────────────────────────────────────────────────────

class _AnalysingScreen extends StatefulWidget {
  const _AnalysingScreen({required this.ready, required this.onCompleted});

  final bool ready;
  final VoidCallback onCompleted;

  @override
  State<_AnalysingScreen> createState() => _AnalysingScreenState();
}

class _AnalysingScreenState extends State<_AnalysingScreen> {
  int _step = 0;
  Timer? _timer;
  Timer? _finishTimer;

  static const _steps = [
    'Analysing photo',
    'Reviewing food matches',
    'Preparing nutrition estimates',
    'Result ready',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.ready) _completeSteps();
  }

  @override
  void didUpdateWidget(covariant _AnalysingScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.ready && !oldWidget.ready) _completeSteps();
  }

  void _completeSteps() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(milliseconds: 250), (timer) {
      if (!mounted) return;
      setState(() => _step++);
      if (_step == _steps.length) {
        timer.cancel();
        _finishTimer = Timer(const Duration(milliseconds: 350), () {
          if (mounted) widget.onCompleted();
        });
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _finishTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    color: AppColors.primaryLight,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: const Icon(Icons.auto_awesome,
                      size: 44, color: AppColors.primary),
                ),
                const SizedBox(height: 22),
                Text('Analysing Your Meal',
                    style: GoogleFonts.manrope(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: AppColors.text)),
                const SizedBox(height: 6),
                Text(
                    widget.ready
                        ? 'Your result is ready'
                        : 'Checking your photo. Please wait…',
                    style: GoogleFonts.manrope(
                        fontSize: 12.5, color: AppColors.textSecondary)),
                const SizedBox(height: 22),
                SizedBox(
                  width: 280,
                  child: Column(
                    children: [
                      for (var i = 0; i < _steps.length; i++)
                        _AnalysisStep(
                          label: _steps[i],
                          state: i < _step
                              ? _StepState.done
                              : i == _step
                                  ? _StepState.active
                                  : _StepState.pending,
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

enum _StepState { done, active, pending }

class _AnalysisStep extends StatelessWidget {
  const _AnalysisStep({required this.label, required this.state});
  final String label;
  final _StepState state;

  @override
  Widget build(BuildContext context) {
    final (bg, iconColor, icon) = switch (state) {
      _StepState.done => (
          AppColors.successBg,
          AppColors.success,
          Icons.check_circle_outline
        ),
      _StepState.active => (AppColors.primaryLight, AppColors.primary, null),
      _StepState.pending => (AppColors.border, AppColors.border, null),
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: 2),
      child: Row(children: [
        Container(
          width: 34,
          height: 34,
          margin: const EdgeInsets.symmetric(vertical: 6),
          decoration:
              BoxDecoration(color: bg, borderRadius: BorderRadius.circular(9)),
          child: icon != null
              ? Icon(icon, size: 16, color: iconColor)
              : state == _StepState.active
                  ? const Center(
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  : null,
        ),
        const SizedBox(width: 11),
        Text(label,
            style: GoogleFonts.manrope(
                fontSize: 13,
                color: state == _StepState.pending
                    ? AppColors.textSecondary
                    : AppColors.text)),
      ]),
    );
  }
}

// ─── Frame Guide Painter ────────────────────────────────────────────────────

class _FrameGuidePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.primary
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    const inset = 20.0;
    const length = 28.0;
    final path = Path()
      ..moveTo(inset, inset + length)
      ..lineTo(inset, inset)
      ..lineTo(inset + length, inset)
      ..moveTo(size.width - inset - length, inset)
      ..lineTo(size.width - inset, inset)
      ..lineTo(size.width - inset, inset + length)
      ..moveTo(inset, size.height - inset - length)
      ..lineTo(inset, size.height - inset)
      ..lineTo(inset + length, size.height - inset)
      ..moveTo(size.width - inset - length, size.height - inset)
      ..lineTo(size.width - inset, size.height - inset)
      ..lineTo(size.width - inset, size.height - inset - length);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter _) => false;
}
