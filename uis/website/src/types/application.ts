export type FieldId =
  | "requesterName"
  | "department"
  | "workEmail"
  | "workPhone"
  | "locationId"
  | "countryMarket"
  | "challengeType"
  | "targetDate"
  | "weeklyIncidents"
  | "currentProcess"
  | "expectedOutcome"
  | "confirmData";

export type TextFieldId = Exclude<FieldId, "confirmData">;
export type FormValues = Record<TextFieldId, string> & { confirmData: boolean };
export type FormErrors = Partial<Record<FieldId, string>>;

export type FieldType = "text" | "email" | "tel" | "date" | "number" | "select" | "textarea" | "checkbox";

export interface MessageRule<T> {
  value: T;
  message: string;
}

export interface PatternRule {
  pattern: RegExp;
  message: string;
}

export interface DateWindowRule {
  minDaysFromToday: number;
  maxDaysFromToday: number;
  pastMessage: string;
  futureMessage: string;
}

// Checks run in declaration order: required, minLength, patterns, minDigits, numberRange, dateWindow.
export interface ValidationRule {
  requiredMessage: string;
  minLength?: MessageRule<number>;
  patterns?: readonly PatternRule[];
  minDigits?: MessageRule<number>;
  numberRange?: MessageRule<{ min: number; max: number }>;
  dateWindow?: DateWindowRule;
}

export interface FieldConfig {
  name: FieldId;
  label: string;
  type: FieldType;
  validation: ValidationRule;
  autoComplete?: string;
  placeholder?: string;
  options?: readonly string[];
  selectPlaceholder?: string;
  rows?: number;
  min?: number;
  max?: number;
}

export interface FieldsetConfig {
  legend: string;
  fields: readonly FieldConfig[];
}

export interface ApplicationPageContent {
  title: string;
  intro: string;
  submitLabel: string;
  resetLabel: string;
  successMessage: string;
  errorSummaryMessage: string;
  fieldsets: readonly FieldsetConfig[];
}

export interface FormStatusState {
  type: "error" | "success";
  message: string;
}
