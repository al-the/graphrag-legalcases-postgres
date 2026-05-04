export const MY_ENTITY_COLORS: Record<string, string> = {
  ORGANIZATION:         "#a855f7",
  PERSON:               "#10b981",
  LAW:                  "#f59e0b",
  REGULATION:           "#f97316",
  FINANCIAL_INSTRUMENT: "#06b6d4",
  LOCATION:             "#3b82f6",
  MINISTRY:             "#8b5cf6",
  COMMITTEE:            "#ec4899",
  EVENT:                "#f43f5e",
  METRIC:               "#84cc16",
  DATE:                 "#64748b",
  DEFAULT:              "#94a3b8",
};

export const NODE_SIZE_BASE = 6;
export const NODE_SIZE_SCALE = 0.4; // added per unit of degree

export function entityColor(type: string): string {
  return MY_ENTITY_COLORS[type?.toUpperCase()] ?? MY_ENTITY_COLORS.DEFAULT;
}
