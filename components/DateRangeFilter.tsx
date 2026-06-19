'use client';

import { useState } from 'react';
import {
  DATE_PRESETS,
  addDays,
  addMonths,
  dateInputValue,
  defaultDateRange,
  displayDateRange,
  parseInputDate,
  rangeForPreset,
  sameDate,
  type DatePresetKey
} from '@/lib/dateRange';

export function DateRangeFilter({
  dateFrom,
  dateTo,
  onApply
}: {
  dateFrom: string;
  dateTo: string;
  onApply: (from: string, to: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(dateFrom);
  const [draftTo, setDraftTo] = useState(dateTo);
  const [month, setMonth] = useState(() => parseInputDate(dateFrom || defaultDateRange.from));

  function openPicker() {
    setDraftFrom(dateFrom);
    setDraftTo(dateTo);
    setMonth(parseInputDate(dateFrom || defaultDateRange.from));
    setOpen(true);
  }

  function applyPreset(preset: DatePresetKey) {
    const range = rangeForPreset(preset);
    setDraftFrom(range.from);
    setDraftTo(range.to);
    setMonth(parseInputDate(range.from));
  }

  function selectDay(value: string) {
    if (!draftFrom || (draftFrom && draftTo)) {
      setDraftFrom(value);
      setDraftTo('');
      return;
    }
    if (value < draftFrom) {
      setDraftTo(draftFrom);
      setDraftFrom(value);
      return;
    }
    setDraftTo(value);
  }

  const monthStart = new Date(month.getFullYear(), month.getMonth(), 1);
  const calendarStart = addDays(monthStart, -monthStart.getDay());
  const days = Array.from({ length: 42 }, (_, index) => addDays(calendarStart, index));
  const monthLabel = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(monthStart);

  return (
    <div className="date-range-filter">
      <button className="date-range-trigger" type="button" onClick={openPicker}>
        <span className="date-range-icon">▣</span>
        <span>{displayDateRange(dateFrom, dateTo)}</span>
      </button>
      {open ? (
        <div className="date-range-popover">
          <div className="date-range-presets">
            <h3>Date Range</h3>
            {DATE_PRESETS.map(preset => {
              const range = rangeForPreset(preset.key);
              const active = sameDate(draftFrom, range.from) && sameDate(draftTo, range.to);
              return (
                <button className={active ? 'active' : ''} type="button" key={preset.key} onClick={() => applyPreset(preset.key)}>
                  {preset.label}
                </button>
              );
            })}
          </div>
          <div className="date-calendar">
            <div className="date-calendar-head">
              <button type="button" onClick={() => setMonth(addMonths(month, -1))}>‹</button>
              <strong>{monthLabel}</strong>
              <button type="button" onClick={() => setMonth(addMonths(month, 1))}>›</button>
            </div>
            <div className="date-calendar-grid week">
              {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => <span key={day}>{day}</span>)}
            </div>
            <div className="date-calendar-grid">
              {days.map(day => {
                const value = dateInputValue(day);
                const outside = day.getMonth() !== month.getMonth();
                const selected = value === draftFrom || value === draftTo;
                const inRange = draftFrom && draftTo && value > draftFrom && value < draftTo;
                return (
                  <button
                    className={`${outside ? 'outside' : ''} ${selected ? 'selected' : ''} ${inRange ? 'in-range' : ''}`}
                    type="button"
                    key={value}
                    onClick={() => selectDay(value)}
                  >
                    {day.getDate()}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="date-range-actions">
            <button type="button" onClick={() => setOpen(false)}>Cancel</button>
            <button
              className="primary"
              type="button"
              onClick={() => {
                onApply(draftFrom || dateFrom, draftTo || draftFrom || dateTo);
                setOpen(false);
              }}
            >
              Apply
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
