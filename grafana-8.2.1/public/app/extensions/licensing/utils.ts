import { dateTime } from '@grafana/data';
import { config } from 'app/core/config';
import { CardState } from './LicenseCard';
import { ActiveUserStats, LicenseToken } from './types';
import { ERROR_RATE, WARNING_RATE } from './constants';

type Status = { state: CardState; status: string; title: string; message: string };

export const getUserStatMessage = (includedUsers: number, activeUsers?: number): string => {
  return (activeUsers ? `${activeUsers} of ` : '') + (includedUsers > 0 ? includedUsers : 'unlimited');
};

const tokenExpired = (token: LicenseToken) => {
  return dateTime(token.exp * 1000) < dateTime();
};

const tokenWillExpireSoon = (token: LicenseToken) => {
  return dateTime(token.exp * 1000) < dateTime().add((config as any).licensing.licenseExpiryWarnDays, 'd');
};

const tokenWillExpireInDays = (token: LicenseToken) => {
  return Math.ceil((token.exp - dateTime().unix()) / 3600 / 24);
};
export const getTokenStatus = (token: LicenseToken | null): Status => {
  if (!token) {
    return { state: '', status: '', title: '', message: '' };
  }

  if (tokenExpired(token)) {
    return {
      state: 'error',
      status: 'Expired',
      title: 'Token expired',
      message: 'Contact support to renew your token, or visit the Cloud portal to learn more.',
    };
  }

  if (tokenWillExpireSoon(token)) {
    return {
      state: 'warning',
      status: ` Expiring in ${tokenWillExpireInDays(token)} day(s)`,
      title: 'Token expires soon',
      message: `Your token expires in ${tokenWillExpireInDays(token)} day(s). Contact support to renew your token.`,
    };
  }

  return { state: '', status: '', title: '', message: '' };
};

export const getRate = (total: number, value = 0) => {
  return (100 * value) / total;
};

export const getUtilStatus = (token: LicenseToken | null, stats?: ActiveUserStats | null): Status => {
  let adminRate = 0;
  let userRate = 0;
  let state: CardState = '';
  let status = '';
  let title = '';
  let message = '';

  if (!token) {
    return {
      state,
      status,
      title,
      message,
    };
  }
  const activeAdmins = stats?.active_admins_and_editors;
  const totalAdmins = token.included_admins;
  const activeViewers = stats?.active_viewers;

  const totalViewers = token.included_viewers;
  if (typeof activeAdmins === 'number') {
    adminRate = getRate(totalAdmins, activeAdmins);
  }

  if (typeof activeViewers === 'number') {
    userRate = getRate(totalViewers, activeViewers);
  }

  if (userRate >= ERROR_RATE || adminRate >= ERROR_RATE) {
    state = 'error';
    status = 'Quota exceeded';
    title = 'Role limit exceeded';

    if (adminRate >= ERROR_RATE) {
      status += ': admins/editors';
      title = 'Admin or editor role limit exceeded';
      message = `There are more than ${totalAdmins} active administrators or editors using Grafana.`;
    } else if (userRate >= ERROR_RATE) {
      status += ': viewers';
      title = 'Viewer role limit exceeded';
      message = `There are more than ${totalViewers} active viewers using Grafana.`;
    }
    message += ' Contact support to increase the quotas.';
  } else if (userRate >= WARNING_RATE || adminRate >= WARNING_RATE) {
    state = 'warning';
    status = 'Reaching limits';
    title = 'Role utilization reaching limit';

    if (adminRate >= WARNING_RATE) {
      status += ': admins/editors';
      title = 'Admin/editor role utilization reaching limit';
      message = `There are ${activeAdmins} active administrators or editors. You are approaching your limit of ${totalAdmins} administrators or editors.`;
    } else if (userRate >= WARNING_RATE) {
      status += ': viewers';
      title = 'Viewer role utilization reaching limit';
      message = `There are ${activeViewers} active viewers. You are approaching your limit of ${totalViewers} viewers.`;
    }
    message += ' Contact support to increase the quotas.';
  }

  return {
    state,
    status,
    title,
    message,
  };
};
