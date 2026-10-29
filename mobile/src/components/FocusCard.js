import { Text, View, StyleSheet } from "react-native";
import { tokens } from "./tokens";

/**
 * Single active-task card.
 *
 * The micro-step is the hero; the task title is a mono kicker above it.
 * Shows strictly one task, its first physical step, the time pill, and the
 * hidden reserve *count* — never reserve titles (Invariant 2).
 *
 * Three honest states: focus, standby (live but empty), offline (the
 * engine did not answer — no invented task, ever).
 */
export function FocusCard({ task, reserveCount, live, mode }) {
  if (mode === "error") {
    return (
      <View
        style={[styles.card, styles.cardOffline]}
        accessibilityLabel="Engine offline"
      >
        <View style={styles.headRow}>
          <Text style={[styles.task, styles.taskOffline]}>ENGINE OFFLINE</Text>
        </View>

        <Text style={styles.title}>NO DATA</Text>
        <Text style={styles.sub}>
          The focus API didn&apos;t answer. Nothing was lost — pull down to
          retry.
        </Text>
      </View>
    );
  }

  if (!task) {
    return (
      <View
        style={[styles.card, styles.cardIdle]}
        accessibilityLabel="No active task"
      >
        <View style={styles.headRow}>
          <Text style={styles.task}>STANDBY</Text>
        </View>

        <Text style={styles.title}>NOTHING IN FOCUS</Text>
        <Text style={styles.sub}>
          The surface is clear. Send anything — voice, snap, or text — and the
          system returns one physical next step.
        </Text>

        <View style={styles.ingestBay}>
          <View style={styles.ingestTarget}>
            <View style={styles.ingestTargetPip} />
          </View>
          <View style={styles.ingestCopy}>
            <Text style={styles.ingestTitle}>AWAITING INPUT</Text>
            <Text style={styles.ingestLine}>ANY FORMAT IN · ONE STEP OUT</Text>
          </View>
        </View>

        <ReserveLine count={reserveCount} />
      </View>
    );
  }

  const minutes = task.estimatedMinutes;
  const hasStep = Boolean(task.firstMicroStep && task.firstMicroStep.trim());
  const longStep = hasStep && task.firstMicroStep.length > 40;
  const serial = live && task.id > 0 ? `#${String(task.id).padStart(3, "0")}` : "PREVIEW";

  return (
    <View style={styles.card} accessibilityLabel="Current task">
      <View style={styles.headRow}>
        <Text style={styles.task} numberOfLines={1}>
          {task.title}
        </Text>
        <Text style={styles.serial}>{serial}</Text>
      </View>

      <View style={styles.stepLabelRow}>
        {hasStep && <View style={styles.stepTick} />}
        <Text style={[styles.stepLabel, !hasStep && styles.stepLabelMuted]}>
          {hasStep ? "NEXT STEP" : "STEP MISSING"}
        </Text>
      </View>

      {hasStep ? (
        <Text style={[styles.step, longStep && styles.stepLong]} numberOfLines={3}>
          {task.firstMicroStep}
        </Text>
      ) : (
        <>
          <Text style={styles.stepPending}>NO STEP YET</Text>
          <Text style={styles.sub}>
            The engine didn&apos;t return a first move for this. The dump is safe.
          </Text>
        </>
      )}

      <Text style={styles.pill}>[{minutes}M]</Text>

      <ReserveLine count={reserveCount} />
    </View>
  );
}

/** One reserve primitive: glyph + count + "in reserve · hidden". Count only. */
function ReserveLine({ count }) {
  const clear = count === 0;
  return (
    <View
      style={styles.reserveLine}
      accessibilityLabel={
        clear ? "Reserve clear" : `${count} items hidden in reserve`
      }
    >
      <View style={[styles.reserveGlyph, clear && styles.reserveGlyphClear]}>
        <View style={[styles.reserveGlyphInner, clear && styles.reserveGlyphInnerClear]} />
      </View>
      <Text style={[styles.reserveCount, clear && styles.reserveCountClear]}>
        {count}
      </Text>
      <Text style={[styles.reserveText, clear && styles.reserveTextClear]}>
        {clear ? "RESERVE CLEAR" : "IN RESERVE · HIDDEN"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: tokens.carbon,
    borderWidth: 1,
    borderColor: tokens.hairlineStrong,
    padding: 26,
  },
  cardIdle: {
    borderStyle: "dashed",
    borderColor: tokens.hairlineStrong,
    backgroundColor: tokens.erebus,
  },
  cardOffline: {
    borderLeftWidth: 2,
    borderLeftColor: tokens.amber,
  },

  headRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 22,
  },
  task: {
    flexShrink: 1,
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.6,
    color: tokens.textFaint,
  },
  taskOffline: {
    color: tokens.amber,
  },
  serial: {
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.2,
    color: tokens.textGhost,
  },

  title: {
    fontSize: 30,
    lineHeight: 35,
    fontWeight: "600",
    letterSpacing: -0.7,
    color: tokens.bone,
    marginBottom: 16,
  },
  sub: {
    fontSize: 14,
    lineHeight: 21,
    color: tokens.textDim,
    marginBottom: 22,
  },

  stepLabelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 14,
  },
  stepTick: {
    width: 6,
    height: 6,
    backgroundColor: tokens.amber,
  },
  stepLabel: {
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 2.2,
    color: tokens.amber,
  },
  stepLabelMuted: { color: tokens.textFaint },
  stepPending: {
    fontSize: 22,
    lineHeight: 28,
    fontWeight: "600",
    letterSpacing: -0.3,
    color: tokens.textDim,
    marginBottom: 12,
  },
  step: {
    fontSize: 22,
    lineHeight: 28,
    fontWeight: "600",
    letterSpacing: -0.3,
    color: tokens.bone,
    marginBottom: 20,
  },
  /* Long steps degrade to two tiers instead of becoming a wall of text. */
  stepLong: {
    fontSize: 19,
    lineHeight: 26,
  },

  pill: {
    alignSelf: "flex-start",
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.2,
    color: tokens.textDim,
    borderWidth: 1,
    borderColor: tokens.hairline,
    paddingVertical: 7,
    paddingHorizontal: 10,
    marginBottom: 24,
  },

  reserveLine: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  reserveGlyph: {
    width: 12,
    height: 12,
    borderWidth: 1,
    borderColor: tokens.hairlineBright,
    alignItems: "flex-end",
    justifyContent: "flex-end",
  },
  reserveGlyphInner: {
    width: 8,
    height: 8,
    borderWidth: 1,
    borderColor: tokens.hairlineStrong,
    marginRight: -4,
    marginBottom: -4,
  },
  reserveGlyphClear: { borderColor: tokens.emeraldLine },
  reserveGlyphInnerClear: { borderColor: tokens.emeraldLine },
  reserveCount: {
    fontFamily: tokens.mono,
    fontSize: 12,
    color: tokens.bone,
  },
  reserveCountClear: { color: tokens.emerald },
  reserveText: {
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.6,
    color: tokens.textFaint,
  },
  reserveTextClear: { color: tokens.emerald },

  ingestBay: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: tokens.hairlineStrong,
    padding: 18,
    marginBottom: 22,
  },
  ingestTarget: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: tokens.amberLine,
  },
  ingestTargetPip: {
    width: 7,
    height: 7,
    backgroundColor: tokens.amber,
  },
  ingestCopy: { flex: 1, gap: 6 },
  ingestTitle: {
    fontFamily: tokens.mono,
    fontSize: 11,
    letterSpacing: 1.6,
    color: tokens.bone,
  },
  ingestLine: {
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.1,
    color: tokens.textFaint,
  },
});
