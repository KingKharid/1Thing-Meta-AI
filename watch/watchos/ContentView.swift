import SwiftUI

/// Warm Industrial Minimalism tokens for watchOS.
enum WarmTokens {
    static let erebus = Color(red: 0x0C / 255, green: 0x0D / 255, blue: 0x0E / 255)
    static let carbon = Color(red: 0x16 / 255, green: 0x18 / 255, blue: 0x1A / 255)
    static let bone = Color(red: 0xF9 / 255, green: 0xF8 / 255, blue: 0xF6 / 255)
    static let amber = Color(red: 0xF5 / 255, green: 0x9E / 255, blue: 0x0B / 255)
    static let emerald = Color(red: 0x10 / 255, green: 0xB9 / 255, blue: 0x81 / 255)

    /// 1px hairline. Flat surfaces, never heavy shadows.
    static let hairline = Color.white.opacity(0.12)
    static let textDim = Color.white.opacity(0.76)
    static let textFaint = Color.white.opacity(0.58)
    static let textGhost = Color.white.opacity(0.5)

    static let mono = Font.system(size: 10, design: .monospaced)
}

/// The single task payload. Sample data exists only for Xcode previews.
struct WatchFocus: Decodable {
    let id: Int
    let title: String
    let firstMicroStep: String
    let estimatedMinutes: Int

    static let preview = WatchFocus(
        id: -1,
        title: "DRAFT EMAIL TO ALICE",
        firstMicroStep: "TYPE SUBJECT LINE",
        estimatedMinutes: 12
    )
}

/// The wrist is the reference surface: the micro-step is the headline, the
/// task title is a mono kicker, and DONE is a machined bone key.
struct ContentView: View {
    @State private var focus: WatchFocus?
    @State private var reserveCount = 0
    @State private var live = false
    @State private var busy = false

    var body: some View {
        ZStack {
            WarmTokens.erebus.ignoresSafeArea()

            VStack(alignment: .leading, spacing: 0) {
                if let task = focus {
                    taskView(task)
                } else if live {
                    idleView
                } else {
                    offlineView
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 6)
        }
        .task { await reload() }
    }

    // MARK: - States

    @ViewBuilder
    private func taskView(_ task: WatchFocus) -> some View {
        // Title as kicker: one line, truncated, never the headline.
        HStack(spacing: 6) {
            Text(task.title)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .tracking(1.0)
                .foregroundColor(WarmTokens.textFaint)
                .lineLimit(1)
                .truncationMode(.tail)

            Spacer(minLength: 4)

            Text("[\(task.estimatedMinutes)M]")
                .font(.system(size: 9, design: .monospaced))
                .foregroundColor(WarmTokens.textFaint)
                .padding(.horizontal, 4)
                .padding(.vertical, 1)
                .overlay(Rectangle().stroke(WarmTokens.hairline, lineWidth: 1))
        }
        .padding(.bottom, 10)

        // The one amber mark on the wrist — only when there is a step for it
        // to mark. An empty step must not borrow one.
        let hasStep = !task.firstMicroStep
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .isEmpty

        HStack(spacing: 5) {
            if hasStep {
                Rectangle()
                    .fill(WarmTokens.amber)
                    .frame(width: 5, height: 5)
            }

            Text(hasStep ? "NEXT STEP" : "STEP MISSING")
                .font(.system(size: 9, weight: .semibold, design: .monospaced))
                .tracking(1.6)
                .foregroundColor(hasStep ? WarmTokens.amber : WarmTokens.textFaint)
        }
        .padding(.bottom, 5)

        Text(hasStep ? task.firstMicroStep : "NO STEP YET")
            .font(.system(size: 16, weight: .semibold))
            .foregroundColor(hasStep ? WarmTokens.bone : WarmTokens.textDim)
            .lineLimit(3)
            .minimumScaleFactor(0.75)
            .fixedSize(horizontal: false, vertical: true)

        Spacer(minLength: 6)

        reserveLine
            .padding(.bottom, 8)

        HStack(spacing: 6) {
            Button {
                Task { await complete() }
            } label: {
                Text(busy ? "…" : "DONE")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .tracking(1.2)
                    .foregroundColor(WarmTokens.erebus)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 7)
                    .background(WarmTokens.bone)
            }
            .buttonStyle(.plain)
            .disabled(busy)
            .accessibilityLabel("Mark done")

            Button {
                Task { await skip() }
            } label: {
                Text("SKIP")
                    .font(.system(size: 11, weight: .medium, design: .monospaced))
                    .tracking(1.2)
                    .foregroundColor(WarmTokens.textFaint)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 7)
                    .overlay(Rectangle().stroke(WarmTokens.hairline, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .disabled(busy)
            .accessibilityLabel("Skip task")
        }
    }

    private var idleView: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("STANDBY")
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .tracking(1.4)
                .foregroundColor(WarmTokens.textFaint)

            Spacer(minLength: 8)

            Text("NOTHING\nIN FOCUS")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(WarmTokens.bone)
                .fixedSize(horizontal: false, vertical: true)

            Spacer(minLength: 6)

            Text("SEND ANYTHING TO BEGIN")
                .font(.system(size: 9, design: .monospaced))
                .tracking(0.8)
                .foregroundColor(WarmTokens.textGhost)

            Spacer(minLength: 10)

            reserveLine
        }
    }

