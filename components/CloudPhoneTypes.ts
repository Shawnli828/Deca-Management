export type PhoneState = 'ready' | 'running' | 'warming' | 'offline' | 'empty';

export type PhoneSlot = {
  id: string;
  label: string;
  state: PhoneState;
  account?: string;
  serialName?: string;
  serialNo?: string;
  groupName?: string;
  countryName?: string;
  timeZone?: string;
  deviceModel?: string;
  statusCode?: number | string | null;
  rpaStatus?: number | string | null;
  tags?: string[];
};

export type IpGroup = {
  id: string;
  name: string;
  code: string;
  countryName: string;
  source?: string;
  phoneCount: number;
  activeCount: number;
  slots: PhoneSlot[];
};

export type CloudProduct = {
  id: string;
  name: string;
  code: string;
  logo?: string;
  folder?: string;
  ipGroups: IpGroup[];
};

export type CountrySection = {
  id: string;
  code: string;
  countryName: string;
  ipGroups: IpGroup[];
  phoneCount: number;
  activeCount: number;
  warningCount: number;
};

export type GeeLarkPhone = {
  id: string;
  serialName?: string;
  serialNo?: string;
  groupName?: string;
  countryName?: string;
  timeZone?: string;
  deviceModel?: string;
  status?: number | string | null;
  rpaStatus?: number | string | null;
  tags?: string[];
};

export type GeeLarkGroup = {
  id: string;
  name: string;
  productCode: string;
  countryCode: string;
  countryName?: string;
  phones: GeeLarkPhone[];
};

export type GeeLarkPayload = {
  ok: boolean;
  phone_count: number;
  group_count: number;
  filters?: {
    product_code?: string;
    country_code?: string;
  };
  groups: GeeLarkGroup[];
};

export type GeeLarkPayloadMap = Record<string, GeeLarkPayload>;

export type GeeLarkMapPayload = {
  ok: boolean;
  phone_count: number;
  group_count: number;
  items: GeeLarkPayload[];
};
