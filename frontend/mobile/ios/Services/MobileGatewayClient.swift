//
//  MobileGatewayClient.swift
//  Alex Mobile Companion (iOS)
//
//  Manages LAN pairing, PBKDF2 key derivation, AES-256-GCM encryption,
//  and WebSocket streaming to the Alex Desktop host.
//

import Foundation
import CryptoKit
import Combine

class MobileGatewayClient: ObservableObject {
    @Published var host: String = ""
    @Published var port: Int = 8766
    @Published var isAuthenticated: Bool = false
    @Published var connectionStatus: String = "Disconnected"
    @Published var errorMessage: String?

    @Published var messages: [ChatMessage] = []
    @Published var pendingApproval: ActionApprovalRequest?

    private var sessionToken: String?
    private var symmetricKey: SymmetricKey?
    private var webSocketTask: URLSessionWebSocketTask?
    private let urlSession = URLSession(configuration: .default)

    struct ChatMessage: Identifiable {
        let id = UUID()
        let sender: String
        let text: String
        let timestamp: Date
        let isUser: Bool
    }

    func pair(host: String, port: Int = 8766, code: String) async -> Bool {
        self.host = host
        self.port = port
        let cleanCode = code.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()

        guard let url = URL(string: "http://\(host):\(port)/api/v1/mobile/pair") else {
            DispatchQueue.main.async { self.errorMessage = "Invalid gateway URL" }
            return false
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "pairing_code": cleanCode,
            "device_name": UIDevice.current.name,
            "device_platform": "iOS"
        ]

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            let (data, response) = try await urlSession.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                DispatchQueue.main.async { self.errorMessage = "Pairing failed. Check code or network." }
                return false
            }

            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let token = json["session_token"] as? String,
                  let saltB64 = json["salt"] as? String,
                  let salt = Data(base64Encoded: saltB64) else {
                DispatchQueue.main.async { self.errorMessage = "Invalid handshake payload" }
                return false
            }

            // Derive 256-bit AES key using PBKDF2 with SHA-256
            let derivedKey = try deriveKey(code: cleanCode, salt: salt, iterations: 200_000)
            self.symmetricKey = derivedKey
            self.sessionToken = token

            DispatchQueue.main.async {
                self.isAuthenticated = true
                self.connectionStatus = "Paired"
                self.errorMessage = nil
            }

