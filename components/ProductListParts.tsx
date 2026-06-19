import type { ReactNode } from 'react';
import type { Product, ProductKpis } from '@/lib/types';

export function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" />
      <circle cx="9.5" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

export function MaterialIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
      <path d="m10 11 5 3-5 3v-6Z" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M19.5 13.5 12 21l-7.5-7.5A5 5 0 0 1 12 7a5 5 0 0 1 7.5 6.5Z" />
    </svg>
  );
}

export type ProductStat = {
  icon: ReactNode;
  label: string;
  today: number;
  avg: number;
};

export function buildProductStats(kpis?: ProductKpis | null): ProductStat[] {
  return [
    {
      icon: <UsersIcon />,
      label: 'Creators who posted',
      today: Number(kpis?.today?.creators) || 0,
      avg: Number(kpis?.seven_day?.average_creators) || 0
    },
    {
      icon: <MaterialIcon />,
      label: 'Posts published',
      today: Number(kpis?.today?.posts) || 0,
      avg: Number(kpis?.seven_day?.average_posts) || 0
    },
    {
      icon: <EyeIcon />,
      label: 'Total views',
      today: Number(kpis?.today?.views) || 0,
      avg: Number(kpis?.seven_day?.average_views_per_day) || 0
    },
    {
      icon: <HeartIcon />,
      label: 'Total likes',
      today: Number(kpis?.today?.likes) || 0,
      avg: Number(kpis?.seven_day?.average_likes) || 0
    }
  ];
}

export function productLastSyncedDate(product: Product) {
  return product.countries?.find(country => country.reelFarmSyncedAt)?.reelFarmSyncedAt?.slice(0, 10) || '—';
}
