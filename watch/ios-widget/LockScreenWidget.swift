import ActivityKit
import SwiftUI
import WidgetKit

// MARK: - Shared constants
//
// Mirror of watchOS OneThingAPI.swift. When the Xcode project grows a
// shared framework target, move these (plus the focus DTOs) into it so
// the app, watch app, and widgets stop duplicating them.

/// App Group shared by the iOS app and every widget. The app writes the
/// latest focus snapshot here on every state change; widgets read it
/// when the backend is unreachable from the extension sandbox.
private let appGroupID = "group.ai.onething.focus"

/// FastAPI base URL. Lock-screen widgets on a physical device need the
/// dev machine's LAN address (same Wi-Fi) instead of loopback.
private let apiBaseURL = URL(string: "http://127.0.0.1:8000")!

/// Testing identity shared across web, mobile, watch, and widgets.
private let defaultPhoneNumber = "+15550007777"

private enum SnapshotKeys {
    static let title = "focus.title"
    static let step = "focus.step"
    static let minutes = "focus.minutes"
    static let updatedAt = "focus.updatedAt"
}

// MARK: - Focus state

struct FocusWidgetState {
    let title: String
    let step: String
    let minutes: Int
    let live: Bool

    static let empty = FocusWidgetState(
        title: "NOTHING IN FOCUS",
        step: "DUMP TO BEGIN",
        minutes: 0,
        live: false
    )
}

private struct FocusResponse: Decodable {
    struct SelectedTask: Decodable {
        let title: String
        let firstMicroStep: String
        let estimatedMinutes: Int

        private enum CodingKeys: String, CodingKey {
            case title
            case firstMicroStep = "first_micro_step"
            case estimatedMinutes = "estimated_minutes"
        }
    }

    let selectedTask: SelectedTask?

    private enum CodingKeys: String, CodingKey {
        case selectedTask = "selected_task"
    }
}

private enum FocusStore {
    static var sharedDefaults: UserDefaults? {
        UserDefaults(suiteName: appGroupID)
    }

    /// Direct backend read. Throws on any transport, HTTP, or decode
    /// failure so the caller can fall back to the App Group snapshot.
    static func fetchRemote() async throws -> FocusWidgetState {
        var request = URLRequest(
            url: apiBaseURL.appendingPathComponent("/api/v1/focus"),
            cachePolicy: .reloadIgnoringLocalCacheData,
            timeoutInterval: 8
        )
        request.setValue(defaultPhoneNumber, forHTTPHeaderField: "X-Phone-Number")
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        let decoded = try JSONDecoder().decode(FocusResponse.self, from: data)
        guard let selected = decoded.selectedTask else {
            return FocusWidgetState(title: "NOTHING IN FOCUS", step: "DUMP TO BEGIN", minutes: 0, live: true)
        }
        let state = FocusWidgetState(
            title: selected.title,
            // An empty step must not render as a blank hero line.
            step: selected.firstMicroStep
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .isEmpty
                ? "NO STEP YET"
                : selected.firstMicroStep,
            minutes: selected.estimatedMinutes,
            live: true
        )
        persist(state)
        return state
    }

    static func persist(_ state: FocusWidgetState) {
        let defaults = sharedDefaults
        defaults?.set(state.title, forKey: SnapshotKeys.title)
        defaults?.set(state.step, forKey: SnapshotKeys.step)
        defaults?.set(state.minutes, forKey: SnapshotKeys.minutes)
        defaults?.set(Date().timeIntervalSince1970, forKey: SnapshotKeys.updatedAt)
    }

    static func loadSnapshot() -> FocusWidgetState {
        guard
            let defaults = sharedDefaults,
            let title = defaults.string(forKey: SnapshotKeys.title),
            let step = defaults.string(forKey: SnapshotKeys.step)
        else {
            return .empty
        }
        return FocusWidgetState(
            title: title,
            step: step,
            minutes: defaults.integer(forKey: SnapshotKeys.minutes),
            live: false
        )
    }

    /// Remote first, App Group snapshot second, honest empty state last.
    static func current() async -> FocusWidgetState {
        if let remote = try? await fetchRemote() {
            return remote
        }
        return loadSnapshot()
    }
}

// MARK: - Widget timeline

struct FocusWidgetEntry: TimelineEntry {
    let date: Date
    let state: FocusWidgetState
}

struct FocusWidgetProvider: TimelineProvider {
    func placeholder(in context: Context) -> FocusWidgetEntry {
        FocusWidgetEntry(date: Date(), state: .empty)
    }

