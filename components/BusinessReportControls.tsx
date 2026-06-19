'use client';

import { businessIsoDate } from '@/hooks/useBusinessMaterialReport';
import type { Product } from '@/lib/types';

type BusinessReportControlsProps = {
  products: Product[];
  selectedProductId: string;
  days: number;
  customRange: boolean;
  dateFrom: string;
  dateTo: string;
  loading: boolean;
  productCode: string;
  onProductChange: (productId: string) => void;
  onDaysChange: (days: number) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onApply: () => void;
};

export function BusinessReportControls({
  products,
  selectedProductId,
  days,
  customRange,
  dateFrom,
  dateTo,
  loading,
  productCode,
  onProductChange,
  onDaysChange,
  onDateFromChange,
  onDateToChange,
  onApply
}: BusinessReportControlsProps) {
  return (
    <div className="business-report-controls">
      <select value={selectedProductId} onChange={event => onProductChange(event.target.value)}>
        {products.map(product => (
          <option value={product.id} key={product.id}>{product.name}</option>
        ))}
      </select>
      <div className="business-report-preset" aria-label="业务日范围">
        {[7, 14, 30].map(value => (
          <button
            className={!customRange && days === value ? 'active' : ''}
            type="button"
            onClick={() => {
              onDaysChange(value);
              onDateFromChange('');
              onDateToChange('');
            }}
            key={value}
          >
            {value} 天
          </button>
        ))}
      </div>
      <input type="date" value={dateFrom} max={dateTo || businessIsoDate()} onChange={event => onDateFromChange(event.target.value)} />
      <input type="date" value={dateTo} min={dateFrom || undefined} max={businessIsoDate()} onChange={event => onDateToChange(event.target.value)} />
      <button type="button" onClick={onApply} disabled={loading || !productCode}>{loading ? '读取中...' : '应用'}</button>
    </div>
  );
}
