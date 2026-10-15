import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../meal_history/data/meal_history_api.dart';
import 'data/meal_analysis.dart';
import 'data/meal_api.dart';
import 'meal_scan_style.dart';
import 'widgets/meal_module_flow.dart';

/// Returns the bytes of a photo from [source], or `null` if the patient cancelled.
typedef MealImagePicker = Future<Uint8List?> Function(ImageSource source);

/// Default picker. `imageQuality` makes the plugin re-encode the photo (iOS HEIC becomes JPEG),
/// and the size cap keeps uploads under the API's image limit.
Future<Uint8List?> pickMealImage(ImageSource source) async {
  final file = await ImagePicker().pickImage(
    source: source,
    maxWidth: 1600,
    maxHeight: 1600,
    imageQuality: 85,
  );
  return file?.readAsBytes();
}

enum _Stage { capture, review, analysing, result }

/// Meal Scan (C1): photo + meal type → detected foods and estimated nutrition.
class MealScanScreen extends StatefulWidget {
  const MealScanScreen({super.key, this.api, this.historyApi, this.pickImage});

  /// Overridable for tests.
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

  void _openReview() {
    if (!_canAnalyse) return;
    setState(() {
      _stage = _Stage.review;
      _error = null;
    });
  }

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
        _stage = _Stage.result;
      });
    } on MealApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _stage = _Stage.capture;
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

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: MealScanStyle.background,
      child: switch (_stage) {
        _Stage.capture => _buildCapture(),
        _Stage.review => _buildReview(),
        _Stage.analysing => const _AnalysingView(),
        _Stage.result => MealModuleFlow(
            analysis: _result!,
            capturedAt: _capturedAt ?? DateTime.now(),
            onScanAgain: _reset,
            historyApi: widget.historyApi,
          ),
      },
    );
  }

  Widget _buildCapture() {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                'Scan Meal',
                style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                    color: MealScanStyle.text),
              ),
              const SizedBox(height: 4),
              const Text(
                'Frame your meal within the guide.',
                style: TextStyle(color: MealScanStyle.textSecondary),
              ),
              const SizedBox(height: 16),
              _PhotoPreview(image: _image, showGuide: _image == null),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      style: MealScanStyle.secondaryButton(),
                      onPressed: () => _choosePhoto(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt_outlined),
                      label: const Text('Take Photo'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      style: MealScanStyle.secondaryButton(),
                      onPressed: () => _choosePhoto(ImageSource.gallery),
                      icon: const Icon(Icons.photo_library_outlined),
                      label: const Text('Upload Image'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Text(
                'Works best with good lighting and a top-down angle. Make sure the full plate is visible.',
                textAlign: TextAlign.center,
                style:
                    TextStyle(fontSize: 12, color: MealScanStyle.textSecondary),
              ),
              const SizedBox(height: 20),
              const Text(
                'Meal type',
                style: TextStyle(
                    fontWeight: FontWeight.w600, color: MealScanStyle.text),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final type in MealType.values)
                    ChoiceChip(
                      label: Text(type.label),
                      selected: _mealType == type,
                      selectedColor: MealScanStyle.primary.withAlpha(40),
                      onSelected: (_) => setState(() => _mealType = type),
                    ),
                ],
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!,
                    style: const TextStyle(color: MealScanStyle.danger)),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: FilledButton(
            style: MealScanStyle.primaryButton(),
            onPressed: _canAnalyse ? _openReview : null,
            child: const Text('Review Photo'),
          ),
        ),
      ],
    );
  }

  Widget _buildReview() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            IconButton(
              tooltip: 'Back to scan',
              onPressed: () => setState(() => _stage = _Stage.capture),
              icon: const Icon(Icons.arrow_back),
            ),
            const Text(
              'Review Photo',
              style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  color: MealScanStyle.text),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _PhotoPreview(image: _image, showGuide: false),
        const SizedBox(height: 12),
        Text(
          '${_mealType!.label} · Photo is held temporarily for this scan',
          textAlign: TextAlign.center,
          style:
              const TextStyle(fontSize: 12, color: MealScanStyle.textSecondary),
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          style: MealScanStyle.primaryButton(),
          onPressed: _analyse,
          icon: const Icon(Icons.auto_awesome),
          label: const Text('Analyse meal'),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                style: MealScanStyle.secondaryButton(),
                onPressed: () => setState(() => _stage = _Stage.capture),
                child: const Text('Retake Photo'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextButton(
                onPressed: () => setState(() {
                  _image = null;
                  _stage = _Stage.capture;
                }),
                child: const Text('Choose Another'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _PhotoPreview extends StatelessWidget {
  const _PhotoPreview({required this.image, required this.showGuide});

  final Uint8List? image;
  final bool showGuide;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: showGuide ? 8 / 5 : 4 / 3,
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: MealScanStyle.cardDecoration().copyWith(
          color: showGuide ? const Color(0xFFEAF5F5) : MealScanStyle.card,
        ),
        child: image == null
            ? Stack(
                fit: StackFit.expand,
                children: [
                  Padding(
                    padding: const EdgeInsets.all(20),
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            showGuide
                                ? Icons.camera_alt_outlined
                                : Icons.restaurant,
                            size: 48,
                            color: MealScanStyle.primary,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            showGuide
                                ? 'Frame your meal within the guide'
                                : 'No photo yet',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                color: MealScanStyle.textSecondary),
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (showGuide)
                    IgnorePointer(
                      child: CustomPaint(painter: _FrameGuidePainter()),
                    ),
                ],
              )
            : Image.memory(image!, fit: BoxFit.cover),
      ),
    );
  }
}

class _FrameGuidePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = MealScanStyle.primary
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
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _AnalysingView extends StatelessWidget {
  const _AnalysingView();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: MealScanStyle.primary),
            SizedBox(height: 20),
            Text(
              'Analysing your meal…',
              style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: MealScanStyle.text),
            ),
            SizedBox(height: 8),
            Text(
              'Recognising foods, estimating portions and looking up nutrition.',
              textAlign: TextAlign.center,
              style: TextStyle(color: MealScanStyle.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
