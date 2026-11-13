//
//  VoiceChatView.swift
//  Alex Mobile Companion (iOS)
//
//  Real-time voice streaming and conversation turn interface.
//

import SwiftUI

struct VoiceChatView: View {
    @EnvironmentObject var gatewayClient: MobileGatewayClient
    @EnvironmentObject var audioManager: AudioStreamingManager
    @State private var textInput: String = ""

    var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.07, blue: 0.11)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("ALEX LIVE")
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                            .foregroundColor(.cyan)
                        Text(gatewayClient.connectionStatus)
                            .font(.system(size: 10))
                            .foregroundColor(.green)
                    }
                    Spacer()
                }
                .padding()
                .background(Color.white.opacity(0.03))

                // Messages Feed
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(gatewayClient.messages) { msg in
                                HStack {
                                    if msg.isUser { Spacer() }
                                    VStack(alignment: msg.isUser ? .trailing : .leading, spacing: 4) {
                                        Text(msg.text)
                                            .font(.system(size: 14))
                                            .foregroundColor(.white)
                                            .padding(12)
                                            .background(msg.isUser ? Color.cyan.opacity(0.25) : Color.white.opacity(0.08))
                                            .cornerRadius(14)
                                    }
                                    if !msg.isUser { Spacer() }
                                }
                                .padding(.horizontal)
                                .id(msg.id)
                            }
                        }
                        .padding(.vertical)
                    }
                    .onChange(of: gatewayClient.messages.count) { _ in
                        if let last = gatewayClient.messages.last {
                            withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                        }
                    }
                }

                // Voice & Input Controls
                VStack(spacing: 12) {
                    // Push-to-Talk Mic Button
                    Button(action: {
                        if audioManager.isRecording {
                            audioManager.stopStreaming()
                        } else {
                            // audioManager.startStreaming(...)
                        }
                    }) {
                        ZStack {
                            Circle()
                                .fill(audioManager.isRecording ? Color.red : Color.cyan.opacity(0.15))
                                .frame(width: 64, height: 64)
                            Image(systemName: audioManager.isRecording ? "stop.fill" : "mic.fill")
                                .font(.system(size: 24))
                                .foregroundColor(audioManager.isRecording ? .white : .cyan)
                        }
                    }

                    // Text Input Bar
                    HStack {
                        TextField("Ask Alex...", text: $textInput)
                            .padding(10)
                            .background(Color.white.opacity(0.06))
                            .cornerRadius(10)
                            .foregroundColor(.white)

                        Button(action: {
                            guard !textInput.trimmingCharacters(in: .whitespaces).isEmpty else { return }
                            gatewayClient.sendTextMessage(textInput)
                            textInput = ""
                        }) {
                            Image(systemName: "arrow.up.circle.fill")
                                .font(.system(size: 28))
                                .foregroundColor(.cyan)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 8)
                }
                .background(Color.white.opacity(0.04))
            }
        }
    }
}

