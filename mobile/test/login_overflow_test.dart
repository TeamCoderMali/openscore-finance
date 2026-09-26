import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:openscore_mobile/core/theme/app_theme.dart';
import 'package:openscore_mobile/core/services/auth_service.dart';
import 'package:openscore_mobile/features/auth/login_screen.dart';

void main() {
  testWidgets(
      'LoginScreen renders without any RenderFlex overflow at 342px width',
      (WidgetTester tester) async {
    // Set screen size to narrow width (342px, exactly matching the error report)
    tester.view.physicalSize = const Size(342 * 3, 800 * 3);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthService()),
        ],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const LoginScreen(),
        ),
      ),
    );

    // Let any animations or initial layout settle
    await tester.pumpAndSettle();

    // Verify key elements exist and no FlutterError was thrown
    expect(find.text('OpenScore'), findsWidgets);
    expect(find.text('Connexion Conseiller'), findsOneWidget);
    expect(find.text('Se connecter'), findsOneWidget);
    expect(find.text('Pas encore de compte ?'), findsOneWidget);
    expect(find.text('Créer un compte'), findsOneWidget);
  });
}
