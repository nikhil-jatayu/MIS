import type { Priority, ProjectStatus, ProjectType, PurchaseRequestStatus } from "@/lib/types";

export interface OperationsReportFilters {
  date_from: string;
  date_to: string;
  project_id: string | null;
  project_status: ProjectStatus | null;
  project_type: ProjectType | null;
  priority: Priority | null;
  purchase_status: PurchaseRequestStatus | null;
}

export interface CountBreakdown {
  label: string;
  count: number;
}

export interface ProjectTrendPoint {
  period: string;
  projects_created: number;
}

export interface ProjectReportRow {
  id: string;
  name: string;
  type: ProjectType;
  status: ProjectStatus;
  priority: Priority;
  start_date: string | null;
  end_date: string | null;
  progress_percent: number;
  shortage_lines: number;
  created_at: string;
}

export interface ProjectsReportSection {
  total_projects: number;
  average_progress_percent: number | null;
  current_overdue_projects: number;
  progress_updates_in_period: number;
  status_breakdown: CountBreakdown[];
  priority_breakdown: CountBreakdown[];
  creation_trend: ProjectTrendPoint[];
  items: ProjectReportRow[];
  scope_note: string;
}

export interface InventoryItemReportRow {
  id: string;
  name: string;
  sku: string;
  quantity_available: number;
  active_project_count: number;
  active_project_required: number;
  active_project_allocated: number;
  active_project_shortage: number;
}

export interface InventoryReportSection {
  as_of: string;
  total_items: number;
  zero_stock_items: number;
  items_with_active_project_demand: number;
  items_with_active_project_shortage: number;
  items: InventoryItemReportRow[];
  scope_note: string;
}

export interface PurchaseItemBreakdown {
  sku: string;
  item_name: string;
  request_count: number;
  requested_quantity: number;
}

export interface PurchaseRequestReportRow {
  id: string;
  project_name: string;
  item_name: string;
  sku: string;
  quantity: number;
  status: PurchaseRequestStatus;
  requester_name: string;
  created_at: string;
  approved_at: string | null;
  ordered_at: string | null;
  delivered_at: string | null;
}

export interface PurchasesReportSection {
  total_requests: number;
  status_breakdown: CountBreakdown[];
  average_approval_hours: number | null;
  average_delivery_days: number | null;
  by_item: PurchaseItemBreakdown[];
  items: PurchaseRequestReportRow[];
  scope_note: string;
}

export interface OperationsReportSummary {
  filters: OperationsReportFilters;
  projects: ProjectsReportSection;
  inventory: InventoryReportSection;
  purchases: PurchasesReportSection;
}
