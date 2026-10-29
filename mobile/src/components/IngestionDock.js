import { View, Text, Pressable, StyleSheet } from "react-native";
import { tokens } from "./tokens";

const CHANNELS = [
  { label: "VOICE", hint: "Speak the dump" },
  { label: "SNAP", hint: "Photograph the mess" },
  { label: "TEXT", hint: "Type it out" },
];

/**
 * Universal bottom ingestion dock. Three equal hairline keys, no numbering:
 * the order carries no meaning, so the chrome doesn't imply one.
 */
export function IngestionDock({ onCapture }) {
  return (
    <View style={styles.dock}>
      {CHANNELS.map(({ label, hint }) => (
        <Pressable
          key={label}
          accessibilityRole="button"
          accessibilityLabel={`Capture via ${label.toLowerCase()}`}
          accessibilityHint={hint}
          onPress={() => onCapture?.(label)}
          style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
        >
          {({ pressed }) => (
            <Text style={[styles.label, pressed && styles.labelPressed]}>
              {label}
            </Text>
          )}
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  dock: {
    flexDirection: "row",
    gap: 10,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: tokens.hairline,
  },
  button: {
    flex: 1,
    minHeight: 52,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: tokens.hairline,
    backgroundColor: tokens.carbon,
  },
  buttonPressed: {
    borderColor: tokens.amberLine,
    backgroundColor: tokens.amberDim,
  },
  label: {
    fontFamily: tokens.mono,
    fontSize: 11,
    letterSpacing: 1.8,
    color: tokens.bone,
  },
  labelPressed: {
    color: tokens.amber,
  },
});
