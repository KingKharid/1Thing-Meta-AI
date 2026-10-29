# 1Thing Companion Targets — watchOS App + iOS Widgets

This directory holds the Apple companion surfaces. Everything here follows the
same contract: **one active task, reserve count only, no reserve titles**
(Invariants 1–2), identified by the shared testing phone number
`+15550007777` sent as the `X-Phone-Number` header.

| Directory | Contents |
| :--- | :--- |
| `watchos/` | watchOS SwiftUI app: live focus view, DONE completion, WidgetKit complication |
| `ios-widget/` | iOS lock-screen widget (`accessoryRectangular` + `accessoryCircular`) and Live Activity blueprint |
| `wearos/` | Reserved for the Wear OS Tile (not yet scaffolded) |

## Shared backend contract

- `GET /api/v1/focus` → `{ selected_task: { id, title, first_micro_step, estimated_minutes } | null, queued_backlog_count }`
- `POST /api/v1/tasks/{id}/complete` → exactly-once completion + next surfaced task
- Identity header: `X-Phone-Number: +15550007777`
- Deep link: `onething://focus` (widgets set this as their `widgetURL`)

On physical hardware the loopback base URL does not resolve. Point the clients
at the dev machine's LAN address on the same Wi-Fi:
`OneThingAPI.baseURL` (watchOS) and `apiBaseURL` (`ios-widget/`).

## Attaching the iOS widget target in Xcode

The `ios-widget/` blueprint is a complete Widget Extension source set. It is not
an `.xcodeproj` — attach it to your app project once:

1. **Create the host app target** (if none exists): File → New → Target →
   iOS → App. Name it `OneThing`, bundle id e.g. `ai.onething.app`.
2. **Add the Widget Extension target**: File → New → Target → iOS →
   Widget Extension. Name it `OneThingWidgets`, bundle id
   `ai.onething.app.widgets`. **Uncheck "Include Live Activity"** in the
   template dialog — this blueprint already declares `FocusLiveActivity`,
   and the template's stub would collide with it.
3. **Set the deployment target**: select the `OneThingWidgets` target →
   General → Minimum Deployments → **iOS 16.1 or later** (Live Activities
   require 16.1; lock-screen accessories require 16.0).
4. **Replace the template sources**: delete the generated widget stub files
   from the new target and add `watch/ios-widget/LockScreenWidget.swift`
   to the `OneThingWidgets` target membership (uncheck the app target).
5. **Enable App Groups** (for the offline snapshot fallback): select the app
   target → Signing & Capabilities → + Capability → App Groups → add
   `group.ai.onething.focus`. Repeat for the `OneThingWidgets` target.
   Both targets must share the group or `UserDefaults(suiteName:)` returns
   nil and widgets fall back to direct backend reads only.
6. **Allow cleartext HTTP for local dev** (dev only): in the app target's
   `Info.plist` and the widget's `Info.plist`, add an App Transport Security
   exception for your dev host, or serve the API over HTTPS. Production
   builds must use HTTPS with no exception.
7. **Register the deep link**: in the app target → Info → URL Types, add
   scheme `onething` so lock-screen taps route into the focus view.
8. **Add the lock-screen widgets**: on a device (iOS 16+), long-press the
   lock screen → Customize → Lock Screen → Add Widgets → 1Thing Focus.
   Rectangular shows title + micro-step + minute pill; circular shows the
   micro-step capped at 16 chars + minute pill.

### Starting the Live Activity from the app

Activities start in the host app, not the extension. Request and start one
when focus goes live (iOS 16.1+):

```swift
import ActivityKit

func startFocusActivity(title: String, step: String, minutes: Int) throws {
    guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
    let attributes = FocusActivityAttributes(title: title)
    let state = FocusActivityAttributes.ContentState(step: step, minutes: minutes)
    _ = try Activity.request(attributes: attributes, content: .init(state: state, staleDate: nil))
}
```

Update it on every focus change with
`activity.update(.init(state: .init(step:minutes:), staleDate: nil))` and end
it with `await activity.end(nil, dismissalPolicy: .immediate)` when the
surface clears. `FocusActivityAttributes` must be visible to both targets —
move it (and the focus DTOs) into a shared framework as soon as the project
grows one, instead of duplicating the file.

### How the widget stays fresh

- `FocusWidgetProvider` reads `GET /api/v1/focus` directly (8s timeout),
  persists the snapshot to the App Group, and schedules the next refresh
  in 15 minutes.
- When the backend is unreachable, it renders the last App Group snapshot
  badged `HELD`; with neither, it renders the honest empty state.
- After the app files, completes, or skips a task, write the new snapshot
  to the App Group and call `WidgetCenter.shared.reloadTimelines(ofKind:)`
  so the lock screen updates instantly instead of waiting for the timer.

## watchOS app notes (`watchos/`)

- `OneThingWatchApp.swift` is the `@main` entry; `ContentView.swift` pulls
  `GET /api/v1/focus` on appear via `OneThingAPI` and posts exactly-once
  DONE (retries are server-safe).
- Transport failures keep the last rendered state with an `OFFLINE PREVIEW`
  marker; the wrist never blanks.
- `Complication.swift` is the WidgetKit complication companion to the app.
  It shares the 16-char micro-step cap with the iOS circular widget.
