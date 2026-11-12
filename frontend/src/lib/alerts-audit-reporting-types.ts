export interface ReportCountBreakdown {
  label: string;
  count: number;
}

export interface AlertTrendPoint {
  period: string;
  alerts_created: number;
}

export interface AlertProjectBreakdown {
  project_id: string;
  project_name: string;
  total_alerts: number;
  unread_alerts: number;
  escalated_alerts: number;
}

export interface AlertReportRow {
  id: string;
  project_id: string;
  project_name: string;
  alert_type: "STANDARD" | "ESCALATED";
  message: string;
  alert_date: string;
  created_at: string;
  is_read: boolean;
}

export interface AlertsReportSection {
  total_alerts: number;
  unread_alerts: number;
  read_alerts: number;
  standard_alerts: number;
  escalated_alerts: number;
  projects_with_alerts: number;
  type_breakdown: ReportCountBreakdown[];
  project_breakdown: AlertProjectBreakdown[];
  trend: AlertTrendPoint[];
  items: AlertReportRow[];
  scope_note: string;
}

export interface AuditTrendPoint {
  period: string;
  events: number;
}

export interface AuditActorBreakdown {
  actor_id: string | null;
  actor_name: string;
  events: number;
}

export interface AuditReportRow {
  id: string;
  actor_id: string | null;
  actor_name: string;
  action: string;
  entity: string;
  entity_id: string | null;
  created_at: string;
}

export interface AuditReportSection {
  total_events: number;
  unique_actors: number;
  unique_entity_references: number;
  action_breakdown: ReportCountBreakdown[];
  entity_breakdown: ReportCountBreakdown[];
  actor_breakdown: AuditActorBreakdown[];
  trend: AuditTrendPoint[];
  items: AuditReportRow[];
  scope_note: string;
}
