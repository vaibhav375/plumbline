const LABELS: Record<string, string> = {
  creator: "Creator",
  external_creator: "Agency",
  reviewer: "Reviewer",
  compliance: "Compliance",
  accessibility: "Accessibility",
  brand_owner: "Brand owner",
  auditor: "Auditor",
};

export function RoleBadge({ name, role }: { name: string; role: string }) {
  return (
    <span className="text-sm text-muted-foreground">
      Signed in as <span className="font-medium text-foreground">{name}</span> ·{" "}
      {LABELS[role] ?? role}
    </span>
  );
}
