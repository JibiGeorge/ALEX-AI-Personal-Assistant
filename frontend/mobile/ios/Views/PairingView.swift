//
//  PairingView.swift
//  Alex Mobile Companion (iOS)
//
//  Pairing screen with host IP entry and 8-character pairing code input.
//

import SwiftUI

struct PairingView: View {
    @EnvironmentObject var gatewayClient: MobileGatewayClient
    @State private var hostInput: String = ""
    @State private var codeInput: String = ""
    @State private var isConnecting: Bool = false

    var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.07, blue: 0.11)
                .ignoresSafeArea()

            VStack(spacing: 24) {
                Spacer()

                // Logo
                VStack(spacing: 6) {
                    Text("ALEX")
                        .font(.system(size: 32, weight: .bold, design: .monospaced))
                        .foregroundColor(.cyan)
                    Text("MOBILE COMPANION")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.gray)
                        .tracking(3)
                }

                // Instructions Card
                VStack(spacing: 16) {
                    Text("Scan the QR code displayed in Alex Desktop Settings or enter the 8-character pairing code below.")
                        .font(.system(size: 13))
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    // Host IP Field
                    VStack(alignment: .leading, spacing: 6) {
                        Text("DESKTOP HOST IP")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.gray)
                        TextField("e.g. 192.168.1.100", text: $hostInput)
                            .keyboardType(.numbersAndPunctuation)
                            .padding(12)
                            .background(Color.white.opacity(0.06))
                            .cornerRadius(10)
                            .foregroundColor(.white)
                    }

                    // Pairing Code Field
                    VStack(alignment: .leading, spacing: 6) {
                        Text("8-CHARACTER PAIRING CODE")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.gray)
                        TextField("e.g. ABC3X9TY", text: $codeInput)
                            .autocapitalization(.allCharacters)
                            .disableAutocorrection(true)
                            .font(.system(.title3, design: .monospaced))
                            .multilineTextAlignment(.center)
                            .padding(12)
                            .background(Color.white.opacity(0.06))
                            .cornerRadius(10)
                            .foregroundColor(.cyan)
                    }

                    if let err = gatewayClient.errorMessage {
                        Text(err)
                            .font(.system(size: 12))
                            .foregroundColor(.red)
                    }

                    Button(action: {
                        Task {
                            isConnecting = true
                            _ = await gatewayClient.pair(host: hostInput.isEmpty ? "127.0.0.1" : hostInput, code: codeInput)
                            isConnecting = false
                        }
                    }) {
                        HStack {
                            if isConnecting {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .black))
                            } else {
                                Text("Connect to Alex")
                                    .fontWeight(.bold)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.cyan)
                        .foregroundColor(.black)
                        .cornerRadius(12)
                    }
                    .disabled(codeInput.trimmingCharacters(in: .whitespaces).count < 6 || isConnecting)
                }
                .padding(24)
                .background(Color.white.opacity(0.04))
                .cornerRadius(20)
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(Color.white.opacity(0.1), lineWidth: 1)
                )
                .padding(.horizontal, 24)

                Spacer()
            }
        }
    }
}

