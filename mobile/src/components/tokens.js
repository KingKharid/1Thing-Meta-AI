import { Platform } from "react-native";

/**
 * Warm Industrial Minimalism tokens shared by mobile components.
 *
 * Erebus void, carbon surfaces, bone type, focus amber, momentum emerald.
 * Flat by default: 1px hairlines instead of shadows, zero corner radius.
 */
export const tokens = {
  // Surfaces
  erebus: "#0C0D0E",
  carbon: "#16181A",
  carbonRaised: "#1C1F22",

  // Type — every step clears 4.5:1 on carbon.
  bone: "#F9F8F6",
  textDim: "rgba(249, 248, 246, 0.76)",
  textFaint: "rgba(249, 248, 246, 0.58)",
  textGhost: "rgba(249, 248, 246, 0.5)",

  // Accents
  amber: "#F59E0B",
  amberDim: "rgba(245, 158, 11, 0.16)",
  amberLine: "rgba(245, 158, 11, 0.34)",
  amberGlow: "rgba(245, 158, 11, 0.20)",
  emerald: "#10B981",
  emeraldDim: "rgba(16, 185, 129, 0.16)",
  emeraldLine: "rgba(16, 185, 129, 0.34)",

  // Hairlines
  hairline: "rgba(249, 248, 246, 0.08)",
  hairlineStrong: "rgba(249, 248, 246, 0.16)",
  hairlineBright: "rgba(249, 248, 246, 0.28)",

  // Type scale
  mono: Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" }),

  // Spacing
  space: { xs: 6, sm: 10, md: 16, lg: 22, xl: 32 },

  // Zero corner radius: this system is engineered, not rounded.
  radius: 0,
};
