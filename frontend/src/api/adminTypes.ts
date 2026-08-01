export type MaintenanceScope = "device" | "group" | "building" | "campus";

export interface MaintenanceWindow {
  id: number;
  scope_type: MaintenanceScope;
  scope_id: number | null;
  scope_building: string | null;
  starts_at: string;
  ends_at: string;
  rrule: string | null;
  reason: string | null;
  created_by: number | null;
  created_at: string;
}

export type UserRole = "admin" | "security_officer" | "technician" | "viewer";

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  vendor_id: number | null;
  active: boolean;
  created_at: string;
}
