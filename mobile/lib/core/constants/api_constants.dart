class ApiConstants {
  // Base URL — supports both Android emulator (10.0.2.2) and iOS/physical (localhost)
  // Change to your backend IP for physical devices
  static const String baseUrl = 'http://0.0.0.0:8000/api/v1';
  // For iOS simulator use:  http://localhost:8000/api/v1
  // For physical device use: http://YOUR_MACHINE_IP:8000/api/v1

  // Auth
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String me = '/auth/me';

  // Applications
  static const String applications = '/applications';
  static String applicationById(int id) => '/applications/$id';
  static String extractDocs(int id) => '/applications/$id/extract-docs';
  static String extractedData(int id) => '/applications/$id/extracted-data';
  static String auditLogs(int id) => '/applications/$id/audit-logs';
  static String receipt(int id) => '/applications/$id/receipt';
  static String scoring(int id) => '/applications/$id/scoring';

  // Voice
  static const String voiceQuery = '/assist/voice-query';

  // Account & Scoring Simulation
  static String accountByNumber(String acc) => '/applications/accounts/$acc';
  static const String linkAccount = '/applications/accounts/link';
  static const String simulateScoring = '/scoring/simulate';
  static String guarantees(int id) => '/applications/$id/guarantees';
  static String debts(int id) => '/applications/$id/debts';

  // Timeouts
  static const int connectTimeout = 15000;
  static const int receiveTimeout = 30000;
}
