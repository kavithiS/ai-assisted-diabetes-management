import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/features/onboarding/data/health_profile.dart';
import 'package:mobile_app/features/onboarding/questionnaire_screen.dart';

void main() {
  testWidgets(
      'saves only entered answers and restores them for the same account',
      (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final store = MemoryHealthProfileStore();
    var completed = false;
    await tester.pumpWidget(const SizedBox());
    await tester.pumpWidget(MaterialApp(
      home: QuestionnaireScreen(
        userId: 'account-one',
        store: store,
        onCompleted: () => completed = true,
      ),
    ));

    expect(await store.load('account-one'), isNull);
    await tester.tap(find.text('Red Rice'));
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Type 2'));
    await tester.enterText(find.byType(TextFormField), '4');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('High').first);
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('No, never'));
    await tester.tap(find.text('Save profile'));
    await tester.pumpAndSettle();

    expect(completed, isTrue);
    final saved = await store.load('account-one');
    expect(saved?.answer('staple_food'), 'Red Rice');
    expect(saved?.answer('diabetes_type'), 'Type 2');
    expect(saved?.answer('years_since_diagnosis'), '4');
    expect(saved?.answer('foot_numbness'), 'No, never');
    expect(saved?.answer('smokes'), isNull);
    expect(await store.load('another-account'), isNull);

    await tester.pumpWidget(const SizedBox());
    await tester.pumpWidget(MaterialApp(
      home: QuestionnaireScreen(
        userId: 'account-one',
        initialProfile: saved,
        store: store,
        onCompleted: () {},
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Red Rice'), findsOneWidget);
  });
}
