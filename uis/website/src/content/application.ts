import type { ApplicationPageContent } from "@/types/application";

export const applicationContent: ApplicationPageContent = {
  title: "Department Application Form",
  intro:
    "Use this form to request a digital initiative for Brasaland operations across Colombia and Florida. All required fields are marked and validated before submission.",
  submitLabel: "Submit application",
  resetLabel: "Clear form",
  successMessage: "Application submitted successfully. Brasaland Digital will review your request.",
  errorSummaryMessage: "Please fix the highlighted fields before submitting this request.",
  fieldsets: [
    {
      legend: "Requester Information",
      fields: [
        {
          name: "requesterName",
          label: "Full name",
          type: "text",
          autoComplete: "name",
          validation: {
            requiredMessage: "Full name is required.",
            patterns: [
              {
                pattern: /^[A-Za-zÀ-ÿ'\-\s]{3,80}$/,
                message: "Use at least 3 letters and only valid name characters.",
              },
            ],
          },
        },
        {
          name: "department",
          label: "Department",
          type: "select",
          selectPlaceholder: "Select department",
          options: [
            "Restaurant Operations",
            "Procurement and Suppliers",
            "Marketing and Digital Experience",
            "People and Culture",
            "Training and Quality Standards",
            "Technology",
            "Executive Direction",
          ],
          validation: { requiredMessage: "Department is required." },
        },
        {
          name: "workEmail",
          label: "Work email",
          type: "email",
          autoComplete: "email",
          placeholder: "name@brasaland.com",
          validation: {
            requiredMessage: "Work email is required.",
            patterns: [
              {
                pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: "Enter a valid email format, for example name@brasaland.com.",
              },
              {
                pattern: /@brasaland\.(com|co)$/i,
                message: "Use your Brasaland corporate email (@brasaland.com or @brasaland.co).",
              },
            ],
          },
        },
        {
          name: "workPhone",
          label: "Work phone",
          type: "tel",
          autoComplete: "tel",
          placeholder: "+57 300 111 2233",
          validation: {
            requiredMessage: "Work phone is required.",
            patterns: [
              {
                pattern: /^\+?[0-9\s()-]{10,20}$/,
                message: "Enter a valid phone with country code and at least 10 digits.",
              },
            ],
            minDigits: { value: 10, message: "Phone must include at least 10 digits." },
          },
        },
      ],
    },
    {
      legend: "Location and Market",
      fields: [
        {
          name: "locationId",
          label: "Location ID (14 total)",
          type: "select",
          selectPlaceholder: "Select location",
          options: [
            "CO-MED-01",
            "CO-MED-02",
            "CO-MED-03",
            "CO-MED-04",
            "CO-MED-05",
            "CO-MED-06",
            "CO-MED-07",
            "CO-MED-08",
            "US-MIA-01",
            "US-MIA-02",
            "US-MIA-03",
            "US-MIA-04",
            "US-MIA-05",
            "US-MIA-06",
          ],
          validation: { requiredMessage: "Location ID is required." },
        },
        {
          name: "countryMarket",
          label: "Country market",
          type: "select",
          selectPlaceholder: "Select market",
          options: ["Colombia", "United States (Florida)"],
          validation: { requiredMessage: "Country market is required." },
        },
      ],
    },
    {
      legend: "Automation Request",
      fields: [
        {
          name: "challengeType",
          label: "Challenge type from milestone map",
          type: "select",
          selectPlaceholder: "Select challenge",
          options: [
            "Real-time sales dashboard",
            "Intelligent ingredient ordering",
            "No-sales opening-hours alerts",
            "Supplier price history and alerts",
            "Digital loyalty and ordering app",
            "Customer CRM and personalization engine",
            "HR portal and onboarding automation",
            "Training platform and recipe update push",
            "Central API and telemetry pipeline",
            "Executive AI assistant and Monday report",
          ],
          validation: { requiredMessage: "Challenge type is required." },
        },
        {
          name: "targetDate",
          label: "Target launch date",
          type: "date",
          validation: {
            requiredMessage: "Target launch date is required.",
            dateWindow: {
              minDaysFromToday: 0,
              maxDaysFromToday: 180,
              pastMessage: "Target launch date cannot be in the past.",
              futureMessage: "Target launch date must be within the next 180 days.",
            },
          },
        },
        {
          name: "weeklyIncidents",
          label: "Weekly incidents affected",
          type: "number",
          min: 1,
          max: 50000,
          validation: {
            requiredMessage: "Weekly incidents affected is required.",
            numberRange: {
              value: { min: 1, max: 50000 },
              message: "Weekly incidents must be a number between 1 and 50000.",
            },
          },
        },
        {
          name: "currentProcess",
          label: "Current process and tools (e.g., WhatsApp, Excel, PDF reports)",
          type: "textarea",
          rows: 4,
          validation: {
            requiredMessage: "Current process and tools is required.",
            minLength: {
              value: 20,
              message: "Current process and tools must be at least 20 characters.",
            },
          },
        },
        {
          name: "expectedOutcome",
          label: "Expected business outcome",
          type: "textarea",
          rows: 3,
          validation: {
            requiredMessage: "Expected business outcome is required.",
            minLength: {
              value: 20,
              message: "Expected business outcome must be at least 20 characters.",
            },
          },
        },
      ],
    },
    {
      legend: "Approval",
      fields: [
        {
          name: "confirmData",
          label:
            "I confirm this request represents a real Brasaland department need and includes accurate operational context.",
          type: "checkbox",
          validation: {
            requiredMessage: "You must confirm the request information before submitting.",
          },
        },
      ],
    },
  ],
};
