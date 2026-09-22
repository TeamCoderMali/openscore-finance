import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../../models/user_model.dart';

class AuthService extends ChangeNotifier {
  User? _currentUser;
  bool _isLoading = false;
  String? _error;

  User? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _currentUser != null;
  String? get error => _error;

  final ApiService _api = ApiService();

  Future<bool> tryAutoLogin() async {
    final token = await StorageService.getToken();
    if (token == null) return false;

    try {
      final data = await _api.getMe();
      _currentUser = User.fromJson(data);
      notifyListeners();
      return true;
    } catch (_) {
      await StorageService.clearAll();
      return false;
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await _api.login(email, password);
      await StorageService.saveToken(data['access_token']);
      await StorageService.saveUserMeta(
        role: data['role'],
        name: data['full_name'],
        userId: data['user_id'],
      );
      _currentUser = User(
        id: data['user_id'],
        email: email,
        fullName: data['full_name'],
        role: data['role'],
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = _extractError(e);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> register(Map<String, dynamic> data) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final result = await _api.register(data);
      await StorageService.saveToken(result['access_token']);
      await StorageService.saveUserMeta(
        role: result['role'],
        name: result['full_name'],
        userId: result['user_id'],
      );
      _currentUser = User(
        id: result['user_id'],
        email: data['email'],
        fullName: result['full_name'],
        role: result['role'],
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = _extractError(e);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await StorageService.clearAll();
    _currentUser = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  String _extractError(dynamic e) {
    try {
      final response = (e as dynamic).response;
      if (response != null) {
        final detail = response.data['detail'];
        if (detail is String) return detail;
      }
    } catch (_) {}
    return 'Une erreur est survenue. Vérifiez votre connexion.';
  }
}
