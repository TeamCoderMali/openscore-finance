import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'core/services/api_service.dart';
import 'core/services/auth_service.dart';
import 'core/services/theme_service.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize French date formatting symbols (fixes LocaleDataException)
  await initializeDateFormatting('fr_FR', null);
  await initializeDateFormatting('fr', null);

  // Initialize API service
  ApiService().init();

  // Lock to portrait
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  runApp(const OpenScoreApp());
}

class OpenScoreApp extends StatefulWidget {
  const OpenScoreApp({super.key});

  @override
  State<OpenScoreApp> createState() => _OpenScoreAppState();
}

class _OpenScoreAppState extends State<OpenScoreApp> {
  late final AuthService _authService;
  late final ThemeService _themeService;

  @override
  void initState() {
    super.initState();
    _authService = AuthService();
    _themeService = ThemeService();
    _init();
  }

  Future<void> _init() async {
    await _themeService.init();
    await _authService.tryAutoLogin();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: _authService),
        ChangeNotifierProvider<ThemeService>.value(value: _themeService),
      ],
      child: Consumer<ThemeService>(
        builder: (context, themeService, _) {
          return MaterialApp.router(
            title: 'OpenScore Finance',
            debugShowCheckedModeBanner: false,
            themeMode: themeService.themeMode,
            theme: AppTheme.light(),
            darkTheme: AppTheme.dark(),
            routerConfig: appRouter,
          );
        },
      ),
    );
  }
}
