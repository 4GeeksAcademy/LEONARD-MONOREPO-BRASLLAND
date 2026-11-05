import { applicationContent } from "@/content/application";
import type { FieldConfig, FieldId, FormValues, ValidationRule } from "@/types/application";

// Rules live in content/application.ts (ported from Milestone 1 validation.js, same messages); this file only evaluates them.
export const FIELD_ORDER: readonly FieldId[] = [
  "requesterName",
  "department",
  "workEmail",
  "workPhone",
  "locationId",
  "countryMarket",
  "challengeType",
  "targetDate",
  "weeklyIncidents",
  "currentProcess",
  "expectedOutcome",
  "confirmData",
];

export const EMPTY_VALUES: FormValues = {
  requesterName: "",
  department: "",
  workEmail: "",
  workPhone: "",
  locationId: "",
  countryMarket: "",
  challengeType: "",
  targetDate: "",
  weeklyIncidents: "",
  currentProcess: "",
  expectedOutcome: "",
  confirmData: false,
};

const FIELDS: Record<FieldId, FieldConfig> = Object.fromEntries(
  applicationContent.fieldsets.flatMap((set) => set.fields.map((field) => [field.name, field])),
) as Record<FieldId, FieldConfig>;

function startOfToday(): Date {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function checkRule(rule: ValidationRule, raw: string | boolean): string | null {
  if (typeof raw === "boolean") return raw ? null : rule.requiredMessage;

  const value = raw.trim();
  if (!value) return rule.requiredMessage;
  if (rule.minLength && value.length < rule.minLength.value) return rule.minLength.message;

  for (const { pattern, message } of rule.patterns ?? []) {
    if (!pattern.test(value)) return message;
  }
  if (rule.minDigits && value.replace(/\D/g, "").length < rule.minDigits.value) {
    return rule.minDigits.message;
  }
  if (rule.numberRange) {
    const amount = Number(value);
    const { min, max } = rule.numberRange.value;
    if (!Number.isFinite(amount) || amount < min || amount > max) return rule.numberRange.message;
  }
  if (rule.dateWindow) {
    const selected = new Date(value);
    const today = startOfToday();
    const earliest = new Date(today);
    earliest.setDate(earliest.getDate() + rule.dateWindow.minDaysFromToday);
    const latest = new Date(today);
    latest.setDate(latest.getDate() + rule.dateWindow.maxDaysFromToday);
    if (selected < earliest) return rule.dateWindow.pastMessage;
    if (selected > latest) return rule.dateWindow.futureMessage;
  }
  return null;
}

export function validateField(id: FieldId, values: FormValues): string | null {
  return checkRule(FIELDS[id].validation, values[id]);
}
