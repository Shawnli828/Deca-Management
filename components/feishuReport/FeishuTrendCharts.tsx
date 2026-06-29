'use client';

import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import type { FeishuCardData } from '@/lib/types';

function compactAxisMetric(value: number) {
  if (!Number.isFinite(value)) return '0';
  const abs = Math.abs(value);
  if (abs >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (abs >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(Math.round(value));
}

function paddedRange(values: number[]) {
  const finite = values.filter(value => Number.isFinite(value));
  if (!finite.length) return { min: 0, max: 1 };
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) {
    const pad = Math.max(1, Math.abs(max) * 0.1);
    return { min: Math.max(0, min - pad), max: max + pad };
  }
  const pad = (max - min) * 0.12;
  return { min: Math.max(0, min - pad), max: max + pad };
}

function ceilToStep(value: number, step: number) {
  return Math.ceil(value / step) * step;
}

function countryTrendAxis(values: number[]) {
  const finite = values.filter(value => Number.isFinite(value));
  if (!finite.length) {
    return {
      min: 0,
      max: 1000,
      ticks: [0, 200, 400, 600, 800, 1000],
    };
  }
  const rawMax = Math.max(...finite, 1);
  const max = Math.max(1000, ceilToStep(rawMax * 1.08, 200));
  const ticks: number[] = [];
  for (let value = 0; value <= max; value += 200) {
    ticks.push(value);
  }
  return {
    min: 0,
    max,
    ticks,
  };
}

function allLabelIndexes(count: number) {
  return Array.from({ length: count }, (_, index) => index);
}

function xAxisLabelAnchor(index: number, count: number) {
  if (index === 0) return 'start';
  if (index === count - 1) return 'end';
  return 'middle';
}

const countryTrendColors = ['#2f8af5', '#0f766e', '#a16207', '#7c3aed', '#dc2626', '#475569', '#0891b2'];
const rfAvgGoalValue = 1000;

function svgSmoothPath(points: Array<{ x: number; y: number }>) {
  if (!points.length) return '';
  if (points.length === 1) return `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  return points.slice(1).reduce((path, point, index) => {
    const previous = points[index];
    const midX = (previous.x + point.x) / 2;
    return `${path} C${midX.toFixed(1)} ${previous.y.toFixed(1)} ${midX.toFixed(1)} ${point.y.toFixed(1)} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
  }, `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`);
}

