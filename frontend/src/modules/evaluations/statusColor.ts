export function evaluationStatusColor(status: string): string {
  switch (status) {
    case "draft":
      return "default";
    case "submitted":
      return "gold";
    case "returned":
      return "red";
    case "manager_approved":
    case "fm_approved":
      return "green";
    case "pmo_reviewed":
      return "blue";
    default:
      return "default";
  }
}
