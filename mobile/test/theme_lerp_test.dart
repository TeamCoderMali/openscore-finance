import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:openscore_mobile/core/theme/app_theme.dart';
import 'package:openscore_mobile/shared/widgets/shared_widgets.dart';

void main() {
  test('AppTheme light and dark lerp smoothly without inherit mismatch', () {
    final light = AppTheme.light();
    final dark = AppTheme.dark();

    for (double t = 0.0; t <= 1.0; t += 0.1) {
      final lerped = ThemeData.lerp(light, dark, t);
      expect(lerped, isNotNull);
      expect(lerped.textTheme.labelLarge?.inherit, isTrue);
      expect(lerped.textTheme.bodyMedium?.inherit, isTrue);
    }
  });

  testWidgets('Theme transition with OutlinedButton and ElevatedButton animates smoothly', (tester) async {
    final lightTheme = AppTheme.light();
    final darkTheme = AppTheme.dark();

    final themeNotifier = ValueNotifier<ThemeData>(lightTheme);

    await tester.pumpWidget(
      ValueListenableBuilder<ThemeData>(
        valueListenable: themeNotifier,
        builder: (context, currentTheme, _) {
          return MaterialApp(
            theme: currentTheme,
            home: Scaffold(
              body: Column(
                children: [
                  PrimaryButton(
                    label: 'Connexion Test',
                    onPressed: () {},
                  ),
                  OutlinedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.flash_on),
                    label: const Text(
                      'Compte démo test',
                      style: TextStyle(inherit: true, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );

    // Initial frame
    await tester.pumpAndSettle();

    // Switch theme to dark
    themeNotifier.value = darkTheme;

    // Pump intermediate frames of the 200ms AnimatedTheme / AnimatedDefaultTextStyle lerp
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();

    // Switch back to light
    themeNotifier.value = lightTheme;
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
  });
}
