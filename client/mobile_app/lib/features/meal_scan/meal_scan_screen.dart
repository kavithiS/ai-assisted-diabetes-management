import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'data/meal_analysis.dart';
import 'data/meal_api.dart';
import 'meal_scan_style.dart';
import 'widgets/meal_result_view.dart';

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

enum _Stage { capture, analysing, result }

/// Meal Scan (C1): photo + meal type → detected foods and estimated nutrition.
class MealScanScreen extends StatefulWidget {
  const MealScanScreen({super.key, this.api, this.pickImage});

  /// Overridable for tests.
  final MealApi? api;
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
  MealAnalysis? _result;
  String? _error;

  bool get _canAnalyse => _image != null && _mealType != null;

  Future<void> _choosePhoto(ImageSource source) async {
    final Uint8List? bytes;
    try {
      bytes = await _pickImage(source);
    } on Exception {
      if (!mounted) return;
      setState(() => _error = 'Could not open the camera or gallery. Check app permissions.');
      return;
    }
    if (bytes == null || !mounted) return;
    setState(() {
      _image = bytes;
      _error = null;
    });
  }

  Future<void> _analyse() async {
    setState(() {
      _stage = _Stage.analysing;
      _error = null;
    });
    try {
      final result = await _api.analyze(imageBytes: _image!, mealType: _mealType!);
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
        _Stage.analysing => const _AnalysingView(),
        _Stage.result => MealResultView(analysis: _result!, onScanAgain: _reset),
      },
    );
  }

  Widget _buildCapture() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Take a photo of your meal',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: MealScanStyle.text),
        ),
        const SizedBox(height: 4),
        const Text(
          'Place the whole plate in the frame, in good light.',
          style: TextStyle(color: MealScanStyle.textSecondary),
        ),
        const SizedBox(height: 16),
        _PhotoPreview(image: _image),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                style: MealScanStyle.secondaryButton(),
                onPressed: () => _choosePhoto(ImageSource.camera),
                icon: const Icon(Icons.camera_alt_outlined),
                label: const Text('Camera'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                style: MealScanStyle.secondaryButton(),
                onPressed: () => _choosePhoto(ImageSource.gallery),
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Gallery'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        const Text(
          'Meal type',
          style: TextStyle(fontWeight: FontWeight.w600, color: MealScanStyle.text),
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
          Text(_error!, style: const TextStyle(color: MealScanStyle.danger)),
        ],
        const SizedBox(height: 24),
        FilledButton(
          style: MealScanStyle.primaryButton(),
          onPressed: _canAnalyse ? _analyse : null,
          child: const Text('Analyse meal'),
        ),
      ],
    );
  }
}

class _PhotoPreview extends StatelessWidget {
  const _PhotoPreview({required this.image});

  final Uint8List? image;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 4 / 3,
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: MealScanStyle.cardDecoration(),
        child: image == null
            ? const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.restaurant, size: 48, color: MealScanStyle.border),
                    SizedBox(height: 8),
                    Text('No photo yet', style: TextStyle(color: MealScanStyle.textSecondary)),
                  ],
                ),
              )
            : Image.memory(image!, fit: BoxFit.cover),
      ),
    );
  }
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
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: MealScanStyle.text),
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
