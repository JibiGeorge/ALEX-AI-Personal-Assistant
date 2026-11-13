//
//  AudioStreamingManager.swift
//  Alex Mobile Companion (iOS)
//
//  Records 16kHz 16-bit mono PCM audio using AVAudioEngine and plays back synthesized responses.
//

import Foundation
import AVFoundation

class AudioStreamingManager: ObservableObject {
    @Published var isRecording: Bool = false
    @Published var isPlaying: Bool = false
    @Published var audioLevel: Float = 0.0

    private let audioEngine = AVAudioEngine()
    private var audioPlayer: AVAudioPlayer?
    private var webSocketTask: URLSessionWebSocketTask?

    func startStreaming(to webSocket: URLSessionWebSocketTask?) {
        guard !isRecording else { return }
        self.webSocketTask = webSocket

        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession.setActive(true)
        } catch {
            print("Failed to configure audio session: \(error)")
            return
        }

        let inputNode = audioEngine.inputNode
        let nativeFormat = inputNode.outputFormat(forBus: 0)

        // Target: 16,000 Hz, 1 Channel, 16-bit Linear PCM
        guard let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: true) else {
            return
        }

        guard let converter = AVAudioConverter(from: nativeFormat, to: targetFormat) else {
            print("Failed to initialize audio converter")
            return
        }

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: nativeFormat) { [weak self] (buffer, _) in
            guard let self = self else { return }

            let frameCapacity = AVAudioFrameCount(targetFormat.sampleRate * Double(buffer.frameLength) / nativeFormat.sampleRate)
            guard let convertedBuffer = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: frameCapacity) else { return }

            var error: NSError?
            converter.convert(to: convertedBuffer, error: &error) { _, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }

            if error == nil && convertedBuffer.frameLength > 0 {
                let channelData = convertedBuffer.int16ChannelData?[0]
                let byteLength = Int(convertedBuffer.frameLength) * MemoryLayout<Int16>.size
                if let dataPtr = channelData {
                    let pcmData = Data(bytes: dataPtr, count: byteLength)
                    self.webSocketTask?.send(.data(pcmData)) { _ in }
                }
            }
        }

        do {
            try audioEngine.start()
            DispatchQueue.main.async { self.isRecording = true }
        } catch {
            print("Failed to start audio engine: \(error)")
        }
    }

    func stopStreaming() {
        guard isRecording else { return }
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        DispatchQueue.main.async { self.isRecording = false }
    }

    func playAudioData(_ data: Data) {
        do {
            audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer?.play()
            DispatchQueue.main.async { self.isPlaying = true }
        } catch {
            print("Failed to play audio: \(error)")
        }
    }
}