            connectWebSocket()
            return true
        } catch {
            DispatchQueue.main.async { self.errorMessage = error.localizedDescription }
            return false
        }
    }

    private func deriveKey(code: String, salt: Data, iterations: Int) throws -> SymmetricKey {
        // Standard PBKDF2-HMAC-SHA256 key derivation matching server
        let passwordData = Data(code.utf8)
        var derivedKeyData = Data(count: 32)
        let result = derivedKeyData.withUnsafeMutableBytes { derivedKeyBytes in
            salt.withUnsafeBytes { saltBytes in
                passwordData.withUnsafeBytes { passwordBytes in
                    CCKeyDerivationPBKDF(
                        CCPBKDFAlgorithm(kCCPBKDF2),
                        passwordBytes.baseAddress?.assumingMemoryBound(to: Int8.self),
                        passwordData.count,
                        saltBytes.baseAddress?.assumingMemoryBound(to: UInt8.self),
                        salt.count,
                        CCPseudoRandomAlgorithm(kCCPRFHmacAlgSHA256),
                        UInt32(iterations),
                        derivedKeyBytes.baseAddress?.assumingMemoryBound(to: UInt8.self),
                        32
                    )
                }
            }
        }
        guard result == 0 else {
            throw NSError(domain: "CryptoError", code: Int(result), userInfo: nil)
        }
        return SymmetricKey(data: derivedKeyData)
    }

    func connectWebSocket() {
        guard let token = sessionToken else { return }
        guard let wsUrl = URL(string: "ws://\(host):\(port)/api/v1/mobile/ws?token=\(token)") else { return }

        let task = urlSession.webSocketTask(with: wsUrl)
        self.webSocketTask = task
        task.resume()

        DispatchQueue.main.async { self.connectionStatus = "Connected" }
        receiveWebSocketMessage()
    }

    private func receiveWebSocketMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.handleIncomingEncryptedString(text)
                case .data(let data):
                    self.handleIncomingData(data)
                @unknown default:
                    break
                }
                self.receiveWebSocketMessage()
            case .failure(let error):
                DispatchQueue.main.async {
                    self.connectionStatus = "Disconnected (\(error.localizedDescription))"
                }
            }
        }
    }

    private func handleIncomingEncryptedString(_ text: String) {
        guard let key = symmetricKey else { return }
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: String],
              let ivB64 = json["iv"],
              let ctB64 = json["ciphertext"],
              let ivData = Data(base64Encoded: ivB64),
              let ctData = Data(base64Encoded: ctB64) else { return }

        do {
            let sealedBox = try AES.GCM.SealedBox(nonce: AES.GCM.Nonce(data: ivData), ciphertext: ctData.dropLast(16), tag: ctData.suffix(16))
            let decryptedData = try AES.GCM.open(sealedBox, using: key)
            if let obj = try? JSONSerialization.jsonObject(with: decryptedData) as? [String: Any] {
                DispatchQueue.main.async {
                    if let text = obj["text"] as? String {
                        self.messages.append(ChatMessage(sender: "Alex", text: text, timestamp: Date(), isUser: false))
                    }
                    if let type = obj["type"] as? String {
                        if type == "action_approval_required",
                           let reqId = obj["request_id"] as? String,
                           let act = obj["action"] as? String {
                            let params = obj["params"] as? [String: Any] ?? [:]
                            self.pendingApproval = ActionApprovalRequest(id: reqId, actionId: act, parameters: params, timestamp: Date())
                        } else if type == "action_approval_ack" {
                            self.pendingApproval = nil
                        }
                    }
                }
            }
        } catch {
            print("Decryption failed: \(error)")
        }
    }

    private func handleIncomingData(_ data: Data) {
        // Direct audio or binary data from server
    }

    func sendTextMessage(_ text: String) {
        guard let token = sessionToken, let key = symmetricKey else { return }

        let payload: [String: Any] = ["type": "turn", "content": text]
        guard let rawData = try? JSONSerialization.data(withJSONObject: payload) else { return }

        do {
            let nonce = AES.GCM.Nonce()
            let sealedBox = try AES.GCM.seal(rawData, using: key, nonce: nonce)
            let combinedCt = sealedBox.ciphertext + sealedBox.tag

            let frame: [String: String] = [
                "iv": Data(nonce).base64EncodedString(),
                "ciphertext": combinedCt.base64EncodedString()
            ]

            guard let frameData = try? JSONSerialization.data(withJSONObject: frame),
                  let frameStr = String(data: frameData, encoding: .utf8) else { return }

            webSocketTask?.send(.string(frameStr)) { _ in }

            DispatchQueue.main.async {
                self.messages.append(ChatMessage(sender: "You", text: text, timestamp: Date(), isUser: true))
            }
        } catch {
            print("Encryption failed: \(error)")
        }
    }

    func sendApprovalDecision(requestId: String, approved: Bool) {
        guard let token = sessionToken, let key = symmetricKey else { return }

        let payload: [String: Any] = [
            "type": "action_approval",
            "request_id": requestId,
            "approved": approved
        ]
        guard let rawData = try? JSONSerialization.data(withJSONObject: payload) else { return }

        do {
            let nonce = AES.GCM.Nonce()
            let sealedBox = try AES.GCM.seal(rawData, using: key, nonce: nonce)
            let combinedCt = sealedBox.ciphertext + sealedBox.tag

            let frame: [String: String] = [
                "iv": Data(nonce).base64EncodedString(),
                "ciphertext": combinedCt.base64EncodedString()
            ]

            guard let frameData = try? JSONSerialization.data(withJSONObject: frame),
                  let frameStr = String(data: frameData, encoding: .utf8) else { return }

            webSocketTask?.send(.string(frameStr)) { _ in }
            DispatchQueue.main.async {
                self.pendingApproval = nil
            }
        } catch {
            print("Encryption failed: \(error)")
        }
    }
}

