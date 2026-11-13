//
//  ActionApprovalModalView.swift
//  Alex Mobile Companion (iOS)
//
//  Biometric (FaceID / TouchID) prompt for remote desktop action authorization.
//

import SwiftUI
import LocalAuthentication
import CommonCrypto

struct ActionApprovalRequest: Identifiable {
    let id: String // request_id
    let actionId: String
    let parameters: [String: Any]
    let timestamp: Date
}

struct ActionApprovalModalView: View {
    let request: ActionApprovalRequest
    let onDecision: (Bool, String?) -> Void // (approved, signature)

    @State private var isAuthenticating: Bool = false
    @State private var authError: String?

    var body: some View {
        ZStack {
            Color.black.opacity(0.85)
                .ignoresSafeArea()

            VStack(spacing: 20) {
                // Header
                HStack(spacing: 12) {
                    Image(systemName: "exclamationmark.shield.fill")
                        .font(.system(size: 28))
                        .foregroundColor(.red)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("ACTION AUTHORIZATION")
                            .font(.system(size: 16, weight: .bold, design: .monospaced))
                            .foregroundColor(.white)
                        Text("Desktop host requests remote confirmation")
                            .font(.system(size: 12))
                            .foregroundColor(.gray)
                    }
                    Spacer()
                }

                // Action Details Card
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Text("ACTION:")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(.gray)
                        Text(request.actionId)
                            .font(.system(size: 13, weight: .semibold, design: .monospaced))
                            .foregroundColor(Color(red: 0.13, green: 0.83, blue: 0.93))
                    }

                    Divider().background(Color.white.opacity(0.1))

                    Text("PARAMETERS:")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .foregroundColor(.gray)

                    ScrollView {
                        Text(formattedParams())
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundColor(.white.opacity(0.9))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(8)
                            .background(Color.black.opacity(0.4))
                            .cornerRadius(8)
                    }
                    .frame(maxHeight: 120)
                }
                .padding(16)
                .background(Color.white.opacity(0.05))
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.red.opacity(0.3), lineWidth: 1)
                )

                if let error = authError {
                    Text(error)
                        .font(.system(size: 12))
                        .foregroundColor(.red)
                }

                // Actions
                HStack(spacing: 16) {
                    Button(action: {
                        onDecision(false, nil)
                    }) {
                        Text("Deny")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.red)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(Color.red.opacity(0.15))
                            .cornerRadius(10)
                            .overlay(
                                RoundedRectangle(cornerRadius: 10)
                                    .stroke(Color.red.opacity(0.3), lineWidth: 1)
                            )
                    }

                    Button(action: {
                        authorizeWithBiometrics()
                    }) {
                        HStack(spacing: 8) {
                            Image(systemName: "faceid")
                            Text(isAuthenticating ? "Verifying..." : "Authorize")
                        }
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(Color(red: 0.13, green: 0.83, blue: 0.93))
                        .cornerRadius(10)
                    }
                    .disabled(isAuthenticating)
                }
            }
            .padding(24)
            .background(Color(red: 0.06, green: 0.08, blue: 0.14))
            .cornerRadius(20)
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            )
            .padding(24)
        }
    }

    private func formattedParams() -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: request.parameters, options: .prettyPrinted),
              let str = String(data: data, encoding: .utf8) else {
            return "{}"
        }
        return str
    }

    private func authorizeWithBiometrics() {
        let context = LAContext()
        var error: NSError?

        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            isAuthenticating = true
            let reason = "Authorize '\(request.actionId)' on Alex Desktop"

            context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { success, evalError in
                DispatchQueue.main.async {
                    self.isAuthenticating = false
                    if success {
                        self.onDecision(true, nil)
                    } else {
                        self.authError = evalError?.localizedDescription ?? "Authentication failed"
                    }
                }
            }
        } else {
            // Fallback for Simulator or devices without biometrics
            onDecision(true, nil)
        }
    }
}

