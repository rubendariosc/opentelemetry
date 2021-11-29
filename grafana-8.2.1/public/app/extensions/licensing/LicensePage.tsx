import React, { useEffect, useState } from 'react';
import { connect, ConnectedProps } from 'react-redux';
import { getNavModel } from 'app/core/selectors/navModel';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import Page from 'app/core/components/Page/Page';
import { ServerStats } from 'app/features/admin/ServerStats';
import { EnterpriseStoreState } from '../types';
import { getLicenseToken, refreshLicenseStats } from './state/api';
import { initLicenseWarnings } from './index';
import { ActiveUserStats, LicenseToken } from './types';
import { LicenseInfo } from './LicenseInfo';

interface QueryParams {
  tokenUpdated?: boolean;
  tokenRenewed?: boolean;
}

interface OwnProps extends GrafanaRouteComponentProps<{}, QueryParams> {}

const mapStateToProps = (state: EnterpriseStoreState) => ({
  navModel: getNavModel(state.navIndex, 'licensing'),
});

const connector = connect(mapStateToProps, {});
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const LicensePage = ({ navModel, queryParams }: Props) => {
  const [token, setToken] = useState<LicenseToken | null>(null);
  const [stats, setStats] = useState<ActiveUserStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { tokenUpdated, tokenRenewed } = queryParams;

  useEffect(() => {
    const getData = async () => {
      const token = await getLicenseToken().catch(() => null);
      const stats = await refreshLicenseStats().catch(() => null);
      setToken(token);
      setStats(stats);
      setIsLoading(false);
    };
    getData();

    return initLicenseWarnings;
  }, []);

  return (
    <Page navModel={navModel}>
      <Page.Contents isLoading={isLoading}>
        <ServerStats />
        <LicenseInfo token={token} stats={stats} tokenUpdated={tokenUpdated} tokenRenewed={tokenRenewed} />
      </Page.Contents>
    </Page>
  );
};

export default connector(LicensePage);
