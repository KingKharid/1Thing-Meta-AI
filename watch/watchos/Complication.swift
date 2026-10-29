import SwiftUI
import WidgetKit

/// Complication timeline entry: the active micro-step only, plus the hidden
/// reserve *count*. Reserve titles never reach the face.
struct FocusEntry: TimelineEntry {
    enum State: Equatable {
        case focus
        case idle
        case offline
    }

    let date: Date
    let microStep: String
    let minutes: Int
    let reserveCount: Int
    let state: State

    static let placeholder = FocusEntry(
        date: Date(),
        microStep: "TYPE SUBJECT LINE",
        minutes: 12,
        reserveCount: 0,
        state: .focus
    )

    static let idle = FocusEntry(
        date: Date(),
        microStep: "NOTHING IN FOCUS",
        minutes: 0,
        reserveCount: 0,
        state: .idle
    )

    static let offline = FocusEntry(
        date: Date(),
        microStep: "ENGINE OFFLINE",
        minutes: 0,
        reserveCount: 0,
        state: .offline
    )

    /// WidgetKit has no shared app state, so the face reads the same focus
    /// endpoint directly. Identity matches every other surface.
    static func load() async -> FocusEntry {
        guard let url = URL(string: "/api/v1/focus", relativeTo: OneThingFaceAPI.baseURL) else {
            return .offline
        }
        var request = URLRequest(url: url, timeoutInterval: 6)
        request.setValue(OneThingFaceAPI.phoneNumber, forHTTPHeaderField: "X-Phone-Number")

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard
                let http = response as? HTTPURLResponse,
                http.statusCode == 200,
                let payload = try? JSONDecoder().decode(FocusPayload.self, from: data)
            else {
                return .offline
            }

            guard let task = payload.selectedTask else {
                return FocusEntry(
                    date: Date(),
                    microStep: "NOTHING IN FOCUS",
                    minutes: 0,
                    reserveCount: payload.queuedBacklogCount,
                    state: .idle
                )
            }

            let step = task.firstMicroStep
                .trimmingCharacters(in: .whitespacesAndNewlines)

            return FocusEntry(
                date: Date(),
                // An empty step says so on the face rather than rendering
                // a blank line where the one action should be.
                microStep: step.isEmpty ? "NO STEP YET" : step,
                minutes: task.estimatedMinutes,
                reserveCount: payload.queuedBacklogCount,
                state: .focus
            )
        } catch {
            return .offline
        }
    }

    private struct FocusPayload: Decodable {
        struct Task: Decodable {
            let firstMicroStep: String
            let estimatedMinutes: Int

            private enum CodingKeys: String, CodingKey {
                case firstMicroStep = "first_micro_step"
                case estimatedMinutes = "estimated_minutes"
            }
        }

        let selectedTask: Task?
        let queuedBacklogCount: Int

        private enum CodingKeys: String, CodingKey {
            case selectedTask = "selected_task"
            case queuedBacklogCount = "queued_backlog_count"
        }
    }
}

/// Complication targets cannot import the app target, so the two constants
/// live here as well. Keep them in sync with `OneThingAPI`.
enum OneThingFaceAPI {
    static let phoneNumber = "+15550007777"
    static let baseURL = URL(string: "http://127.0.0.1:8000")!
}

struct FocusProvider: TimelineProvider {
    func placeholder(in context: Context) -> FocusEntry {
        .placeholder
    }

    func getSnapshot(in context: Context, completion: @escaping (FocusEntry) -> Void) {
        completion(.placeholder)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<FocusEntry>) -> Void) {
        Task {
            let entry = await FocusEntry.load()
            // Refresh on the minute for live states, slowly when offline so
            // the face does not spin on a dead backend.
            let minutes = entry.state == .offline ? 30 : 15
            let next = Calendar.current.date(byAdding: .minute, value: minutes, to: Date()) ?? Date()
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }
}

/// 16-character complication face: flat, monospaced, no chrome.
struct FocusComplicationView: View {
    let entry: FocusEntry

    /// 16-char cap, cut on a word boundary so it never truncates mid-word.
    var cappedStep: String {
        let text = entry.microStep.uppercased()
        guard text.count > 16 else { return text }

        let limit = text.index(text.startIndex, offsetBy: 15)
        let prefix = text[text.startIndex..<limit]
        if let space = prefix.lastIndex(of: " "), space != prefix.startIndex {
            return String(prefix[..<space]) + "…"
        }
        return String(prefix) + "…"
    }

    var meta: String {
        switch entry.state {
        case .focus:
            return "[\(entry.minutes)M]"
        case .idle:
            return entry.reserveCount == 0 ? "RESERVE CLEAR" : "\(entry.reserveCount) IN RESERVE"
        case .offline:
            return "NO DATA"
        }
    }

    var accent: Color {
        switch entry.state {
        case .focus:
            return WarmTokens.amber
        case .idle:
            return WarmTokens.emerald
        case .offline:
            return WarmTokens.textGhost
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 4) {
                Rectangle()
                    .fill(accent)
                    .frame(width: 4, height: 4)

                Text(cappedStep)
                    .font(.system(size: 11, weight: .semibold, design: .monospaced))
                    .foregroundColor(entry.state == .offline ? WarmTokens.textFaint : WarmTokens.bone)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }

            Text(meta)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundColor(
                    entry.state == .focus ? WarmTokens.textFaint : accent
                )
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .widgetSurface()
    }
}

private extension View {
    /// watchOS 10 requires an explicit container background; earlier
    /// versions fall back to a flat fill.
    @ViewBuilder
    func widgetSurface() -> some View {
        if #available(watchOS 10.0, *) {
            self.containerBackground(for: .widget) {
                WarmTokens.erebus
            }
        } else {
            self.background(WarmTokens.erebus)
        }
    }
}

struct FocusComplication: Widget {
    let kind = "oneThingFocus"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FocusProvider()) { entry in
            FocusComplicationView(entry: entry)
        }
        .configurationDisplayName("1Thing Focus")
        .description("The single active micro-step.")
        .supportedFamilies([.accessoryRectangular])
    }
}
