import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'data/foot_analysis.dart';
import 'data/foot_api.dart';
import 'foot_monitor_style.dart';
import 'widgets/foot_result_view.dart';

typedef FootImagePicker = Future<Uint8List?> Function(ImageSource source);

Future<Uint8List?> pickFootImage(ImageSource source) async {
  final file = await ImagePicker().pickImage(
    source: source,
    maxWidth: 1280,
    maxHeight: 1280,
  );
  return file?.readAsBytes();
}

enum _Stage { capture, analysing, result }

/// Foot Monitor (C4): photograph a foot and get an estimated risk band.
/// The photo is sent for analysis and never stored.
class FootMonitorScreen extends StatefulWidget {
  const FootMonitorScreen({super.key, this.api, this.pickImage});

  /// Injected in tests.
  final FootApi? api;
  final FootImagePicker? pickImage;

  @override
  State<FootMonitorScreen> createState() => _FootMonitorScreenState();
}

class _FootMonitorScreenState extends State<FootMonitorScreen> {
  late final FootApi _api = widget.api ?? FootApi();
  late final FootImagePicker _pickImage = widget.pickImage ?? pickFootImage;

  _Stage _stage = _Stage.capture;
  Uint8List? _image;
  FootAnalysis? _result;
  String? _error;

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
    final image = _image;
    if (image == null) return;
    setState(() {
      _stage = _Stage.analysing;
      _error = null;
    });
    try {
      final result = await _api.analyze(imageBytes: image);
      if (!mounted) return;
      setState(() {
        _result = result;
        _stage = _Stage.result;
      });
    } on FootApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = _Stage.capture;
        _error = e.message;
      });
    }
  }

  void _reset() => setState(() {
        _stage = _Stage.capture;
        _image = null;
        _result = null;
        _error = null;
      });

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: FootMonitorStyle.background,
        body: SafeArea(
          child: switch (_stage) {
            _Stage.capture => _CaptureView(
                image: _image,
                error: _error,
                onPickPhoto: _choosePhoto,
                onAnalyse: _image == null ? null : _analyse,
              ),
            _Stage.analysing => const _AnalysingView(),
            _Stage.result => FootResultView(
                analysis: _result!,
                image: _image,
                onScanAgain: _reset,
              ),
          },
        ),
      );
}

class _CaptureView extends StatelessWidget {
  const _CaptureView({
    required this.image,
    required this.error,
    required this.onPickPhoto,
    required this.onAnalyse,
  });

  final Uint8List? image;
  final String? error;
  final ValueChanged<ImageSource> onPickPhoto;
  final VoidCallback? onAnalyse;

  static const _tips = [
    'Use good light, and wash and dry your foot first.',
    'Show the whole sole and the area you are worried about.',
    'Hold the phone about 30 cm away and keep it steady.',
  ];

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(22, 16, 22, 24),
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: FootMonitorStyle.primaryLight,
                  borderRadius: BorderRadius.circular(9),
                ),
                child: const Icon(Icons.healing_outlined, color: FootMonitorStyle.primary),
              ),
              const SizedBox(width: 13),
              const Expanded(child: Text('Foot Check', style: FootMonitorStyle.title)),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: FootMonitorStyle.cardDecoration(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('HOW TO TAKE THE PHOTO', style: FootMonitorStyle.sectionLabel),
                const SizedBox(height: 8),
                for (final tip in _tips)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.check_circle_outline,
                            size: 17, color: FootMonitorStyle.primary),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(tip,
                              style: const TextStyle(
                                  fontSize: 13.5, height: 1.45, color: FootMonitorStyle.text)),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _PhotoPreview(image: image),
          const SizedBox(height: 14),
          if (error != null) ...[
            Container(
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(
                color: FootMonitorStyle.dangerBg,
                borderRadius: BorderRadius.circular(FootMonitorStyle.controlRadius),
              ),
              child: Text(error!,
                  style: const TextStyle(fontSize: 13, color: FootMonitorStyle.danger)),
            ),
            const SizedBox(height: 14),
          ],
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  style: FootMonitorStyle.secondaryButton(),
                  onPressed: () => onPickPhoto(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt_outlined),
                  label: const Text('Take Photo'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  style: FootMonitorStyle.secondaryButton(),
                  onPressed: () => onPickPhoto(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Gallery'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          FilledButton(
            style: FootMonitorStyle.primaryButton(),
            onPressed: onAnalyse,
            child: const Text('Analyse Photo'),
          ),
          const SizedBox(height: 14),
          const Text(
            'Research prototype. The result is an estimate, not a diagnosis. '
            'Your photo is not stored.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: FootMonitorStyle.textSecondary),
          ),
        ],
      );
}

class _PhotoPreview extends StatelessWidget {
  const _PhotoPreview({required this.image});

  final Uint8List? image;

  @override
  Widget build(BuildContext context) {
    if (image != null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(FootMonitorStyle.cardRadius),
        child: Image.memory(image!, height: 220, fit: BoxFit.cover),
      );
    }
    return Container(
      height: 180,
      decoration: FootMonitorStyle.cardDecoration(color: FootMonitorStyle.primaryLight),
      child: const Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.add_a_photo_outlined, size: 40, color: FootMonitorStyle.primary),
          SizedBox(height: 8),
          Text('No photo yet',
              style: TextStyle(fontSize: 13.5, color: FootMonitorStyle.textSecondary)),
        ],
      ),
    );
  }
}

class _AnalysingView extends StatelessWidget {
  const _AnalysingView();

  @override
  Widget build(BuildContext context) => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: FootMonitorStyle.primary),
            SizedBox(height: 16),
            Text('Analysing your foot image…', style: FootMonitorStyle.body),
          ],
        ),
      );
}
