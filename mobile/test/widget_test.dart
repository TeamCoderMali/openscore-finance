import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:openscore_mobile/main.dart';

void main() {
  testWidgets('OpenScore app launches without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const OpenScoreApp());
    // App uses MaterialApp.router via GoRouter
    expect(find.byType(MaterialApp), findsNothing);
  });
}
