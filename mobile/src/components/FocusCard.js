import { Text, View, StyleSheet } from "react-native";
import { tokens } from "./tokens";

/**
 * Single active-task card. Shows strictly one task, its first micro-step,
 * the time pill, and the hidden reserve count — never reserve titles.
 */
export function FocusCard({ task, reserveCount, live }) {
  if (!task) {
    return (
      <View style={styles.card} accessibilityLabel="No active task">
        <Text style={styles.title}>NOTHING IN FOCUS</Text>
        <Text style={styles.step}>▸ SEND A VOICE NOTE TO BEGIN</Text>
        <Text style={styles.reserve}>
          RESERVE: {reserveCount} ITEMS IN STASIS (HIDDEN)
        </Text>
        {!live && <Text style={styles.offline}>OFFLINE PREVIEW</Text>}
      </View>
    );
  }
  return (
    <View style={styles.card} accessibilityLabel="Current task">
      <Text style={styles.kicker}>ACTIVE FOCUS</Text>
      <Text style={styles.title}>{task.title}</Text>
      <Text style={styles.step}>▸ {task.firstMicroStep}</Text>
      <View style={styles.metaRow}>
        <Text style={[styles.pill, styles.pillAmber]}>[{task.estimatedMinutes}M]</Text>
        <Text style={styles.pill}>ONE STEP</Text>
      </View>
      <Text style={styles.reserve}>
        RESERVE: {reserveCount} ITEMS IN STASIS (HIDDEN)
      </Text>
      {!live && <Text style={styles.offline}>OFFLINE PREVIEW</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: tokens.carbon,
    borderWidth: 1,
    borderColor: tokens.hairline,
    padding: 32,
  },
  kicker: {
    fontFamily: "monospace",
    fontSize: 12,
    letterSpacing: 1,
    color: tokens.bone,
    opacity: 0.55,
    marginBottom: 16,
  },
  title: { fontSize: 26, fontWeight: "600", color: tokens.bone, marginBottom: 20 },
  step: { fontSize: 15, fontWeight: "600", color: tokens.amber, marginBottom: 20 },
  metaRow: { flexDirection: "row", gap: 12, marginBottom: 20 },
  pill: {
    fontFamily: "monospace",
    fontSize: 12,
    color: tokens.bone,
    borderWidth: 1,
    borderColor: tokens.hairline,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  pillAmber: { borderColor: tokens.amber, color: tokens.amber },
  reserve: { fontFamily: "monospace", fontSize: 12, color: tokens.bone, opacity: 0.55 },
  offline: {
    fontFamily: "monospace",
    fontSize: 12,
    color: tokens.amber,
    marginTop: 16,
  },
});
