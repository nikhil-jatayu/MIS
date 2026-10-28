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
  role_in_project: ProjectMemberRole;
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

export interface DashboardSummary {
  role: UserRole;
  stats: DashboardStats;
  recent_projects: Project[];
  recent_alerts: Alert[];
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
