import React from 'react';
import { render, screen } from '@testing-library/react';
import * as index from './index';
import { LicenseInfo, Props } from './LicenseInfo';
import { LicenseToken } from './types';

jest.mock('app/core/config', () => ({
  ...(jest.requireActual('app/core/config') as any),
  licenseInfo: {},
  buildInfo: {},
  config: {
    licensing: {
      activeAdminsAndEditors: 1,
      activeViewers: 2,
      includedAdmins: -1,
      includedViewers: -1,
      slug: '',
      licenseExpiry: 1610976490,
      licenseExpiryWarnDays: 0,
      tokenExpiry: 1610976490,
      tokenExpiryWarnDays: 0,
      usageBilling: false,
    },
    licenseInfo: {},
  },
}));
jest.spyOn(index, 'initLicenseWarnings').mockImplementation(() => {});

const validToken: LicenseToken = {
  status: 1,
  jti: '805',
  iss: 'https://test.com',
  sub: 'https://test.com',
  iat: 1578576782,
  exp: 2610976490,
  nbf: 1578576526,
  lexp: 1610976490,
  lid: '10500',
  max_users: -1,
  included_admins: 10,
  included_viewers: 100,
  prod: ['grafana-enterprise'],
  company: 'Test',
  slug: '',
};

const expiredToken: LicenseToken = {
  status: 5,
  jti: '14',
  iss: 'https://test.com',
  sub: 'https://test.com',
  iat: 1539191907,
  exp: 1577854800,
  nbf: 1539191759,
  lexp: 1577854800,
  lid: '5',
  max_users: -1,
  included_admins: -1,
  included_viewers: -1,
  prod: ['grafana-enterprise'],
  company: 'Test',
  slug: '',
};

const activeUserStats = {
  active_admins_and_editors: 1,
  active_viewers: 2,
};

afterEach(jest.clearAllMocks);

const setup = (propOverrides?: Partial<Props>) => {
  const props: Props = {
    tokenUpdated: false,
    tokenRenewed: false,
    token: validToken,
    stats: activeUserStats,
  };

  Object.assign(props, propOverrides);

  render(<LicenseInfo {...props} />);
};

describe('LicensePage', () => {
  it('should show license info for valid license', async () => {
    setup();

    expect(await screen.findByRole('heading', { name: 'Enterprise license' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'License' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Token' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Utilization' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should show license warning for invalid license', async () => {
    setup({ token: expiredToken });
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(
      screen.getAllByText('Contact support to renew your token, or visit the Cloud portal to learn more.')
    ).toHaveLength(2);
    expect(screen.getByText('Token expired')).toBeInTheDocument();
  });

  it('should show warning when user utilization is reaching limits', async () => {
    setup({ stats: { ...activeUserStats, active_viewers: 81 } });

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Reaching limits: viewers')).toBeInTheDocument();
    expect(screen.getByText('Upgrade your license quotas.')).toBeInTheDocument();
    expect(screen.getByText(/There are 81 active viewers. You are approaching your limit of 100 viewers/i));
  });
});