    func getSnapshot(in context: Context, completion: @escaping (FocusWidgetEntry) -> Void) {
        Task {
            completion(FocusWidgetEntry(date: Date(), state: await FocusStore.current()))
        }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<FocusWidgetEntry>) -> Void) {
        Task {
            let entry = FocusWidgetEntry(date: Date(), state: await FocusStore.current())
            let next = Calendar.current.date(byAdding: .minute, value: 15, to: Date()) ?? Date()
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }
}

// MARK: - Lock-screen views (16-char discipline on circular)

private let amber = Color(red: 0xF5 / 255, green: 0x9E / 255, blue: 0x0B / 255)
private let bone = Color(red: 0xF9 / 255, green: 0xF8 / 255, blue: 0xF6 / 255)

struct FocusRectangularView: View {
    let state: FocusWidgetState

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            // Title as kicker; the physical step is the headline.
            Text(state.title)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundColor(bone.opacity(0.58))
                .lineLimit(1)

            HStack(alignment: .top, spacing: 5) {
                Rectangle()
                    .fill(amber)
                    .frame(width: 3, height: 3)
                    .padding(.top, 5)

                Text(state.step)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(bone)
                    .lineLimit(2)
                    .minimumScaleFactor(0.8)
            }

            Text(state.live ? "[\(state.minutes)M]" : "[\(state.minutes)M] HELD")
                .font(.system(size: 9, design: .monospaced))
                .foregroundColor(bone.opacity(0.5))
        }
        .widgetURL(URL(string: "onething://focus"))
    }
}

struct FocusCircularView: View {
    let state: FocusWidgetState

    /// 16-char cap, cut on a word boundary so it never truncates mid-word.
    var cappedStep: String {
        let text = state.step.uppercased()
        guard text.count > 16 else { return text }

        let limit = text.index(text.startIndex, offsetBy: 15)
        let prefix = text[text.startIndex..<limit]
        if let space = prefix.lastIndex(of: " "), space != prefix.startIndex {
            return String(prefix[..<space]) + "…"
        }
        return String(prefix) + "…"
    }

    var body: some View {
        VStack(spacing: 1) {
            Text(cappedStep)
                .font(.system(size: 9, weight: .semibold, design: .monospaced))
                .foregroundColor(bone)
                .lineLimit(2)
                .multilineTextAlignment(.center)
            Text("[\(state.minutes)M]")
                .font(.system(size: 9, design: .monospaced))
                .foregroundColor(bone.opacity(0.5))
        }
        .widgetURL(URL(string: "onething://focus"))
    }
}

struct FocusLockScreenWidget: Widget {
    let kind = "ai.onething.focus.lockscreen"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FocusWidgetProvider()) { entry in
            FocusWidgetView(entry: entry)
        }
        .configurationDisplayName("1Thing Focus")
        .description("The single active micro-step on the lock screen.")
        .supportedFamilies([.accessoryRectangular, .accessoryCircular])
    }
}

struct FocusWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: FocusWidgetEntry

    @ViewBuilder
    var body: some View {
        switch family {
        case .accessoryCircular:
            FocusCircularView(state: entry.state)
        default:
            FocusRectangularView(state: entry.state)
        }
    }
}

// MARK: - Live Activity (lock-screen banner + Dynamic Island)

struct FocusActivityAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        let step: String
        let minutes: Int
    }

    let title: String
}

struct FocusLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: FocusActivityAttributes.self) { context in
            // Lock-screen banner: step first, title as kicker.
            VStack(alignment: .leading, spacing: 3) {
                Text(context.attributes.title)
                    .font(.system(size: 9, weight: .medium, design: .monospaced))
                    .foregroundColor(bone.opacity(0.58))
                    .lineLimit(1)
                Text(context.state.step)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(bone)
                    .lineLimit(2)
                Text("[\(context.state.minutes)M]")
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(bone.opacity(0.5))
            }
            .padding()
            .widgetURL(URL(string: "onething://focus"))
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Text("[\(context.state.minutes)M]")
                        .font(.caption.monospaced())
                        .foregroundColor(bone.opacity(0.5))
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(context.attributes.title)
                        .font(.caption2.monospaced())
                        .foregroundColor(bone.opacity(0.58))
                        .lineLimit(1)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text(context.state.step)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(bone)
                        .lineLimit(1)
                }
            } compactLeading: {
                Rectangle()
                    .fill(amber)
                    .frame(width: 4, height: 4)
            } compactTrailing: {
                Text("\(context.state.minutes)M")
                    .font(.caption2.monospaced())
                    .foregroundColor(bone)
            } minimal: {
                Rectangle()
                    .fill(amber)
                    .frame(width: 5, height: 5)
            }
        }
    }
}

// MARK: - Bundle

@main
struct OneThingWidgets: WidgetBundle {
    var body: some Widget {
        FocusLockScreenWidget()
        FocusLiveActivity()
    }
}
