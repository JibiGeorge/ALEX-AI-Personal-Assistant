//
//  AlexCompanionApp.swift
//  Alex Mobile Companion (iOS)
//
//  Secure LAN Companion Client for Alex AI Desktop Assistant.
//

import SwiftUI

@main
struct AlexCompanionApp: App {
    @StateObject private var gatewayClient = MobileGatewayClient()
    @StateObject private var audioManager = AudioStreamingManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(gatewayClient)
                .environmentObject(audioManager)
                .preferredColorScheme(.dark)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var gatewayClient: MobileGatewayClient
    @State private var selectedTab = 0

    var body: some View {
        Group {
            if gatewayClient.isAuthenticated {
                TabView(selection: $selectedTab) {
                    VoiceChatView()
                        .tabItem {
                            Label("Voice & Chat", systemImage: "waveform.circle.fill")
                        }
                        .tag(0)

                    MemoryBrowserView()
                        .tabItem {
                            Label("Memories", systemImage: "brain.head.profile")
                        }
                        .tag(1)
                }
                .accentColor(Color.cyan)
            } else {
                PairingView()
            }
        }
    }
}

