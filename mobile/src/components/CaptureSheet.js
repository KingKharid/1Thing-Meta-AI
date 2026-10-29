import { useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { tokens } from "./tokens";
import { createTask } from "../lib/api";

/** Matches the server's cap. A week of thoughts fits; a novel does not. */
const MAX_CHARS = 8000;
const COUNT_FROM = 1200;

const MODE_NOTES = {
  VOICE:
    "VOICE FILE — recording + transcription lands with the media pipeline. Type it below to file it now.",
  SNAP:
    "SNAP FILE — viewfinder capture + visual parsing lands with the media pipeline. Type it below to file it now.",
  TEXT:
    "DUMP IT — everything on your mind, however messy. You get one physical next step back.",
};

/**
 * Capture sheet: one message, as long as the user needs.
 *
 * This used to be a four-field form (title, step, minutes, energy), which
 * asked a person in executive overload to do the decomposition the engine
 * exists to do. Now it is a dump: paste a week of loose ends, send, and the
 * model extracts every task, surfaces the first one, and hides the rest in
 * the reserve.
 *
 * Every dock channel lands here. TEXT is fully native today; VOICE/SNAP
 * accept a typed dump until their capture pipelines land.
 */
export function CaptureSheet({ channel, onClose, onSaved }) {
  const [dump, setDump] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const visible = channel !== null;
  const canSubmit = dump.trim().length > 0 && !pending;

  function reset() {
    setDump("");
    setPending(false);
    setError(null);
  }

  function close() {
    reset();
    onClose();
  }

  async function submit() {
    if (!dump.trim()) {
      setError("NOTHING TO FILE — TYPE OR PASTE SOMETHING FIRST");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await createTask({ dump: dump.trim() });
      reset();
      onClose();
      onSaved();
    } catch (err) {
      // Nothing was filed on either branch, so the text stays exactly where
      // the user left it. A 503 means the engine could not read the dump.
      setError(
        err && err.status === 503
          ? "NOTHING FILED — THE ENGINE COULD NOT READ THIS. YOUR DUMP IS STILL HERE."
          : "NOTHING FILED — THE ENGINE DID NOT ANSWER. YOUR DUMP IS STILL HERE."
      );
      setPending(false);
    }
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={close}
      accessibilityLabel="Capture sheet"
    >
      <KeyboardAvoidingView
        style={styles.scrim}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.sheet}>
          <View style={styles.headRow}>
            <Text style={styles.kicker}>DUMP // {channel ?? ""}</Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Close capture sheet"
              onPress={close}
              style={({ pressed }) => [
                styles.closeButton,
                pressed && styles.closeButtonPressed,
              ]}
            >
              <Text style={styles.closeLabel}>ESC</Text>
            </Pressable>
          </View>

          <Text style={styles.note}>{MODE_NOTES[channel] ?? MODE_NOTES.TEXT}</Text>

          <TextInput
            style={styles.input}
            value={dump}
            onChangeText={setDump}
            placeholder="A week of loose ends, a single thought — anything"
            placeholderTextColor={tokens.textGhost}
            multiline
            textAlignVertical="top"
            maxLength={MAX_CHARS}
            accessibilityLabel="Thought dump"
            editable={!pending}
          />

          <View style={styles.hintRow}>
            <Text style={styles.hintGlyph}>↳</Text>
            <Text style={styles.hint}>
              {pending ? "EXTRACTING" : "AS MUCH AS YOU WANT · ONE THING BACK"}
            </Text>
            {dump.length > COUNT_FROM && (
              <Text style={styles.count}>
                {dump.length} / {MAX_CHARS}
              </Text>
            )}
          </View>

          {error && (
            <Text style={styles.error} accessibilityRole="alert">
              {error}
            </Text>
          )}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="File dump"
            disabled={!canSubmit}
            onPress={submit}
            style={({ pressed }) => [
              styles.submit,
              !canSubmit && styles.submitDisabled,
              pressed && canSubmit && styles.submitPressed,
            ]}
          >
            <Text style={styles.submitLabel}>
              {pending ? "EXTRACTING…" : "FILE DUMP"}
            </Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(12, 13, 14, 0.72)",
  },
  sheet: {
    backgroundColor: tokens.carbon,
    borderWidth: 1,
    borderColor: tokens.hairlineStrong,
    padding: 24,
    gap: 10,
  },
  headRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  kicker: {
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.8,
    color: tokens.textFaint,
  },
  closeButton: {
    borderWidth: 1,
    borderColor: tokens.hairline,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  closeButtonPressed: { borderColor: tokens.amberLine },
  closeLabel: {
    fontFamily: tokens.mono,
    fontSize: 10,
    letterSpacing: 1.4,
    color: tokens.bone,
  },
  note: {
    fontFamily: tokens.mono,
    fontSize: 9,
    lineHeight: 14,
    letterSpacing: 0.8,
    color: tokens.textGhost,
    marginBottom: 6,
  },
  input: {
    fontFamily: tokens.mono,
    fontSize: 13,
    lineHeight: 20,
    color: tokens.bone,
    borderWidth: 1,
    borderColor: tokens.hairline,
    backgroundColor: tokens.erebus,
    paddingVertical: 12,
    paddingHorizontal: 12,
    minHeight: 150,
    maxHeight: 260,
  },
  hintRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  hintGlyph: {
    fontFamily: tokens.mono,
    fontSize: 11,
    color: tokens.textGhost,
  },
  hint: {
    flex: 1,
    fontFamily: tokens.mono,
    fontSize: 9,
    letterSpacing: 1.2,
    color: tokens.textGhost,
  },
  count: {
    fontFamily: tokens.mono,
    fontSize: 9,
    letterSpacing: 1,
    color: tokens.textFaint,
    fontVariant: ["tabular-nums"],
  },
  error: {
    fontFamily: tokens.mono,
    fontSize: 9,
    lineHeight: 14,
    letterSpacing: 1.2,
    color: tokens.amber,
    marginTop: 4,
  },
  submit: {
    alignItems: "center",
    borderWidth: 1,
    borderColor: tokens.bone,
    backgroundColor: tokens.bone,
    paddingVertical: 16,
    marginTop: 10,
  },
  submitDisabled: { opacity: 0.4 },
  submitPressed: { backgroundColor: "rgba(249, 248, 246, 0.86)" },
  submitLabel: {
    fontFamily: tokens.mono,
    fontSize: 12,
    letterSpacing: 1.8,
    fontWeight: "700",
    color: tokens.erebus,
  },
});
