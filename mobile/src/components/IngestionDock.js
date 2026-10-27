import { View, Text, Pressable, StyleSheet } from "react-native";
import { tokens } from "./tokens";

/**
 * Universal bottom ingestion dock. Capture handlers (voice recorder,
 * camera, text sheet) land with the device-permission phase.
 */
export function IngestionDock({ onCapture }) {
  const buttons = ["VOICE", "SNAP", "TEXT"];
  return (
    <View style={styles.dock}>
      {buttons.map((label) => (
        <Pressable
          key={label}
          style={styles.button}
          accessibilityLabel={`Capture via ${label.toLowerCase()}`}
          onPress={() => onCapture?.(label)}
        >
          <Text style={styles.label}>[{label}]</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  dock: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: tokens.hairline,
    paddingTop: 24,
  },
  button: {
    flex: 1,
    borderWidth: 1,
    borderColor: tokens.hairline,
    paddingVertical: 14,
    alignItems: "center",
  },
  label: { fontFamily: "monospace", fontSize: 12, letterSpacing: 1, color: tokens.bone },
});
