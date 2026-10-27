import SwiftUI
import WidgetKit

/// Complication timeline entry: the active micro-step only.
struct FocusEntry: TimelineEntry {
    let date: Date
    let microStep: String
    let minutes: Int
}

struct FocusProvider: TimelineProvider {
    func placeholder(in context: Context) -> FocusEntry {
        FocusEntry(date: Date(), microStep: "TYPE SUBJECT LINE", minutes: 12)
    }

    func getSnapshot(in context: Context, completion: @escaping (FocusEntry) -> Void) {
        completion(placeholder(in: context))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<FocusEntry>) -> Void) {
        // Companion sync phase: fetch /api/v1/focus and schedule the next
        // refresh at the active task's estimated boundary.
        let entry = placeholder(in: context)
        let next = Calendar.current.date(byAdding: .minute, value: 30, to: Date()) ?? Date()
        completion(Timeline(entries: [entry], policy: .after(next)))
    }
}

/// 16-character complication face: flat, monospaced, no chrome.
struct FocusComplicationView: View {
    let entry: FocusEntry

    /// Hard 16-char cap per the face budget (SPEC 2.1A).
    var cappedStep: String {
        String(entry.microStep.prefix(16))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(cappedStep)
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(WarmTokens.bone)
            Text("[\(entry.minutes)M]")
                .font(.system(size: 10, design: .monospaced))
                .foregroundColor(WarmTokens.amber)
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
