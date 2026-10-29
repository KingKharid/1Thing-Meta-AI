import Foundation

/// 1Thing watchOS API client.
///
/// Identity default matches every other surface: the shared testing
/// phone number, sent as the `X-Phone-Number` header so focus state
/// synchronizes across web, mobile, watch, and WhatsApp.
///
/// `baseURL` defaults to the local FastAPI server. A physical watch
/// cannot reach a Mac's loopback interface, so point this at the Mac's
/// LAN address (same Wi-Fi) for on-device testing.
enum OneThingAPI {
    static let defaultPhoneNumber = "+15550007777"
    static let baseURL = URL(string: "http://127.0.0.1:8000")!

    struct FocusResponse: Decodable {
        struct SelectedTask: Decodable {
            let id: Int
            let title: String
            let firstMicroStep: String
            let estimatedMinutes: Int

            private enum CodingKeys: String, CodingKey {
                case id, title
                case firstMicroStep = "first_micro_step"
                case estimatedMinutes = "estimated_minutes"
            }
        }

        let selectedTask: SelectedTask?
        let queuedBacklogCount: Int

        private enum CodingKeys: String, CodingKey {
            case selectedTask = "selected_task"
            case queuedBacklogCount = "queued_backlog_count"
        }
    }

    struct FocusState {
        let focus: WatchFocus?
        let reserveCount: Int
    }

    private static func request(path: String, method: String = "GET") -> URLRequest {
        // Resolve against baseURL instead of appending path components, so a
        // query string such as "?mode=reserve" survives intact.
        let url = URL(string: path, relativeTo: baseURL) ?? baseURL
        var request = URLRequest(
            url: url,
            cachePolicy: .reloadIgnoringLocalCacheData,
            timeoutInterval: 8
        )
        request.httpMethod = method
        request.setValue(defaultPhoneNumber, forHTTPHeaderField: "X-Phone-Number")
        return request
    }

    private static func decodeFocus(_ data: Data) -> FocusState {
        guard let response = try? JSONDecoder().decode(FocusResponse.self, from: data) else {
            return FocusState(focus: nil, reserveCount: 0)
        }
        guard let selected = response.selectedTask else {
            return FocusState(focus: nil, reserveCount: response.queuedBacklogCount)
        }
        let focus = WatchFocus(
            id: selected.id,
            title: selected.title,
            firstMicroStep: selected.firstMicroStep,
            estimatedMinutes: selected.estimatedMinutes
        )
        return FocusState(focus: focus, reserveCount: response.queuedBacklogCount)
    }

    /// GET /api/v1/focus. Throws on transport or HTTP errors so the
    /// caller can fall back to the last rendered state.
    static func fetchFocus() async throws -> FocusState {
        let (data, response) = try await URLSession.shared.data(for: request(path: "/api/v1/focus"))
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        return decodeFocus(data)
    }

    /// POST /api/v1/tasks/{id}/complete. Exactly-once server-side, so
    /// retries from the wrist are safe.
    static func completeTask(id: Int) async throws {
        let ( _, response) = try await URLSession.shared.data(
            for: request(path: "/api/v1/tasks/\(id)/complete", method: "POST")
        )
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }

    /// POST /api/v1/tasks/{id}/skip?mode=reserve. Demotes the task to the
    /// hidden reserve and promotes the next one.
    static func skipTask(id: Int) async throws {
        let ( _, response) = try await URLSession.shared.data(
            for: request(path: "/api/v1/tasks/\(id)/skip?mode=reserve", method: "POST")
        )
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }
}
