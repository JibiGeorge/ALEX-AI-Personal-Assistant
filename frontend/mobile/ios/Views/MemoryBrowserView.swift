//
//  MemoryBrowserView.swift
//  Alex Mobile Companion (iOS)
//
//  Search and view memories synced from the Alex desktop host.
//

import SwiftUI

struct MemoryBrowserView: View {
    @EnvironmentObject var gatewayClient: MobileGatewayClient
    @State private var searchQuery: String = ""
    @State private var memories: [MemoryItem] = []

    struct MemoryItem: Identifiable {
        let id = UUID()
        let category: String
        let content: String
        let updatedAt: String
    }

    var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.07, blue: 0.11)
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: 16) {
                Text("PERSISTENT MEMORY")
                    .font(.system(size: 14, weight: .bold, design: .monospaced))
                    .foregroundColor(.cyan)
                    .padding(.horizontal)
                    .padding(.top)

                TextField("Search memories...", text: $searchQuery)
                    .padding(10)
                    .background(Color.white.opacity(0.06))
                    .cornerRadius(10)
                    .foregroundColor(.white)
                    .padding(.horizontal)

                ScrollView {
                    LazyVStack(spacing: 10) {
                        ForEach(filteredMemories) { item in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text(item.category.uppercased())
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(.cyan)
                                    Spacer()
                                    Text(item.updatedAt)
                                        .font(.system(size: 9))
                                        .foregroundColor(.gray)
                                }
                                Text(item.content)
                                    .font(.system(size: 13))
                                    .foregroundColor(.white)
                            }
                            .padding()
                            .background(Color.white.opacity(0.04))
                            .cornerRadius(12)
                            .padding(.horizontal)
                        }
                    }
                }
            }
        }
        .onAppear {
            loadMemories()
        }
    }

    private var filteredMemories: [MemoryItem] {
        if searchQuery.isEmpty { return memories }
        return memories.filter { $0.content.localizedCaseInsensitiveContains(searchQuery) }
    }

    private func loadMemories() {
        // Query /api/v1/mobile/memories
    }
}

