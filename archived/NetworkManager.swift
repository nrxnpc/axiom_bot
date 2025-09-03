import Foundation
import Combine

// MARK: - Network Error
enum NetworkError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingError
    case networkUnavailable
    case serverError(Int)
    case timeout
    case unauthorized
    case invalidCredentials
    case userExists
    case qrCodeAlreadyUsed
    case qrCodeNotFound
    case insufficientPermissions
    
    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Неверный URL"
        case .noData: return "Нет данных"
        case .decodingError: return "Ошибка декодирования"
        case .networkUnavailable: return "Сеть недоступна"
        case .serverError(let code): return "Ошибка сервера: \(code)"
        case .timeout: return "Превышено время ожидания"
        case .unauthorized: return "Необходима авторизация"
        case .invalidCredentials: return "Неверные учетные данные"
        case .userExists: return "Пользователь с таким email уже существует"
        case .qrCodeAlreadyUsed: return "QR-код уже использован"
        case .qrCodeNotFound: return "QR-код не найден"
        case .insufficientPermissions: return "Недостаточно прав доступа"
        }
    }
}

// MARK: - API Models
struct APIResponse<T: Codable>: Codable {
    let success: Bool?
    let data: T?
    let error: String?
    let message: String?
}

struct APIUser: Codable {
    let id: String
    let name: String
    let email: String
    let phone: String
    let userType: String
    let points: Int
    let role: String
    let registrationDate: String
    let isActive: Bool
    
    func toUser() -> User {
        return User(
            id: id,
            name: name,
            email: email,
            phone: phone,
            userType: User.UserType(rawValue: userType) ?? .individual,
            points: points,
            role: User.UserRole(rawValue: role) ?? .user,
            registrationDate: ISO8601DateFormatter().date(from: registrationDate) ?? Date(),
            isActive: isActive
        )
    }
}

struct APICar: Codable {
    let id: String
    let brand: String
    let model: String
    let year: Int
    let price: String
    let imageURL: String
    let description: String
    let specifications: CarSpecifications
    let isActive: Bool
    let createdAt: String
    
    struct CarSpecifications: Codable {
        let engine: String
        let transmission: String
        let fuelType: String
        let bodyType: String
        let drivetrain: String
        let color: String
    }
    
    func toCar() -> Car {
        return Car(
            id: id,
            brand: brand,
            model: model,
            year: year,
            price: price,
            imageURL: imageURL,
            description: description,
            specifications: Car.CarSpecifications(
                engine: specifications.engine,
                transmission: specifications.transmission,
                fuelType: specifications.fuelType,
                bodyType: specifications.bodyType,
                drivetrain: specifications.drivetrain,
                color: specifications.color
            ),
            isActive: isActive,
            createdAt: ISO8601DateFormatter().date(from: createdAt) ?? Date()
        )
    }
}

struct APIProduct: Codable {
    let id: String
    let name: String
    let category: String
    let pointsCost: Int
    let imageURL: String
    let description: String
    let stockQuantity: Int
    let isActive: Bool
    let createdAt: String
    let deliveryOptions: [String]
    
    func toProduct() -> Product {
        let categoryEnum = Product.ProductCategory(rawValue: category) ?? .merchandise
        let deliveryEnum = deliveryOptions.compactMap { Product.DeliveryOption(rawValue: $0) }
        
        return Product(
            id: id,
            name: name,
            category: categoryEnum,
            pointsCost: pointsCost,
            imageURL: imageURL,
            description: description,
            stockQuantity: stockQuantity,
            isActive: isActive,
            createdAt: ISO8601DateFormatter().date(from: createdAt) ?? Date(),
            deliveryOptions: deliveryEnum,
            imageData: nil
        )
    }
}

struct APINewsArticle: Codable {
    let id: String
    let title: String
    let content: String
    let imageURL: String
    let isImportant: Bool
    let createdAt: String
    let publishedAt: String?
    let isPublished: Bool
    let authorId: String
    let tags: [String]
    