export function FeishuCountryAvgTrendChart({
  title,
  countries
}: {
  title: string;
  countries: NonNullable<FeishuCardData['countryAvgTrend']>[string];
}) {
  const baseChart = useMemo(() => {
    const labelMap = new Map<string, { date: string; label: string }>();
    const seriesSource = (countries || []).map((country, index) => {
      const rows = (country.rows || [])
        .map(row => ({
          date: String(row.date || '').slice(0, 10),
          label: row.label || String(row.date || '').slice(5, 10),
          rfAvg: row.rfAvg === null || row.rfAvg === undefined ? null : Number(row.rfAvg),
          posts: Number(row.posts || 0),
        }))
        .filter(row => row.date && row.rfAvg !== null && Number.isFinite(row.rfAvg));
      rows.forEach(row => labelMap.set(row.date, { date: row.date, label: row.label }));
      const countryName = country.countryName || country.countryCode || 'Country';
      return {
        id: `${country.countryCode || countryName}-${index}`,
        countryName,
        flag: country.flag || '🌐',
        color: countryTrendColors[index % countryTrendColors.length],
        rows,
      };
    }).filter(country => country.rows.length);

    const labels = Array.from(labelMap.values()).sort((a, b) => a.date.localeCompare(b.date));
    return { labels, seriesSource };
  }, [countries]);

  const countrySelectionKey = baseChart.seriesSource.map(series => series.id).join('|');
  const [selectedCountryIds, setSelectedCountryIds] = useState<string[]>([]);

  useEffect(() => {
    setSelectedCountryIds(baseChart.seriesSource.map(series => series.id));
  }, [countrySelectionKey, baseChart.seriesSource]);

  const selectedIdSet = useMemo(() => {
    const activeIds = selectedCountryIds.length
      ? selectedCountryIds
      : baseChart.seriesSource.map(series => series.id);
    return new Set(activeIds);
  }, [selectedCountryIds, baseChart.seriesSource]);

  const chart = useMemo(() => {
    const labels = baseChart.labels;
    const visibleSource = baseChart.seriesSource.filter(country => selectedIdSet.has(country.id));
    const seriesSource = visibleSource.length ? visibleSource : baseChart.seriesSource;
    const values = seriesSource.flatMap(country => country.rows.map(row => Number(row.rfAvg || 0)));
    const width = 1040;
    const pad = { top: 46, right: 36, bottom: 42, left: 62 };
    const axis = countryTrendAxis(values);
    const tickIntervals = Math.max(1, (axis.max - axis.min) / 200);
    const height = pad.top + pad.bottom + Math.max(360, tickIntervals * 38);
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const xFor = (index: number) => pad.left + (labels.length <= 1 ? plotWidth / 2 : (plotWidth / (labels.length - 1)) * index);
    const yFor = (value: number) => {
      const clamped = Math.min(axis.max, Math.max(axis.min, value));
      const ratio = (clamped - axis.min) / Math.max(1, axis.max - axis.min);
      return pad.top + plotHeight - ratio * plotHeight;
    };
    const labelIndexes = allLabelIndexes(labels.length);
    const series = seriesSource.map(country => {
      const rowsByDate = new Map(country.rows.map(row => [row.date, row]));
      const points = labels
        .map((label, labelIndex) => {
          const row = rowsByDate.get(label.date);
          if (!row || row.rfAvg === null) return null;
          return {
            x: xFor(labelIndex),
            y: yFor(row.rfAvg),
            value: row.rfAvg,
            date: label.date,
          };
        })
        .filter(Boolean) as Array<{ x: number; y: number; value: number; date: string }>;
      return {
        ...country,
        points,
        path: svgSmoothPath(points),
      };
    });
    const grid = axis.ticks.map(value => ({
      y: yFor(value),
      value,
    }));
    const goal = {
      y: yFor(rfAvgGoalValue),
      value: rfAvgGoalValue,
    };
    return { labels, width, height, pad, series, grid, goal, labelIndexes };
  }, [baseChart, selectedIdSet]);

  const toggleCountry = (countryId: string) => {
    setSelectedCountryIds(current => {
      const activeIds = current.length ? current : baseChart.seriesSource.map(series => series.id);
      const isActive = activeIds.includes(countryId);
      if (isActive && activeIds.length <= 1) return activeIds;
      return isActive
        ? activeIds.filter(id => id !== countryId)
        : [...activeIds, countryId];
    });
  };

  if (!baseChart.seriesSource.length || !baseChart.labels.length) {
    return (
      <div className="feishu-country-trend is-empty">
        <div className="feishu-native-section-title">{title}</div>
        <p>暂无国家均播趋势。</p>
      </div>
    );
  }

  return (
    <div className="feishu-country-trend">
      <div className="feishu-country-trend-head">
        <div className="feishu-native-section-title">{title}</div>
        <div className="feishu-country-legend">
          {baseChart.seriesSource.map(series => {
            const active = selectedIdSet.has(series.id);
            return (
              <button
                type="button"
                key={series.id}
                className={active ? 'is-active' : 'is-muted'}
                style={{ '--series-color': series.color } as CSSProperties}
                aria-pressed={active}
                onClick={() => toggleCountry(series.id)}
              >
                {series.flag} {series.countryName}
              </button>
            );
          })}
        </div>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        width={chart.width}
        height={chart.height}
        role="img"
        aria-label={title}
      >
        {chart.grid.map(line => (
          <g key={`country-grid-${line.y}`}>
            <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={line.y} y2={line.y} />
            <text className="is-y-label" x={chart.pad.left - 8} y={line.y + 3} textAnchor="end">
              {compactAxisMetric(line.value)}
            </text>
          </g>
        ))}
        <g className="is-goal-marker">
          <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={chart.goal.y} y2={chart.goal.y} />
          <text x={chart.width - chart.pad.right - 4} y={chart.goal.y - 6} textAnchor="end">
            Goal {compactAxisMetric(chart.goal.value)}
          </text>
        </g>
        {chart.series.map(series => (
          <g key={`country-series-${series.countryName}`}>
            <path d={series.path} style={{ stroke: series.color }} />
            {series.points.map(point => (
              <g key={`${series.countryName}-${point.date}`}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r="2.2"
                  style={{ fill: series.color }}
                />
                <text
                  className="is-point-label"
                  x={point.x}
                  y={Math.max(chart.pad.top - 10, point.y - 8)}
                  textAnchor="middle"
                  style={{ fill: series.color }}
                >
                  {compactAxisMetric(point.value)}
                </text>
              </g>
            ))}
          </g>
        ))}
        {chart.labelIndexes.map(index => (
          <text
            className="is-x-label"
            x={chart.pad.left + (chart.labels.length <= 1 ? (chart.width - chart.pad.left - chart.pad.right) / 2 : ((chart.width - chart.pad.left - chart.pad.right) / (chart.labels.length - 1)) * index)}
            y={chart.height - 7}
            textAnchor={xAxisLabelAnchor(index, chart.labels.length)}
            key={`country-label-${chart.labels[index].date}`}
          >
            {chart.labels[index].label}
          </text>
        ))}
      </svg>
    </div>
  );
}

