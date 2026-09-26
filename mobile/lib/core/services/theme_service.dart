import 'package:flutter/material.dart';
import 'storage_service.dart';

/// Global reactive theme manager for OpenScore Finance.
/// Persists theme preference in secure storage and notifies all listeners.
class ThemeService extends ChangeNotifier {
  bool _isDark = false;
  bool _isInitialized = false;

  bool get isDark => _isDark;
  bool get isInitialized => _isInitialized;
  ThemeMode get themeMode => _isDark ? ThemeMode.dark : ThemeMode.light;

  Future<void> init() async {
    _isDark = await StorageService.getDarkMode();
    _isInitialized = true;
    notifyListeners();
  }

  Future<void> toggleTheme() async {
    _isDark = !_isDark;
    await StorageService.saveDarkMode(_isDark);
    notifyListeners();
  }

  Future<void> setDarkMode(bool value) async {
    if (_isDark == value) return;
    _isDark = value;
    await StorageService.saveDarkMode(value);
    notifyListeners();
  }
}
