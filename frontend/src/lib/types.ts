export type UserRole = "SUPER_ADMIN" | "ADMIN" | "USER";
export type ProjectType = "RND" | "PRODUCTION";
export type ProjectStatus =
  | "PENDING_INVENTORY"
  | "READY_FOR_PRODUCTION"
  | "AWAITING_DELIVERY"
  | "IN_PRODUCTION"
  | "IN_TESTING"
  | "COMPLETED";
export type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ProjectMemberRole = "DEVELOPER" | "PRODUCER" | "TESTER";
export type Department =
  | "management"
  | "R_D"
  | "production"
  | "assembly"
  | "testing"
  | "store"
  | "other";
export type PurchaseRequestStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "ORDERED"
  | "DELIVERED";
export type AlertType = "STANDARD" | "ESCALATED";
export type TestResult = "PASS" | "FAIL";

export interface UserSummary {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department: Department | null;
  department_other: string | null;
  is_active: boolean;
}

export interface User extends UserSummary {
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface InventoryItem {
  id: string;
  name: string;
  sku: string;
  quantity_available: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: string;
  user: UserSummary;
  role_in_project: ProjectMemberRole | null;
  department: Department | null;
}

export interface ProjectBomLine {
  id: string;
  item: InventoryItem;
  quantity_required: number;
  quantity_allocated: number;
  quantity_shortage: number;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  type: ProjectType;
  status: ProjectStatus;
  priority: Priority;
  start_date: string | null;
  end_date: string | null;
  estimated_completion_date: string | null;
  estimated_completion_set_by: string | null;
  estimated_completion_set_at: string | null;
  estimated_completion_edited_by_member: boolean;
  created_by: string;
  status_changed_at: string;
  progress_percent: number;
  delay_reason: string | null;
  paused_from_status: ProjectStatus | null;
  test_result: TestResult | null;
  test_note: string | null;
  tested_by: string | null;
  tested_at: string | null;
  created_at: string;
  updated_at: string;
  creator: UserSummary;
  tester: UserSummary | null;
  estimate_setter: UserSummary | null;
  members: ProjectMember[];
  bom_lines: ProjectBomLine[];
  is_inventory_ready: boolean;
  shortage_count: number;
  pending_days: number;
}

export interface ProjectRef {
  id: string;
  name: string;
  status: ProjectStatus;
  type: ProjectType;
}

export interface PurchaseRequest {
  id: string;
  project_id: string;
  item_id: string;
  quantity: number;
  requested_by: string;
  status: PurchaseRequestStatus;
  reason: string | null;
  review_note: string | null;
  approved_by: string | null;
  approved_at: string | null;
  ordered_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
  project: ProjectRef;
  item: Pick<InventoryItem, "id" | "name" | "sku" | "quantity_available">;
  requester: UserSummary;
  approver: UserSummary | null;
}

export interface ProgressLog {
  id: string;
  project_id: string;
  user_id: string;
  note: string;
  progress_percent: number;
  created_at: string;
  user: UserSummary;
}

export interface Attachment {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string;
  created_at: string;
  uploader: UserSummary;
  download_url: string;
}

export interface Alert {
  id: string;
  user_id: string;
  project_id: string;
  type: AlertType;
  message: string;
  is_read: boolean;
  alert_date: string;
  created_at: string;
  project: ProjectRef;
}

export interface AuditLog {
  id: string;
  actor_id: string | null;
  action: string;
  entity: string;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
  actor: UserSummary | null;
}

export interface ThresholdSettings {
  safe_threshold_days: number;
  escalation_threshold_days: number;
  deadline_reminder_days: number;
  severe_delay_multiplier: number;
  updated_at: string | null;
}

export interface DashboardStats {
  projects_total: number;
  projects_active: number;
  projects_completed: number;
  projects_assigned: number;
  pending_inventory: number;
  ready_for_production: number;
  awaiting_delivery: number;
  in_production: number;
  in_testing: number;
  pending_purchase_requests: number;
  unread_alerts: number;
  escalated_alerts: number;
  users_total: number;
  inventory_items: number;
}

export interface DashboardProductionUnit {
  unit_of_measure: string;
  entries_count: number;
  planned_quantity: number;
  actual_quantity: number;
  accepted_first_pass_quantity: number;
  rework_quantity: number;
  plan_achievement_percent: number | null;
  first_pass_yield_percent: number | null;
  rework_rate_percent: number | null;
}

export interface DashboardProductionSummary {
  period_start: string;
  period_end: string;
  entries_count: number;
  open_actions: number;
  overdue_actions: number;
  units: DashboardProductionUnit[];
}

export interface DashboardSummary {
  role: UserRole;
  stats: DashboardStats;
  recent_projects: Project[];
  recent_alerts: Alert[];
  production: DashboardProductionSummary;
}

export interface AlertRunResult {
  evaluated_projects: number;
  standard_projects: number;
  escalated_projects: number;
  severe_projects: number;
  alerts_created: number;
  duplicates_skipped: number;
  run_at: string;
}

export interface MessageResponse {
  message: string;
}

export type ProductionActionStatus = "OPEN" | "IN_PROGRESS" | "ON_HOLD" | "CLOSED";

export interface ProductionEntry {
  id: string;
  production_date: string;
  production_line: string;
  product_model: string;
  work_order_customer: string | null;
  process_stage: string;
  unit_of_measure: string;
  planned_quantity: number;
  actual_quantity: number;
  accepted_quantity: number;
  rejected_quantity: number;
  rework_quantity: number;
  production_hours: number;
  downtime_hours: number;
  plan_achievement_percent: number | null;
  first_pass_yield_percent: number | null;
  rejection_percent: number | null;
  downtime_percent: number | null;
  month: string;
  project_id: string | null;
  remarks: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  creator: UserSummary;
}

export interface ProductionEntryCreate {
  production_date: string;
  production_line: string;
  product_model: string;
  work_order_customer?: string | null;
  process_stage: string;
  unit_of_measure: string;
  planned_quantity: number;
  actual_quantity: number;
  accepted_quantity: number;
  rework_quantity: number;
  production_hours: number;
  downtime_hours: number;
  project_id?: string | null;
  remarks?: string | null;
}

export interface ProductionAction {
  id: string;
  action_number: string;
  date_raised: string;
  issue_observation: string;
  corrective_action: string;
  responsible_user_id: string | null;
  deadline: string;
  status: ProductionActionStatus;
  closed_at: string | null;
  closed_by_user_id: string | null;
  closure_evidence: string | null;
  remarks: string | null;
  project_id: string | null;
  production_entry_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  responsible_user: UserSummary | null;
  creator: UserSummary;
  closed_by: UserSummary | null;
  is_overdue: boolean;
}

export interface ProductionActionCreate {
  date_raised: string;
  issue_observation: string;
  corrective_action: string;
  responsible_user_id: string;
  deadline: string;
  remarks?: string | null;
  project_id?: string | null;
  production_entry_id?: string | null;}

export interface ProductionUnitSummary {
  unit_of_measure: string;
  entries_count: number;
  planned_quantity: number;
  actual_quantity: number;
  accepted_quantity: number;
  rejected_quantity: number;
  rework_quantity: number;
  production_hours: number;
  downtime_hours: number;
  plan_achievement_percent: number | null;
  first_pass_yield_percent: number | null;
  rejection_percent: number | null;
  downtime_percent: number | null;
}

export interface ProductionMonthlyReview {
  id: string;
  year: number;
  month: number;
  management_summary: string;
  prepared_by_user_id: string;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  prepared_by: UserSummary;
  reviewed_by: UserSummary | null;
}

export interface ProductionSummary {
  year: number;
  month: number;
  units: ProductionUnitSummary[];
  open_actions: number;
  overdue_actions: number;
  closed_this_month: number;
  monthly_review: ProductionMonthlyReview | null;
}

export interface ProductionAssignee {
  id: string;
  name: string;
}