    func toNewsArticle() -> NewsArticle {
        let publishedDate = publishedAt.flatMap { ISO8601DateFormatter().date(from: $0) }
        
        return NewsArticle(
            id: id,
            title: title,
            content: content,
            imageURL: imageURL,
            isImportant: isImportant,
            createdAt: ISO8601DateFormatter().date(from: createdAt) ?? Date(),
            publishedAt: publishedDate,
            isPublished: isPublished,
            authorId: authorId,
            tags: tags,
            imageData: nil
        )
    }
}

struct APIQRScan: Codable {
    let valid: Bool
    let scan_id: String?
    let product_name: String?
    let product_category: String?
    let points_earned: Int?
    let description: String?
    let timestamp: String?
    let error: String?
    let used_at: String?
    
    func toQRScanResult() -> QRScanResult? {
        guard valid,
              let scanId = scan_id,
              let productName = product_name,
              let productCategory = product_category,
              let pointsEarned = points_earned,
              let timestamp = timestamp else {
            return nil
        }
        
        return QRScanResult(
            id: scanId,
            pointsEarned: pointsEarned,
            productName: productName,
            productCategory: productCategory,
            timestamp: ISO8601DateFormatter().date(from: timestamp) ?? Date(),
            qrCode: "", // Will be set separately
            location: nil
        )
    }
}

struct APIPointTransaction: Codable {
    let id: String
    let userId: String
    let type: String
    let amount: Int
    let description: String
    let timestamp: String
    let relatedId: String?
    
    func toPointTransaction() -> PointTransaction {
        let typeEnum = PointTransaction.TransactionType(rawValue: type) ?? .earned
        
        return PointTransaction(
            id: id,
            userId: userId,
            type: typeEnum,
            amount: amount,
            description: description,
            timestamp: ISO8601DateFormatter().date(from: timestamp) ?? Date(),
            relatedId: relatedId
        )
    }
}

// MARK: - Request Models
struct LoginRequest: Codable {
    let email: String
    let password: String
    let deviceInfo: String?
}

struct RegistrationRequest: Codable {
    let name: String
    let email: String
    let phone: String
    let password: String
    let userType: String
    let deviceInfo: String?
}

struct QRScanRequest: Codable {
    let qr_code: String
    let location: String?
}

struct CarCreateRequest: Codable {
    let brand: String
    let model: String
    let year: Int
    let price: String
    let description: String?
    let engine: String?
    let transmission: String?
    let fuelType: String?
    let bodyType: String?
    let drivetrain: String?
    let color: String?
}

// MARK: - Response Models
struct AuthResponse: Codable {
    let success: Bool
    let user: APIUser?
    let token: String?
    let error: String?
}

struct CarsResponse: Codable {
    let cars: [APICar]
    let pagination: Pagination?
}

struct ProductsResponse: Codable {
    let products: [APIProduct]
    let pagination: Pagination?
}

struct NewsResponse: Codable {
    let news: [APINewsArticle]
    let pagination: Pagination?
}

struct UserScansResponse: Codable {
    let user_id: String
    let total_scans: Int
    let total_points: Int
    let scans: [UserScan]
    let pagination: Pagination?
    
    struct UserScan: Codable {
        let id: String
        let qr_code: String
        let product_name: String
        let product_category: String
        let points_earned: Int
        let timestamp: String
        let location: String?
    }
}

struct TransactionsResponse: Codable {
    let transactions: [APIPointTransaction]
    let pagination: Pagination?
}

struct Pagination: Codable {
    let limit: Int
    let offset: Int
    let has_more: Bool?
}

struct FileUploadResponse: Codable {
    let success: Bool
    let file_url: String?
    let filename: String?
    let size: Int?
    let error: String?
}

// MARK: - Network Manager
@MainActor
class NetworkManager: ObservableObject {
    static let shared = NetworkManager()
    
    @Published var isConnected = true
    @Published var isLoading = false
    