    private var offlineView: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("ENGINE OFFLINE")
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .tracking(1.4)
                .foregroundColor(WarmTokens.textFaint)

            Spacer(minLength: 8)

            Text("NO DATA")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(WarmTokens.bone)

            Spacer(minLength: 6)

            Text("OPEN THE APP TO RETRY")
                .font(.system(size: 9, design: .monospaced))
                .tracking(0.8)
                .foregroundColor(WarmTokens.textGhost)

            Spacer(minLength: 10)
        }
    }

    /// One reserve primitive: glyph + count. Never a title.
    private var reserveLine: some View {
        HStack(spacing: 5) {
            Rectangle()
                .stroke(
                    reserveCount == 0 ? WarmTokens.emerald.opacity(0.55) : WarmTokens.hairline,
                    lineWidth: 1
                )
                .frame(width: 8, height: 8)

            Text("\(reserveCount)")
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .foregroundColor(reserveCount == 0 ? WarmTokens.emerald : WarmTokens.bone)

            Text(reserveCount == 0 ? "CLEAR" : "IN RESERVE")
                .font(.system(size: 9, design: .monospaced))
                .tracking(0.8)
                .foregroundColor(
                    reserveCount == 0 ? WarmTokens.emerald.opacity(0.85) : WarmTokens.textGhost
                )
        }
        .accessibilityLabel(
            reserveCount == 0
                ? "Reserve clear"
                : "\(reserveCount) items hidden in reserve"
        )
    }

    // MARK: - Transport

    /// Pull live focus. A transport failure is an explicit offline state,
    /// never a fabricated task on the wrist.
    private func reload() async {
        do {
            let state = try await OneThingAPI.fetchFocus()
            focus = state.focus
            reserveCount = state.reserveCount
            live = true
        } catch {
            live = false
        }
    }

    /// Exactly-once DONE, then re-pull so the next step lands instantly.
    private func complete() async {
        guard !busy, live, let task = focus, task.id >= 0 else { return }
        busy = true
        defer { busy = false }
        do {
            try await OneThingAPI.completeTask(id: task.id)
            await reload()
        } catch {
            live = false
        }
    }

    /// Skip returns the task to the hidden reserve and surfaces the next one.
    private func skip() async {
        guard !busy, live, let task = focus, task.id >= 0 else { return }
        busy = true
        defer { busy = false }
        do {
            try await OneThingAPI.skipTask(id: task.id)
            await reload()
        } catch {
            live = false
        }
    }
}

#Preview {
    ContentView()
}
