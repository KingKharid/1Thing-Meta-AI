import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  StatusBar,
  ScrollView,
  RefreshControl,
  Platform,
} from "react-native";
import { FocusCard } from "./src/components/FocusCard";
import { CaptureSheet } from "./src/components/CaptureSheet";
import { IngestionDock } from "./src/components/IngestionDock";
import { tokens } from "./src/components/tokens";
import { fetchFocus, completeTask, skipTask, FALLBACK_FOCUS, OFFLINE_FOCUS } from "./src/lib/api";

const TOP_INSET = Platform.OS === "ios" ? 58 : (StatusBar.currentHeight ?? 24) + 14;
const BOTTOM_INSET = Platform.OS === "ios" ? 34 : 18;

/**
 * 1Thing Expo focus interface: single-screen, dark-mode, one active task.
 *
 * DONE/SKIP post to the live API when configured. When the API is
 * configured but unreachable, the screen says so and disables actions —
 * it never shows a fabricated task.
 */
export default function App() {
  const [focus, setFocus] = useState(FALLBACK_FOCUS);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [sheetChannel, setSheetChannel] = useState(null);

  const refresh = useCallback(() => {
    fetchFocus().then(setFocus).catch(() => setFocus(OFFLINE_FOCUS));
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchFocus()
      .then(setFocus)
      .catch(() => setFocus(OFFLINE_FOCUS))
      .finally(() => setRefreshing(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function act(label, fn) {
    if (!focus.live || !focus.task || focus.task.id < 0) {
      setError("NOTHING TO ACT ON — THE ENGINE IS NOT REACHABLE");
      return;
    }
    setPending(label);
    setError(null);
    try {
      await fn(focus.task.id);
      refresh();
    } catch {
      setError(`${label} FAILED — NOTHING CHANGED · RETRY`);
    } finally {
      setPending(null);
    }
  }

  const statusLabel =
    focus.mode === "live" ? "LIVE" : focus.mode === "error" ? "OFFLINE" : "PREVIEW";
  const statusColor =
    focus.mode === "live"
      ? tokens.emerald
      : focus.mode === "error"
        ? tokens.amber
        : tokens.textGhost;

  return (
    <View style={styles.shell}>
      <StatusBar barStyle="light-content" backgroundColor={tokens.erebus} />

      <View style={styles.topbar}>
        <View style={styles.brand}>
          <View style={styles.brandMark} />
          <Text style={styles.wordmark}>1Thing</Text>
          <View style={styles.brandRule} />
          <Text style={styles.brandSub}>ONE PHYSICAL NEXT STEP</Text>
        </View>
        <View style={styles.statusChip}>
          <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
          <Text style={styles.status}>{statusLabel}</Text>
        </View>
      </View>

      <View style={styles.body}>
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={tokens.amber}
            />
          }
        >
          <FocusCard
            task={focus.task}
            reserveCount={focus.reserveCount}
            live={focus.live}
            mode={focus.mode}
          />

          {focus.mode === "error" && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Retry connection"
              onPress={onRefresh}
              style={({ pressed }) => [
                styles.retry,
                pressed && styles.retryPressed,
              ]}
            >
              <Text style={styles.retryLabel}>RETRY</Text>
            </Pressable>
          )}

          {focus.task && (
            <View style={styles.actions}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Mark done"
                accessibilityHint="Archives this task and surfaces the next one"
                disabled={!focus.live || pending !== null}
                onPress={() => act("DONE", completeTask)}
                style={({ pressed }) => [
                  styles.action,
                  styles.actionDone,
                  pressed && styles.actionDonePressed,
                  (!focus.live || pending !== null) && styles.actionDisabled,
                ]}
              >
                <Text style={styles.actionLabelDone}>
                  {pending === "DONE" ? "SETTLING…" : "DONE"}
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Skip task"
                accessibilityHint="Returns this task to the hidden reserve"
                disabled={!focus.live || pending !== null}
                onPress={() => act("SKIP", skipTask)}
                style={({ pressed }) => [
                  styles.action,
                  styles.actionSkip,
                  pressed && styles.actionSkipPressed,
                  (!focus.live || pending !== null) && styles.actionDisabled,
                ]}
              >
                <Text style={styles.actionLabelSkip}>
                  {pending === "SKIP" ? "MOVING…" : "SKIP"}
                </Text>
              </Pressable>
            </View>
          )}

          {focus.mode === "preview" && (
            <Text style={styles.actionNote}>
              PREVIEW — ACTIONS DISABLED UNTIL THE ENGINE IS REACHABLE
            </Text>
          )}

          {error && (
            <View style={styles.errorBanner} accessibilityRole="alert">
              <View style={styles.errorRail} />
              <Text style={styles.error}>{error}</Text>
            </View>
          )}
        </ScrollView>
      </View>

      <IngestionDock onCapture={setSheetChannel} />

      <CaptureSheet
        channel={sheetChannel}
        onClose={() => setSheetChannel(null)}
        onSaved={refresh}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    flex: 1,
    backgroundColor: tokens.erebus,
    paddingHorizontal: 20,
    paddingTop: TOP_INSET,
    paddingBottom: BOTTOM_INSET,
  },

  topbar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    marginBottom: 22,
  },
  brand: { flexDirection: "row", alignItems: "center", gap: 9, flexShrink: 1 },
  brandMark: { width: 8, height: 8, backgroundColor: tokens.amber },
  wordmark: {
    fontSize: 17,
    fontWeight: "700",
    letterSpacing: -0.3,
    color: tokens.bone,
  },
  brandRule: {
    width: 1,
    height: 14,
    backgroundColor: tokens.hairlineStrong,
    marginHorizontal: 2,
  },
  brandSub: {
    fontFamily: tokens.mono,
    fontSize: 9,
    letterSpacing: 1.2,
    color: tokens.textGhost,
    flexShrink: 1,
  },

  statusChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: tokens.hairline,
    paddingVertical: 6,
    paddingHorizontal: 9,
  },
  statusDot: { width: 5, height: 5 },
  status: {
    fontFamily: tokens.mono,
    fontSize: 9,
    letterSpacing: 1.4,
    color: tokens.textFaint,
  },

  body: { flex: 1 },
  scroll: { flex: 1 },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    paddingVertical: 8,
  },

  /* DONE is the machined bone key; SKIP is a hairline outline. */
  actions: { flexDirection: "row", gap: 12, marginTop: 14 },
  action: {
    alignItems: "center",
    justifyContent: "center",
    minHeight: 56,
    borderWidth: 1,
  },
  actionDone: {
    flex: 1.15,
    borderColor: tokens.bone,
    backgroundColor: tokens.bone,
  },
  actionDonePressed: { backgroundColor: "rgba(249, 248, 246, 0.86)" },
  actionSkip: {
    flex: 1,
    borderColor: tokens.hairlineStrong,
    backgroundColor: "transparent",
  },
  actionSkipPressed: {
    borderColor: tokens.hairlineBright,
    backgroundColor: tokens.carbonRaised,
  },
  actionDisabled: { opacity: 0.5 },
  actionLabelDone: {
    fontFamily: tokens.mono,
    fontSize: 12,
    letterSpacing: 1.8,
    fontWeight: "700",
    color: tokens.erebus,
  },
  actionLabelSkip: {
    fontFamily: tokens.mono,
    fontSize: 12,
    letterSpacing: 1.8,
    color: tokens.textDim,
  },

  /* Offline recovery: an outline key, never an amber fill. */
  retry: {
    alignSelf: "flex-start",
    marginTop: 14,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderWidth: 1,
    borderColor: tokens.hairlineStrong,
  },
  retryPressed: {
    borderColor: tokens.hairlineBright,
    backgroundColor: tokens.carbonRaised,
  },
  retryLabel: {
    fontFamily: tokens.mono,
    fontSize: 11,
    letterSpacing: 1.8,
    color: tokens.bone,
  },

  actionNote: {
    marginTop: 12,
    fontFamily: tokens.mono,
    fontSize: 10,
    lineHeight: 15,
    letterSpacing: 1.2,
    color: tokens.textFaint,
  },

  errorBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginTop: 14,
    paddingVertical: 11,
    paddingRight: 12,
    backgroundColor: tokens.carbon,
    borderWidth: 1,
    borderColor: tokens.hairline,
  },
  errorRail: { width: 2, alignSelf: "stretch", backgroundColor: tokens.amber },
  error: {
    flex: 1,
    fontFamily: tokens.mono,
    fontSize: 10,
    lineHeight: 15,
    letterSpacing: 1.2,
    color: tokens.amber,
  },
});
