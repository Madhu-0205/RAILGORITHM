export function formatMinutes(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const normalised = ((Math.round(value) % 1440) + 1440) % 1440;
  const hours = Math.floor(normalised / 60);
  const minutes = normalised % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function severityClass(severity: string): string {
  return `severity severity-${severity.toLowerCase()}`;
}

export function statusClass(status: string): string {
  const normalised = status.toLowerCase().replace(/_/g, "-");
  return `status status-${normalised}`;
}

export function evidenceLabel(status: string): string {
  switch (status) {
    case "VALIDATED":
      return "Independently validated";
    case "VALIDATED_WITH_ASSUMPTIONS":
      return "Validated with stated assumptions";
    case "MODEL_DISAGREEMENT":
      return "Models disagree — human review required";
    case "NO_FEASIBLE_SOLUTION":
      return "No feasible solution";
    case "INCOMPLETE_DATA":
      return "Incomplete data";
    default:
      return status.replace(/_/g, " ").toLowerCase();
  }
}

export function numberOrDash(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function delayTone(delay: number): string {
  if (delay <= 5) return "delay-good";
  if (delay <= 15) return "delay-watch";
  return "delay-bad";
}

export function humanise(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
