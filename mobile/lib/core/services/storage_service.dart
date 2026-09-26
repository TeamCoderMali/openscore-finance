import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class StorageService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static const _tokenKey = 'osf_access_token';
  static const _roleKey = 'osf_user_role';
  static const _nameKey = 'osf_user_name';
  static const _userIdKey = 'osf_user_id';
  static const _themeKey = 'osf_dark_mode';

  // Token
  static Future<void> saveToken(String token) async =>
      await _storage.write(key: _tokenKey, value: token);

  static Future<String?> getToken() async =>
      await _storage.read(key: _tokenKey);

  static Future<void> deleteToken() async =>
      await _storage.delete(key: _tokenKey);

  // User metadata
  static Future<void> saveUserMeta({
    required String role,
    required String name,
    required int userId,
  }) async {
    await _storage.write(key: _roleKey, value: role);
    await _storage.write(key: _nameKey, value: name);
    await _storage.write(key: _userIdKey, value: userId.toString());
  }

  static Future<String?> getRole() async => await _storage.read(key: _roleKey);
  static Future<String?> getName() async => await _storage.read(key: _nameKey);
  static Future<int?> getUserId() async {
    final val = await _storage.read(key: _userIdKey);
    return val != null ? int.tryParse(val) : null;
  }

  // Theme
  static Future<void> saveDarkMode(bool value) async =>
      await _storage.write(key: _themeKey, value: value.toString());

  static Future<bool> getDarkMode() async {
    final val = await _storage.read(key: _themeKey);
    return val == 'true';
  }

  // Clear all
  static Future<void> clearAll() async => await _storage.deleteAll();
}
