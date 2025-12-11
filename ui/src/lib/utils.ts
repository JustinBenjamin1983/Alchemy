import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const opinionDocumentTypes = [
  { label: "Template", value: "template", colour: "bg-alchemyPrimaryOrange" },
  { label: "Case Law", value: "caselaw", colour: "bg-alchemyPrimaryOrange" },
  {
    label: "Regulation",
    value: "regulation",
    colour: "bg-alchemyPrimaryOrange",
  },
];

export const RISK_CATEGORIES = [
  "Shareholding and corporate structure",
  "Financial Position",
  "Financing",
  "Material Contracts",
  "Lease Agreements",
  "Licences",
  "Insurance",
  "Compliance with Laws",
  "Litigation",
  "Employees",
];