export function FeishuTrendPanel({
  groups
}: {
  groups: NonNullable<FeishuCardData['trendGroups']>;
}) {
  const visibleGroups = groups.slice(0, 4);

  return (
    <div className="feishu-native-trend">
      <div className="feishu-native-trend-head">
        <div className="feishu-native-section-title">View / Download 趋势</div>
        <div className="feishu-native-legend">
          <span className="is-view">View</span>
          <span className="is-download">Download</span>
        </div>
      </div>
      {visibleGroups.length ? (
        <div className={`feishu-native-trend-grid${visibleGroups.length === 1 ? ' is-single' : ''}`}>
          {visibleGroups.map(group => (
            <FeishuMiniTrendChart
              key={group.key || group.label}
              title={(group.label || group.key) === '总览' ? '全部汇总' : (group.label || group.key || '趋势')}
              trend={group.trend || []}
              wide={visibleGroups.length === 1}
            />
          ))}
        </div>
      ) : (
        <p>暂无趋势数据。</p>
      )}
    </div>
  );
}

function FeishuMiniTrendChart({
  title,
  trend,
  wide = false
}: {
  title: string;
  trend: NonNullable<FeishuCardData['trend']>;
  wide?: boolean;
}) {
  const chart = useMemo(() => {
    const rows = trend.map(row => ({
      label: row.label || row.date || '',
      view: Number(row.view || 0),
      download: Number(row.download || 0)
    }));
    const width = wide ? 920 : 320;
    const height = wide ? 300 : 170;
    const pad = wide
      ? { top: 16, right: 58, bottom: 34, left: 58 }
      : { top: 12, right: 36, bottom: 26, left: 42 };
    const plotWidth = width - pad.left - pad.right;
    const plotHeight = height - pad.top - pad.bottom;
    const viewRange = paddedRange(rows.map(row => row.view));
    const downloadRange = paddedRange(rows.map(row => row.download));
    const xFor = (index: number) => pad.left + (rows.length <= 1 ? plotWidth / 2 : (plotWidth / (rows.length - 1)) * index);
    const yFor = (value: number, range: { min: number; max: number }) => {
      const ratio = (value - range.min) / Math.max(1, range.max - range.min);
      return pad.top + plotHeight - ratio * plotHeight;
    };
    const viewPoints = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.view, viewRange), value: row.view }));
    const downloadPoints = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.download, downloadRange), value: row.download }));
    const labelYFor = (pointY: number, offset: number) => Math.min(
      height - pad.bottom - 4,
      Math.max(pad.top + 8, pointY + offset)
    );
    const pathFor = (points: Array<{ x: number; y: number }>) => {
      if (!points.length) return '';
      if (points.length === 1) return `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
      return points.slice(1).reduce((path, point, index) => {
        const previous = points[index];
        const midX = (previous.x + point.x) / 2;
        return `${path} C${midX.toFixed(1)} ${previous.y.toFixed(1)} ${midX.toFixed(1)} ${point.y.toFixed(1)} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
      }, `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`);
    };
    const grid = Array.from({ length: 4 }, (_, index) => {
      const ratio = index / 3;
      return {
        y: pad.top + ratio * plotHeight,
        view: viewRange.max - ratio * (viewRange.max - viewRange.min),
        download: downloadRange.max - ratio * (downloadRange.max - downloadRange.min),
      };
    });
    const labelIndexes = allLabelIndexes(rows.length);
    return {
      rows,
      width,
      height,
      pad,
      viewPoints,
      downloadPoints,
      labelYFor,
      viewPath: pathFor(viewPoints),
      downloadPath: pathFor(downloadPoints),
      grid,
      labelIndexes,
    };
  }, [trend, wide]);

  if (!chart.rows.length) {
    return (
      <div className={`feishu-native-mini-chart is-empty${wide ? ' is-wide' : ''}`}>
        <div className="feishu-native-mini-chart-head">
          <strong>{title}</strong>
        </div>
        <p>暂无趋势数据。</p>
      </div>
    );
  }

  return (
    <div className={`feishu-native-mini-chart${wide ? ' is-wide' : ''}`}>
      <div className="feishu-native-mini-chart-head">
        <strong>{title}</strong>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        width={chart.width}
        height={chart.height}
        role="img"
        aria-label={`${title} View and Download trend`}
      >
          {chart.grid.map(line => (
            <g key={`grid-${line.y}`}>
              <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={line.y} y2={line.y} />
              <text className="is-y-label" x={chart.pad.left - 8} y={line.y + 3} textAnchor="end">
                {compactAxisMetric(line.view)}
              </text>
              <text className="is-y-label" x={chart.width - chart.pad.right + 8} y={line.y + 3} textAnchor="start">
                {compactAxisMetric(line.download)}
              </text>
            </g>
          ))}
          <path className="is-view-line" d={chart.viewPath} />
          <path className="is-download-line" d={chart.downloadPath} />
          {chart.viewPoints.map((point, index) => (
            <circle className="is-view-point" cx={point.x} cy={point.y} r="2.2" key={`view-${index}-${chart.rows[index].label}`} />
          ))}
          {chart.downloadPoints.map((point, index) => (
            <circle className="is-download-point" cx={point.x} cy={point.y} r="2.2" key={`download-${index}-${chart.rows[index].label}`} />
          ))}
          {chart.viewPoints.map((point, index) => (
            <text
              className="is-point-label is-view-label"
              x={point.x}
              y={chart.labelYFor(point.y, -9)}
              textAnchor="middle"
              key={`view-label-${index}-${chart.rows[index].label}`}
            >
              {compactAxisMetric(point.value)}
            </text>
          ))}
          {chart.downloadPoints.map((point, index) => (
            <text
              className="is-point-label is-download-label"
              x={point.x}
              y={chart.labelYFor(point.y, 14)}
              textAnchor="middle"
              key={`download-label-${index}-${chart.rows[index].label}`}
            >
              {compactAxisMetric(point.value)}
            </text>
          ))}
          {chart.labelIndexes.map(index => (
            <text
              className="is-x-label"
              x={chart.viewPoints[index].x}
              y={chart.height - 6}
              textAnchor={xAxisLabelAnchor(index, chart.rows.length)}
              key={`label-${index}-${chart.rows[index].label}`}
            >
              {chart.rows[index].label}
            </text>
          ))}
        </svg>
    </div>
  );
}

