import SwiftUI

/// Warm Industrial Minimalism tokens for watchOS.
enum WarmTokens {
    static let erebus = Color(red: 0x0C / 255, green: 0x0D / 255, blue: 0x0E / 255)
    static let carbon = Color(red: 0x16 / 255, green: 0x18 / 255, blue: 0x1A / 255)
    static let bone = Color(red: 0xF9 / 255, green: 0xF8 / 255, blue: 0xF6 / 255)
    static let amber = Color(red: 0xF5 / 255, green: 0x9E / 255, blue: 0x0B / 255)
    static let emerald = Color(red: 0x10 / 255, green: 0xB9 / 255, blue: 0x81 / 255)
}

/// Preview payload until the companion sync phase wires URLSession to
/// GET /api/v1/focus with the phone-identity header.
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

struct ContentView: View {
    let focus: WatchFocus

    init(focus: WatchFocus = .preview) {
        self.focus = focus
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("ACTIVE FOCUS")
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(WarmTokens.bone.opacity(0.55))
            Text(focus.title)
                .font(.headline)
                .foregroundColor(WarmTokens.bone)
                .lineLimit(3)
            Text("▸ \(focus.firstMicroStep)")
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundColor(WarmTokens.amber)
                .lineLimit(2)
            Text("[\(focus.estimatedMinutes)M]")
                .font(.system(size: 12, design: .monospaced))
                .foregroundColor(WarmTokens.bone)
                .padding(6)
                .border(WarmTokens.bone.opacity(0.08), width: 1)
            // DONE posts to the completion API in the companion sync phase.
            Button("DONE") {}
                .font(.system(size: 13, weight: .bold, design: .monospaced))
                .foregroundColor(WarmTokens.bone)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .border(WarmTokens.bone.opacity(0.08), width: 1)
        }
        .padding()
        .background(WarmTokens.erebus)
    }
}

#Preview {
    ContentView()
}
