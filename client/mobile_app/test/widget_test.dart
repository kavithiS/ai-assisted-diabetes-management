import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile_app/features/auth/data/auth_tokens.dart';
import 'package:mobile_app/features/meal_history/meal_history_screen.dart';
import 'package:mobile_app/features/meal_history/today_summary_screen.dart';
import 'package:mobile_app/main.dart';

import 'features/auth/auth_test_support.dart';

void main() {
  void useTallView(WidgetTester tester) {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
  }

  late AuthSession session;

  Widget shell(FakeGateway gateway, {Map<String, WidgetBuilder>? routes}) =>
      MaterialApp(
        home: HomeShell(accountApi: gateway.accountApi(session)),
        routes: routes ?? const {},
      );

  setUp(() async {
    // The app's own session stores tokens in secure storage; tests use the in-memory mock.
    FlutterSecureStorage.setMockInitialValues({});
    session = await signedInSession();
  });

  testWidgets('home screen shows all navigation tabs', (tester) async {
    useTallView(tester);

    await tester.pumpWidget(shell(FakeGateway((_) => meResponse())));
    await tester.pump();

    for (final label in ['Home', 'Meals', 'Insights', 'Foot', 'Profile']) {
      expect(find.text(label), findsWidgets, reason: 'tab "$label" not found');
    }

    await tester.tap(find.text('Meals'));
    await tester.pumpAndSettle();
    expect(find.text('Scan Meal'), findsOneWidget);
  });

  testWidgets('home greets the real signed-in user and shows no invented data',
      (tester) async {
    useTallView(tester);

    await tester.pumpWidget(shell(FakeGateway((_) =>
        meResponse(email: 'amara@example.test', displayName: 'Amara Perera'))));
    await tester.pumpAndSettle();

    expect(find.text('Amara'), findsOneWidget);
    expect(find.text('amara@example.test'), findsNothing);
    expect(find.text('No score yet'), findsOneWidget);
    expect(find.text('No readings yet'), findsOneWidget);
    expect(find.textContaining('mg/dL'), findsNothing);
    expect(find.text('Kavindu Perera'), findsNothing);
    expect(find.text('82'), findsNothing);
  });

  testWidgets('home still works when the user cannot be loaded',
      (tester) async {
    useTallView(tester);
    final gateway =
        FakeGateway((_) => errorEnvelope(502, 'UPSTREAM_UNAVAILABLE', 'Down.'));

    await tester.pumpWidget(shell(gateway));
    await tester.pumpAndSettle();

    expect(find.text('Welcome'), findsOneWidget);
    expect(find.text('Meal history'), findsOneWidget);
  });

  testWidgets('an expired session sends the user back to the start screen',
      (tester) async {
    useTallView(tester);
    final gateway = FakeGateway(
        (_) => errorEnvelope(401, 'UNAUTHORIZED', 'Not signed in.'));

    // The shell sits on top of a start screen, as in the real app.
    await tester.pumpWidget(MaterialApp(
      initialRoute: '/shell',
      routes: {
        '/': (_) => const Scaffold(body: Text('START SCREEN')),
        '/shell': (_) => HomeShell(accountApi: gateway.accountApi(session)),
      },
    ));
    expect(find.text('START SCREEN'), findsNothing);
    await tester.pumpAndSettle();

    expect(find.text('START SCREEN'), findsOneWidget);
    expect(find.byType(HomeShell), findsNothing);
  });

  testWidgets('meal history and today summary can be opened from home',
      (tester) async {
    useTallView(tester);

    await tester.pumpWidget(shell(FakeGateway((_) => meResponse())));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Meal history'));
    await tester.pump();
    await tester.pump();
    expect(find.byType(MealHistoryScreen), findsOneWidget);
    tester.state<NavigatorState>(find.byType(Navigator)).pop();
    await tester.pumpAndSettle();

    await tester.tap(find.text("Today's summary"));
    await tester.pump();
    await tester.pump();
    expect(find.byType(TodaySummaryScreen), findsOneWidget);
  });

  testWidgets('the Profile tab shows the account and Log out', (tester) async {
    useTallView(tester);

    await tester.pumpWidget(
        shell(FakeGateway((_) => meResponse(email: 'amara@example.test'))));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();

    expect(find.text('Log out'), findsOneWidget);
    expect(find.text('SIGNED IN AS'), findsOneWidget);
  });
}
