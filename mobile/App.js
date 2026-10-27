import { useCallback, useEffect, useState } from "react";
import { View, Text, Pressable, StyleSheet, StatusBar } from "react-native";
import { FocusCard } from "./src/components/FocusCard";
import { IngestionDock } from "./src/components/IngestionDock";
import { tokens } from "./src/components/tokens";
import { fetchFocus, completeTask, skipTask, FALLBACK_FOCUS } from "./src/lib/api";

/**
 * 1Thing Expo focus interface: single-screen, dark-mode, one active task.
 * DONE/SKIP post to the live API when configured; otherwise the screen
 * renders the offline preview.
 */
export default function App() {
  const [focus, setFocus] = useState(FALLBACK_FOCUS);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(null);

  const refresh = useCallback(() => {
    fetchFocus().then(setFocus).catch(() => setFocus(FALLBACK_FOCUS));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function act(label, fn) {
    if (!focus.live || !focus.task || focus.task.id < 0) {
      setError("OFFLINE PREVIEW — ACTIONS DISABLED");
      return;
    }
    setPending(label);
    setError(null);
    try {
      await fn(focus.task.id);
      refresh();
    } catch {
      setError(`${label} FAILED — RETRY`);
    } finally {
      setPending(null);
    }
  }

  return (
    <View style={styles.shell}>
      <StatusBar barStyle="light-content" backgroundColor={tokens.erebus} />
      <View style={styles.topbar}>
        <Text style={styles.wordmark}>1Thing</Text>
        <Text style={styles.status}>{focus.live ? "LIVE" : "OFFLINE"}</Text>
      </View>
      <View style={styles.body}>
        <FocusCard task={focus.task} reserveCount={focus.reserveCount} live={focus.live} />
        {focus.task && (
          <View style={styles.actions}>
            <Pressable
              style={styles.action}
              accessibilityLabel="Mark done"
              disabled={pending !== null}
              onPress={() => act("DONE", completeTask)}
            >
              <Text style={styles.actionLabel}>{pending === "DONE" ? "..." : "DONE"}</Text>
            </Pressable>
            <Pressable
              style={styles.action}
              accessibilityLabel="Skip task"
              disabled={pending !== null}
              onPress={() => act("SKIP", skipTask)}
            >
              <Text style={styles.actionLabel}>{pending === "SKIP" ? "..." : "SKIP"}</Text>
            </Pressable>
          </View>
        )}
        {error && (
          <Text style={styles.error} role="alert">
            {error}
          </Text>
        )}
      </View>
      <IngestionDock />
    </View>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1, backgroundColor: tokens.erebus, padding: 32, paddingTop: 64 },
  topbar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 32,
  },
  wordmark: { fontSize: 18, fontWeight: "700", color: tokens.bone },
  status: { fontFamily: "monospace", fontSize: 12, color: tokens.bone, opacity: 0.7 },
  body: { flex: 1, justifyContent: "center" },
  actions: { flexDirection: "row", gap: 12, marginTop: 16 },
  action: {
    flex: 1,
    borderWidth: 1,
    borderColor: tokens.hairline,
    paddingVertical: 14,
    alignItems: "center",
  },
  actionLabel: { fontFamily: "monospace", fontSize: 12, letterSpacing: 1, color: tokens.bone },
  error: { fontFamily: "monospace", fontSize: 12, color: tokens.amber, marginTop: 16 },
});
