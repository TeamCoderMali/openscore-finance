import 'package:dio/dio.dart';
import '../constants/api_constants.dart';
import 'storage_service.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  late final Dio _dio;

  void init() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConstants.baseUrl,
      connectTimeout: const Duration(milliseconds: ApiConstants.connectTimeout),
      receiveTimeout: const Duration(milliseconds: ApiConstants.receiveTimeout),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Auth token interceptor
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await StorageService.getToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        // Let caller handle errors
        return handler.next(error);
      },
    ));
  }

  // ── Generic request helpers ──────────────────────────────────────
  Future<Response> get(String path, {Map<String, dynamic>? queryParams}) async {
    return await _dio.get(path, queryParameters: queryParams);
  }

  Future<Response> post(String path, {dynamic data}) async {
    return await _dio.post(path, data: data);
  }

  Future<Response> put(String path, {dynamic data}) async {
    return await _dio.put(path, data: data);
  }

  Future<Response> postFormData(String path, FormData formData) async {
    return await _dio.post(
      path,
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );
  }

  // ── Auth ─────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post(ApiConstants.login, data: {
      'email': email,
      'password': password,
    });
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> register(Map<String, dynamic> data) async {
    final response = await _dio.post(ApiConstants.register, data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getMe() async {
    final response = await _dio.get(ApiConstants.me);
    return response.data as Map<String, dynamic>;
  }

  // ── Applications ────────────────────────────────────────────────
  Future<Map<String, dynamic>> getApplications() async {
    final response = await _dio.get(ApiConstants.applications);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createApplication(Map<String, dynamic> data) async {
    final response = await _dio.post(ApiConstants.applications, data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> extractDocs(int appId, FormData formData) async {
    final response = await _dio.post(
      ApiConstants.extractDocs(appId),
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getAuditLogs(int appId) async {
    final response = await _dio.get(ApiConstants.auditLogs(appId));
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getReceipt(int appId) async {
    final response = await _dio.get(ApiConstants.receipt(appId));
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getScoring(int appId) async {
    final response = await _dio.get(ApiConstants.scoring(appId));
    return response.data as Map<String, dynamic>;
  }

  // ── Account Operations ───────────────────────────────────────────
  Future<Map<String, dynamic>> lookupAccount(String accountNumber) async {
    final response = await _dio.get(ApiConstants.accountByNumber(accountNumber));
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> linkAccount(String accountNumber) async {
    final response = await _dio.post(ApiConstants.linkAccount, data: {
      'account_number': accountNumber,
    });
    return response.data as Map<String, dynamic>;
  }

  // ── Scoring Simulation (Prospect Base 100) ────────────────────────
  Future<Map<String, dynamic>> simulateScoring(Map<String, dynamic> data) async {
    final response = await _dio.post(ApiConstants.simulateScoring, data: data);
    return response.data as Map<String, dynamic>;
  }

  // ── Multi-Guarantees ──────────────────────────────────────────────
  Future<List<dynamic>> getGuarantees(int appId) async {
    final response = await _dio.get(ApiConstants.guarantees(appId));
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> addGuarantee(int appId, Map<String, dynamic> data) async {
    final response = await _dio.post(ApiConstants.guarantees(appId), data: data);
    return response.data as Map<String, dynamic>;
  }

  // ── Multi-Debts ───────────────────────────────────────────────────
  Future<List<dynamic>> getDebts(int appId) async {
    final response = await _dio.get(ApiConstants.debts(appId));
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> addDebt(int appId, Map<String, dynamic> data) async {
    final response = await _dio.post(ApiConstants.debts(appId), data: data);
    return response.data as Map<String, dynamic>;
  }

  // ── Voice Assist ─────────────────────────────────────────────────
  Future<Map<String, dynamic>> voiceQuery(
    String queryText, {
    String language = 'fr',
    Map<String, dynamic>? context,
    int? applicationId,
  }) async {
    final payload = <String, dynamic>{
      'query_text': queryText,
      'language': language,
    };
    if (context != null) payload['context'] = context;
    if (applicationId != null) payload['application_id'] = applicationId;

    final response = await _dio.post(ApiConstants.voiceQuery, data: payload);
    return response.data as Map<String, dynamic>;
  }
}
