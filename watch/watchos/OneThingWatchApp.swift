import SwiftUI

/// 1Thing watchOS entry point. Single-screen focus surface: the active
/// task only, with exactly-once DONE fanning out over the completion API.
@main
struct OneThingWatchApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