    private let baseURL = "http://195.189.70.202:8080"
    private let apiKey = "nsp_mobile_app_api_key_2024"
    private var authToken: String?
    
    private init() {
        // Загружаем сохраненный токен
        authToken = UserDefaults.standard.string(forKey: "auth_token")
    }
    
    // MARK: - Private Methods
    
    private func createRequest(endpoint: String, method: String = "GET") -> URLRequest? {
        guard let url = URL(string: baseURL + endpoint) else {
            return nil
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        return request
    }
    
    private func performRequest<T: Codable>(_ request: URLRequest, responseType: T.Type) async throws -> T {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                throw NetworkError.networkUnavailable
            }
            
            if httpResponse.statusCode == 401 {
                // Токен истек, очищаем его
                authToken = nil
                UserDefaults.standard.removeObject(forKey: "auth_token")
                throw NetworkError.unauthorized
            }
            
            if httpResponse.statusCode >= 400 {
                // Пытаемся декодировать ошибку
                if let errorResponse = try? JSONDecoder().decode(APIResponse<String>.self, from: data) {
                    if let error = errorResponse.error {
                        switch error {
                        case _ where error.contains("already exists"):
                            throw NetworkError.userExists
                        case _ where error.contains("Invalid credentials"):
                            throw NetworkError.invalidCredentials
                        case _ where error.contains("already used"):
                            throw NetworkError.qrCodeAlreadyUsed
                        case _ where error.contains("not found"):
                            throw NetworkError.qrCodeNotFound
                        case _ where error.contains("Insufficient permissions"):
                            throw NetworkError.insufficientPermissions
                        default:
                            throw NetworkError.serverError(httpResponse.statusCode)
                        }
                    }
                }
                throw NetworkError.serverError(httpResponse.statusCode)
            }
            
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
            
        } catch let error as NetworkError {
            throw error
        } catch {
            throw NetworkError.networkUnavailable
        }
    }
    
    // MARK: - Authentication Methods
    
    func login(email: String, password: String) async throws -> APIUser {
        guard var request = createRequest(endpoint: "/api/v1/login", method: "POST") else {
            throw NetworkError.invalidURL
        }
        
        let loginRequest = LoginRequest(
            email: email,
            password: password,
            deviceInfo: UIDevice.current.model
        )
        
        request.httpBody = try JSONEncoder().encode(loginRequest)
        
        let response: AuthResponse = try await performRequest(request, responseType: AuthResponse.self)
        
        if let token = response.token, let user = response.user {
            authToken = token
            UserDefaults.standard.set(token, forKey: "auth_token")
            isConnected = true
            return user
        } else {
            throw NetworkError.invalidCredentials
        }
    }
    
    func register(name: String, email: String, phone: String, password: String, userType: User.UserType) async throws -> APIUser {
        guard var request = createRequest(endpoint: "/api/v1/register", method: "POST") else {
            throw NetworkError.invalidURL
        }
        
        let registrationRequest = RegistrationRequest(
            name: name,
            email: email,
            phone: phone,
            password: password,
            userType: userType.rawValue,
            deviceInfo: UIDevice.current.model
        )
        
        request.httpBody = try JSONEncoder().encode(registrationRequest)
        
        let response: AuthResponse = try await performRequest(request, responseType: AuthResponse.self)
        
        if let token = response.token, let user = response.user {
            authToken = token
            UserDefaults.standard.set(token, forKey: "auth_token")
            isConnected = true
            return user
        } else {
            throw NetworkError.serverError(500)
        }
    }
    
    func logout() {
        authToken = nil
        UserDefaults.standard.removeObject(forKey: "auth_token")
    }
    
    // MARK: - QR Code Methods
    
    func scanQRCode(qrCode: String, location: String? = nil) async throws -> APIQRScan {
        guard var request = createRequest(endpoint: "/api/v1/scan", method: "POST") else {
            throw NetworkError.invalidURL
        }
        
        let scanRequest = QRScanRequest(qr_code: qrCode, location: location)
        request.httpBody = try JSONEncoder().encode(scanRequest)
        
        return try await performRequest(request, responseType: APIQRScan.self)
    }
    
    func getUserScans(limit: Int = 50, offset: Int = 0) async throws -> UserScansResponse {
        guard let request = createRequest(endpoint: "/api/v1/user/scans?limit=\(limit)&offset=\(offset)") else {
            throw NetworkError.invalidURL
        }
        
        return try await performRequest(request, responseType: UserScansResponse.self)
    }
    
    // MARK: - Data Fetching Methods
    
    func getCars(limit: Int = 50, offset: Int = 0) async throws -> [APICar] {
        guard let request = createRequest(endpoint: "/api/v1/cars?limit=\(limit)&offset=\(offset)") else {
            throw NetworkError.invalidURL
        }
        
        let response: CarsResponse = try await performRequest(request, responseType: CarsResponse.self)
        return response.cars
    }
    
    func addCar(_ carData: CarCreateRequest) async throws -> String {
        guard var request = createRequest(endpoint: "/api/v1/cars", method: "POST") else {
            throw NetworkError.invalidURL
        }
        
        request.httpBody = try JSONEncoder().encode(carData)
        
        let response: APIResponse<[String: String]> = try await performRequest(request, responseType: APIResponse<[String: String]>.self)
        
        if let data = response.data, let carId = data["car_id"] {
            return carId
        } else {
            throw NetworkError.serverError(500)
        }
    }
    
    func getProducts(limit: Int = 50, offset: Int = 0) async throws -> [APIProduct] {
        guard let request = createRequest(endpoint: "/api/v1/products?limit=\(limit)&offset=\(offset)") else {
            throw NetworkError.invalidURL
        }
        
        let response: ProductsResponse = try await performRequest(request, responseType: ProductsResponse.self)
        return response.products
    }
    
    func getNews(limit: Int = 50, offset: Int = 0) async throws -> [APINewsArticle] {
        guard let request = createRequest(endpoint: "/api/v1/news?limit=\(limit)&offset=\(offset)") else {
            throw NetworkError.invalidURL
        }
        
        let response: NewsResponse = try await performRequest(request, responseType: NewsResponse.self)
        return response.news
    }
    
    func getUserTransactions(limit: Int = 50, offset: Int = 0) async throws -> [APIPointTransaction] {
        guard let request = createRequest(endpoint: "/api/v1/user/transactions?limit=\(limit)&offset=\(offset)") else {
            throw NetworkError.invalidURL
        }
        
        let response: TransactionsResponse = try await performRequest(request, responseType: TransactionsResponse.self)
        return response.transactions
    }
    
    // MARK: - File Upload
    
    func uploadFile(imageData: Data, filename: String) async throws -> String {
        guard let url = URL(string: baseURL + "/api/v1/upload") else {
            throw NetworkError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        // Создаем multipart/form-data
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        
        // Добавляем файл
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        
        request.httpBody = body
        
        let response: FileUploadResponse = try await performRequest(request, responseType: FileUploadResponse.self)
        
        if let fileUrl = response.file_url {
            return baseURL + fileUrl
        } else {
            throw NetworkError.serverError(500)
        }
    }
    
    // MARK: - Utility Methods
    
    func checkConnection() {
        Task {
            do {
                guard let request = createRequest(endpoint: "/health") else {
                    await MainActor.run { isConnected = false }
                    return
                }
                
                _ = try await performRequest(request, responseType: [String: String].self)
                await MainActor.run { isConnected = true }
            } catch {
                await MainActor.run { isConnected = false }
            }
        }
    }
    
    var connectionsStatusText: String {
        if isConnected {
            if let lastSync = UserDefaults.standard.object(forKey: "lastSyncDate") as? Date {
                return "Онлайн • Синхронизировано \(lastSync.timeAgoDisplay())"
            } else {
                return "Онлайн • Готов к синхронизации"
            }
        } else {
            return "Оффлайн"
        }
    }
    
    var isAuthenticated: Bool {
        return authToken != nil
    }
}