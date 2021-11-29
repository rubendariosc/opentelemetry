export interface LicenseToken {
  status: number;
  jti: string;
  iss: string;
  sub: string;
  iat: number;
  exp: number;
  nbf: number;
  lexp: number;
  lid: string;
  max_users: number;
  included_admins: number;
  included_viewers: number;
  prod: string[];
  company: string;
  usage_billing?: boolean;
  slug: string;
}

export interface ActiveUserStats {
  active_admins_and_editors: number;
  active_viewers: number;
}

export type PermissionsReport = {
  id: number;
  title: string;
  slug: string;
  uid: string;
  url: string;
  isFolder: boolean;
  orgId: number;
  granteeType: string;
  granteeName: string;
  granteeUrl: string;
  customPermissions: string;
  orgRole: string;
  usersCount: number;
};
